import gradio as gr
import pandas as pd
import math

from app_helpers import (
    CURRENCY_CHOICES,
    build_page_label,
    clear_all,
    clear_logs,
    log_message,
    generate_image,
    generate_pdf,
    get_exchange_rate,
    paginate_dataframe,
    process_reconciliation,
)

with gr.Blocks(title="Cross-Border Treasury Reconciliation Agent") as demo:
    gr.Markdown(
        """
        # 🌍 Cross-Border Treasury Reconciliation Agent

        Automated reconciliation of cross-border transactions using AI agents.
        Upload transaction data, configure parameters, and let the agent handle the reconciliation.
        """
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Configuration")

            with gr.Group():
                gr.Markdown("#### Transaction Data")
                file_input = gr.File(
                    label="Upload CSV/Excel File",
                    file_count="single",
                    file_types=[".csv", ".xls", ".xlsx"],
                    type="filepath",
                )
                gr.Markdown(
                    """
                    **Expected CSV Columns:**
                    - `invoice_amount`: Original invoice amount
                    - `invoice_currency`: Invoice currency code
                    - `received_amount`: Amount received in account
                    - `received_currency`: Received currency code
                    - `transaction_date`: Date of transaction
                    - `reference_id`: Transaction reference
                    """
                )

            with gr.Group():
                gr.Markdown("#### Exchange & Matching")
                with gr.Row():
                    source_currency = gr.Dropdown(
                        label="Source Currency",
                        choices=CURRENCY_CHOICES,
                        value="USD",
                        info="Pick the invoice currency",
                    )
                    target_currency = gr.Dropdown(
                        label="Target Currency",
                        choices=CURRENCY_CHOICES,
                        value="MYR",
                        info="Target settlement currency",
                    )

                exchange_rate = gr.Number(
                    label="Exchange Rate",
                    value=get_exchange_rate("USD", "MYR"),
                    info="Conversion rate (Source → Target)",
                    interactive=False,
                )

                tolerance_threshold = gr.Slider(
                    label="Tolerance Threshold (%)",
                    minimum=0.1,
                    maximum=5.0,
                    step=0.1,
                    value=0.5,
                    info="Acceptable variance for matching",
                )

            with gr.Group():
                gr.Markdown("#### Agent Configuration")
                auto_match = gr.Checkbox(
                    label="Enable Auto-Matching",
                    value=True,
                    info="Automatically match transactions within tolerance",
                )

                logging_level = gr.Radio(
                    label="Logging Level",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    value="INFO",
                    info="Output verbosity",
                )

            with gr.Row():
                process_btn = gr.Button("🚀 Process Reconciliation", variant="primary", scale=2)
                clear_btn = gr.Button("🗑️ Clear All", variant="stop", scale=1)

        with gr.Column(scale=1):
            gr.Markdown("### 📊 Results & Logs")

            with gr.Group():
                gr.Markdown("#### Reconciliation Results")
                results_output = gr.Dataframe(
                    label="Results Table",
                    value=pd.DataFrame(),
                    show_search="search",
                    row_count=25,
                    max_height=500,
                    interactive=False,
                    elem_classes="results-table",
                )
                with gr.Row():
                    prev_page_btn = gr.Button("◀ Previous", variant="secondary")
                    next_page_btn = gr.Button("Next ▶", variant="secondary")
                page_indicator = gr.Markdown("Page 0 of 0")
                with gr.Row():
                    pdf_btn = gr.Button("📄 Export PDF", variant="primary")
                    img_btn = gr.Button("🖼️ Export Image", variant="primary")
                pdf_file = gr.File(label="Download PDF", file_count="single", type="filepath")
                img_file = gr.File(label="Download Image", file_count="single", type="filepath")

            with gr.Group():
                gr.Markdown("#### Agent Log Terminal")
                log_output = gr.Textbox(
                    label="Output Log",
                    lines=15,
                    max_lines=25,
                    value="System ready. Waiting for input...",
                    interactive=False,
                    elem_classes="log-terminal",
                )

    results_store = gr.State(pd.DataFrame())
    current_page = gr.State(1)

    def update_exchange_rate(source_currency_value, target_currency_value):
        return get_exchange_rate(source_currency_value, target_currency_value)

    source_currency.change(
        fn=update_exchange_rate,
        inputs=[source_currency, target_currency],
        outputs=[exchange_rate],
    )

    target_currency.change(
        fn=update_exchange_rate,
        inputs=[source_currency, target_currency],
        outputs=[exchange_rate],
    )

    process_btn.click(
        fn=process_reconciliation,
        inputs=[
            file_input,
            source_currency,
            target_currency,
            exchange_rate,
            tolerance_threshold,
            auto_match,
        ],
        outputs=[
            results_output,
            log_output,
            results_store,
            current_page,
            page_indicator,
            pdf_file,
            img_file,
        ],
    )

    clear_btn.click(
        fn=clear_all,
        outputs=[
            file_input,
            results_output,
            log_output,
            results_store,
            current_page,
            page_indicator,
            pdf_file,
            img_file,
        ],
    )

    def change_page(results_df, current_page, direction):
        if results_df is None or len(results_df) == 0:
            return pd.DataFrame(), 1, "Page 0 of 0"
        next_page = max(1, min(current_page + direction, math.ceil(len(results_df) / 25)))
        page_df, page, total_pages = paginate_dataframe(results_df, next_page)
        return page_df, page, build_page_label(page, total_pages)

    prev_page_btn.click(
        fn=change_page,
        inputs=[results_store, current_page, gr.State(-1)],
        outputs=[results_output, current_page, page_indicator],
    )

    next_page_btn.click(
        fn=change_page,
        inputs=[results_store, current_page, gr.State(1)],
        outputs=[results_output, current_page, page_indicator],
    )

    pdf_btn.click(
        fn=generate_pdf,
        inputs=[results_store],
        outputs=[pdf_file, log_output],
    )

    img_btn.click(
        fn=generate_image,
        inputs=[results_store],
        outputs=[img_file, log_output],
    )

    def init_logs():
        clear_logs()
        return log_message("System initialized. Ready for reconciliation.")

    demo.load(fn=init_logs, outputs=[log_output])


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True,
        theme=gr.themes.Soft(),
    )
