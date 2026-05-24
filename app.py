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
    set_api_key,
)
from ui_components import CSS, build_header, build_configuration_panel, build_results_panel

with gr.Blocks(title="Cross-Border Treasury Reconciliation Agent") as demo:
    # Single top-level row: header, configuration, results
    with gr.Row(elem_id="app-container"):
        with gr.Column(scale=2):
            build_header()

        (
            file_input,
            edit_api_key_btn,
            api_modal,
            api_key_input,
            api_key_save,
            api_key_close,
            source_currency,
            target_currency,
            exchange_rate,
            tolerance_threshold,
            auto_match,
            logging_level,
            process_btn,
            clear_btn,
        ) = build_configuration_panel(CURRENCY_CHOICES, get_exchange_rate)

        (
            results_output,
            prev_page_btn,
            page_indicator,
            next_page_btn,
            pdf_btn,
            img_btn,
            pdf_file,
            img_file,
            log_output,
        ) = build_results_panel()

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

    # Wire the API key popup toggles and save/close actions
    # Show modal when clicking Edit button
    edit_api_key_btn.click(fn=lambda: gr.update(visible=True), inputs=None, outputs=[api_modal])
    # Close modal
    api_key_close.click(fn=lambda: gr.update(visible=False), inputs=None, outputs=[api_modal])

    # Save API key and hide modal (wrapper to also return a visibility update)
    def save_key_and_close(new_key: str):
        msg = set_api_key(new_key)
        return msg, gr.update(visible=False)

    api_key_save.click(fn=save_key_and_close, inputs=[api_key_input], outputs=[log_output, api_modal])


if __name__ == "__main__":
    demo.launch(
        theme=gr.themes.Soft(primary_hue="blue"),
        css=CSS,
    )
