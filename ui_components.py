import gradio as gr

CSS = """
body {
  background: #eef2ff;
}
.gradio-container {
  max-width: 1300px;
  margin: auto;
  padding: 18px 22px 30px;
}
#app-container {
  display: grid;
  gap: 26px;
}
.header-panel,
.section-panel,
.summary-card {
  border-radius: 24px;
  background: white;
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
}
.header-panel {
  padding: 28px 32px;
}
.summary-card {
  padding: 20px 22px;
  min-height: 120px;
  border: 1px solid rgba(148, 163, 184, 0.18);
}
.header-panel h1 {
  margin-bottom: 10px;
  font-size: 2.15rem;
}
.header-panel p {
  color: #475569;
  font-size: 1rem;
  line-height: 1.7;
  max-width: 820px;
}
.section-panel {
  padding: 26px;
}
.column-panel {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.gr-file {
  min-height: 190px;
  border-radius: 20px;
  background: #f8fbff;
  border: 2px dashed rgba(59, 130, 246, 0.28);
}
.gr-file .file-button {
  border-radius: 16px;
}
.results-table .output_dataframe {
  border-radius: 18px !important;
}
.gr-button {
  border-radius: 999px;
  min-width: 140px;
}
.gr-button.primary {
  color: white;
}
.log-terminal textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: #f8fafc;
  border-radius: 14px;
}
"""


def build_header():
    with gr.Column(scale=2):
        with gr.Group(elem_classes="header-panel"):
            gr.Markdown(
                """
                # 🌍 Cross-Border Treasury Reconciliation Agent

                Upload invoices, run smart reconciliation, and export polished results in one clean dashboard.
                Supported upload formats: `.csv`, `.xls`, `.xlsx`, `.pdf`.
                """
            )


def build_configuration_panel(CURRENCY_CHOICES, get_exchange_rate):
  with gr.Column(scale=1):
    with gr.Group(elem_classes="section-panel"):
      gr.Markdown("### Configuration")

      with gr.Group():
        gr.Markdown("#### Transaction Data")
        file_input = gr.File(
          label="Upload CSV/Excel/PDF File",
          file_count="single",
          file_types=[".csv", ".xls", ".xlsx", ".pdf"],
          type="filepath",
        )

      # Admin: API key editing is in a hidden popup-like panel toggled by a button
      with gr.Row():
        edit_api_key_btn = gr.Button("Edit API Key", variant="secondary")

      with gr.Column(visible=False, elem_id="api-modal") as api_modal:
        with gr.Group(elem_classes="section-panel"):
          gr.Markdown("### API Key (private)")
          api_key_input = gr.Textbox(
            label="API Key (private)",
            placeholder="Paste SHOOTS/OpenAI API key here",
            type="password",
            interactive=True,
          )
          with gr.Row():
            api_key_save = gr.Button("Save API Key", variant="primary")
            api_key_close = gr.Button("Close", variant="secondary")

      with gr.Accordion("Expected CSV Columns", open=False):
        gr.Markdown(
          """
          - `invoice_amount`: Original invoice amount
          - `invoice_currency`: Invoice currency code
          - `received_amount`: Amount received in account
          - `received_currency`: Received currency code
          - `transaction_date`: Date of transaction
          - `reference_id`: Transaction reference
          """
        )

      with gr.Row():
        with gr.Column():
          source_currency = gr.Dropdown(
            label="Source Currency",
            choices=CURRENCY_CHOICES,
            value="USD",
            info="Pick the invoice currency",
          )
        with gr.Column():
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
        value=3.0,
        info="Acceptable variance for matching",
      )

      with gr.Row():
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
        process_btn = gr.Button("🚀 Process Reconciliation", variant="primary")
        clear_btn = gr.Button("🗑️ Clear All", variant="secondary")

  return (
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
  )


def build_results_panel():
    with gr.Column(scale=1):
        with gr.Group(elem_classes="section-panel"):
            gr.Markdown("### Results")

            results_output = gr.Dataframe(
                label="Results Table",
                value=None,
                show_search="search",
                row_count=18,
                max_height=440,
                interactive=False,
                elem_classes="results-table",
            )

            with gr.Row():
                prev_page_btn = gr.Button("◀ Previous", variant="secondary")
                page_indicator = gr.Markdown("Page 0 of 0")
                next_page_btn = gr.Button("Next ▶", variant="secondary")

            with gr.Row():
                pdf_btn = gr.Button("📄 Export PDF", variant="primary")
                img_btn = gr.Button("🖼️ Export Image", variant="primary")

            pdf_file = gr.File(label="Download PDF", file_count="single", type="filepath")
            img_file = gr.File(label="Download Image", file_count="single", type="filepath")

        with gr.Group(elem_classes="section-panel"):
            gr.Markdown("### Agent Log")
            log_output = gr.Textbox(
                label="Output Log",
                lines=16,
                max_lines=18,
                value="System ready. Waiting for input...",
                interactive=False,
                elem_classes="log-terminal",
            )

    return (
        results_output,
        prev_page_btn,
        page_indicator,
        next_page_btn,
        pdf_btn,
        img_btn,
        pdf_file,
        img_file,
        log_output,
    )
