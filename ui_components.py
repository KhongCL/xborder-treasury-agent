import gradio as gr

THEME_TOGGLE_JS = """
() => {
  const syncToggle = (theme) => {
    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;
    toggle.textContent = theme === "dark" ? "☀" : "☾";
    toggle.setAttribute("data-theme", theme);
    toggle.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
  };
  const params = new URLSearchParams(window.location.search);
  const currentTheme = params.get("__theme") === "dark" ? "dark" : "light";
  syncToggle(currentTheme);
}
"""

CSS = """
html,
body {
  background: var(--body-background-fill, #e8eefc);
  color: var(--body-text-color, #0f172a);
  margin: 0;
}
.app-shell {
  min-height: 100vh;
  background: inherit;
}
.gradio-container {
  max-width: 100% !important;
  width: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  width: 100%;
  padding: 18px 28px;
  margin: 0;
  border-radius: 0;
  background: var(--block-background-fill, #f8fbff);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  border-bottom: 1px solid var(--block-border-color, rgba(148, 163, 184, 0.18));
  box-sizing: border-box;
}
.app-header__brand {
  display: flex;
  align-items: center;
  gap: 14px;
}
.app-header__mark {
  font-size: 1.9rem;
  line-height: 1;
}
.app-header__title {
  margin: 0;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.03em;
}
.app-header__subtitle {
  margin: 4px 0 0;
  color: var(--body-text-color-subdued, #475569);
  font-size: 0.98rem;
}
.app-header__toggle {
  width: 48px;
  height: 48px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(135deg, #dbeafe, #bfdbfe);
  color: #0f172a;
  font-size: 1.35rem;
  cursor: pointer;
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.18);
}
.app-header__toggle:hover {
  transform: translateY(-1px);
}
.app-main {
  padding: 24px 22px 30px;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
.app-main > .gr-group {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
}
.app-main .gr-form,
.app-main .gr-block,
.app-main .gr-box,
.app-main .gr-panel,
.app-main .gr-row,
#app-container,
#app-container.row,
#app-container.svelte-7xavid,
#app-container > .gr-column,
#app-container > .gr-form,
#app-container > div {
  background: transparent !important;
  background-color: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
.left-panel,
.right-panel,
.left-panel > div,
.right-panel > div,
.left-panel .gr-column,
.right-panel .gr-column,
.left-panel .gr-group,
.right-panel .gr-group,
.left-panel .gr-box,
.right-panel .gr-box,
.left-panel .gr-block,
.right-panel .gr-block {
  background: transparent !important;
  background-color: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
#app-container {
  width: 100%;
  gap: 26px;
  align-items: flex-start;
  padding: 0 !important;
}
.section-panel,
.summary-card {
  border-radius: 24px;
  background: transparent !important;
  box-shadow: none !important;
  border: 0 !important;
}
.summary-card {
  padding: 20px 22px;
  min-height: 120px;
}
.section-panel {
  padding: 10px 18px 18px;
}
.section-panel > .gr-markdown {
  margin: 0 0 10px 0 !important;
}
.section-panel > .gr-markdown h3,
.section-panel > .gr-markdown h4,
.section-panel > .gr-markdown p strong {
  margin: 0 !important;
  color: var(--body-text-color, #0f172a) !important;
  font-weight: 700;
  letter-spacing: -0.02em;
}
.section-panel > .gr-markdown h3 {
  font-size: 1.05rem;
}
.section-panel > .gr-markdown h4 {
  font-size: 0.95rem;
}
.column-panel {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.gr-file {
  min-height: 190px;
  border-radius: 20px;
  background: var(--block-background-fill, #f8fbff);
  border: 2px dashed rgba(59, 130, 246, 0.28);
}
.gr-file,
.gr-textbox,
.gr-number,
.gr-dropdown,
.gr-radio,
.gr-checkbox,
.gr-accordion,
.gr-dataframe {
  background: transparent !important;
}
.gr-file .file-button {
  border-radius: 16px;
}
.gr-file .wrap,
.gr-textbox,
.gr-number,
.gr-dropdown,
.gr-accordion,
.gr-dataframe {
  box-shadow: none !important;
}
.section-panel .gr-group,
.section-panel .gr-box,
.section-panel .gr-block {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
.results-table .output_dataframe {
  border-radius: 18px !important;
}
.results-table .wrap,
.log-terminal,
.download-file {
  background: transparent !important;
}
.log-terminal,
.log-terminal > div,
.log-terminal .wrap,
.log-terminal .scroll-hide {
  background: var(--block-background-fill, #f8fbff) !important;
  border-radius: 14px !important;
}
.gr-button {
  border-radius: 16px;
  min-width: 140px;
}
.gr-button.primary {
  color: white;
}
.process-button,
.process-button button {
  border-radius: 999px !important;
}
.process-button button {
  min-height: 52px;
  padding: 0 28px;
  font-weight: 600;
}
.log-terminal textarea {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  background: var(--input-background-fill, #f8fafc);
  color: var(--body-text-color, #0f172a);
  border: 1px solid var(--input-border-color, rgba(148, 163, 184, 0.35));
  border-radius: 14px;
}
.log-terminal textarea,
.log-terminal textarea:disabled,
.log-terminal textarea[disabled] {
  background: var(--input-background-fill, #f8fafc) !important;
  color: var(--body-text-color, #0f172a) !important;
}
.dark .log-terminal textarea,
.dark .log-terminal textarea:disabled,
.dark .log-terminal textarea[disabled],
[data-theme="dark"] .log-terminal textarea,
[data-theme="dark"] .log-terminal textarea:disabled,
[data-theme="dark"] .log-terminal textarea[disabled] {
  background: #0b1220 !important;
  color: #e2e8f0 !important;
}
.download-file {
  min-height: 0 !important;
  border: 2px solid #10b981 !important;
  background: #ecfdf5 !important;
  color: #065f46 !important;
  font-weight: 700 !important;
  border-radius: 16px !important;
  transform: scale(1.02);
  transition: all 0.2s ease-in-out;
  box-shadow: 0 8px 24px rgba(16, 185, 129, 0.25) !important;
}
.download-file:hover {
  transform: scale(1.04);
  box-shadow: 0 12px 28px rgba(16, 185, 129, 0.35) !important;
}

/* Fix for Red Button */
.gr-button.stop, .stop, .stop button, button.stop {
    background: #dc2626 !important;
    border-color: #dc2626 !important;
    color: white !important;
}
.gr-button.stop:hover, .stop:hover, .stop button:hover, button.stop:hover {
    background: #b91c1c !important;
}

/* Fix for Dark Mode Checkbox Visibility */
.dark .gr-checkbox span, .dark .gr-checkbox label, [data-theme="dark"] .gr-checkbox label {
    color: white !important;
}
.dark .gr-checkbox input[type="checkbox"]:not(:checked), [data-theme="dark"] .gr-checkbox input[type="checkbox"]:not(:checked) {
    border: 1px solid #475569 !important;
    background: #1e293b !important;
}
.dark .download-file, [data-theme="dark"] .download-file {
  border-color: #10b981 !important;
  background: rgba(16, 185, 129, 0.15) !important;
  color: #34d399 !important; /* Light green text for dark mode */
}
.left-panel,
.right-panel {
  min-width: 0;
}
@media (max-width: 900px) {
  .app-header {
    padding: 16px 18px;
  }
  .app-header__title {
    font-size: 1.55rem;
  }
  .app-header__subtitle {
    font-size: 0.9rem;
  }
  .app-main {
    padding: 18px 16px 24px;
  }
  #app-container {
    gap: 20px;
  }
}
.dark .app-header,
[data-theme="dark"] .app-header {
  box-shadow: none;
}
.dark .app-header__toggle,
[data-theme="dark"] .app-header__toggle {
  background: linear-gradient(135deg, #1e293b, #334155);
  color: #f8fafc;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.35);
}
.dark .gr-file,
[data-theme="dark"] .gr-file {
  border-color: rgba(96, 165, 250, 0.45);
}
.dark .gr-dataframe table,
.dark .gr-dataframe .table-wrap,
.dark .gr-dataframe .wrap,
[data-theme="dark"] .gr-dataframe table,
[data-theme="dark"] .gr-dataframe .table-wrap,
[data-theme="dark"] .gr-dataframe .wrap {
  background: #0b1220 !important;
  color: #e2e8f0 !important;
}
.dark .gr-dataframe th,
.dark .gr-dataframe td,
[data-theme="dark"] .gr-dataframe th,
[data-theme="dark"] .gr-dataframe td {
  background: #0b1220 !important;
  color: #e2e8f0 !important;
  border-color: rgba(71, 85, 105, 0.45) !important;
}
.dark input:not([type="checkbox"]):not([type="radio"]),
.dark textarea,
.dark select,
[data-theme="dark"] input:not([type="checkbox"]):not([type="radio"]),
[data-theme="dark"] textarea,
[data-theme="dark"] select {
  background: transparent !important;
  color: #e2e8f0 !important;
  border-color: rgba(71, 85, 105, 0.7) !important;
}
.dark input[type="number"],
[data-theme="dark"] input[type="number"] {
  color-scheme: dark;
}
.dark input[type="number"]::-webkit-inner-spin-button,
.dark input[type="number"]::-webkit-outer-spin-button,
[data-theme="dark"] input[type="number"]::-webkit-inner-spin-button,
[data-theme="dark"] input[type="number"]::-webkit-outer-spin-button {
  filter: invert(1);
  opacity: 0.85;
}
.dark .gr-button.secondary,
[data-theme="dark"] .gr-button.secondary {
  background: #334155 !important;
  color: #e2e8f0 !important;
}
"""


def build_header():
    gr.HTML(
        """
        <header class="app-header">
          <div class="app-header__brand">
            <div class="app-header__mark">🌍</div>
            <div>
              <h1 class="app-header__title">Cross-Border Treasury Reconciliation Agent</h1>
              <p class="app-header__subtitle">Upload invoices, run reconciliation, and export results from one workspace.</p>
            </div>
          </div>
          <button
            id="theme-toggle"
            class="app-header__toggle"
            type="button"
            aria-label="Toggle theme"
            data-theme="light"
            onclick="(function(){
                document.body.classList.toggle('dark');
                const isDark = document.body.classList.contains('dark');
                const toggle = document.getElementById('theme-toggle');
                toggle.textContent = isDark ? '☀' : '☾';
            })()"
          >☾</button>
        </header>
        """
    )


def build_configuration_panel(CURRENCY_CHOICES, get_exchange_rate):
  with gr.Column(scale=1, elem_classes="left-panel"):
    with gr.Group(elem_classes="section-panel"):
      gr.Markdown("### Configuration")

      with gr.Group():
        gr.Markdown("#### Transaction Data")
        file_input = gr.File(
          label="Upload CSV/Excel/PDF File",
          file_count="single",
          file_types=[".csv", ".xls", ".xlsx", ".pdf"],
          type="filepath",
          show_label=False,
        )

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

      confirm_clear = gr.Checkbox(label="Unlock 'Clear All' button", value=False)
      
      with gr.Row():
        process_btn = gr.Button("🚀 Process Reconciliation", variant="primary", elem_classes="process-button")
        clear_btn = gr.Button("🗑️ Clear All", variant="stop", elem_classes="stop")

  return (
    file_input,
    source_currency,
    target_currency,
    exchange_rate,
    tolerance_threshold,
    confirm_clear,
    process_btn,
    clear_btn,
  )


def build_results_panel():
    with gr.Column(scale=1, elem_classes="right-panel"):
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
                show_label=False,
            )

            with gr.Row():
                prev_page_btn = gr.Button("◀ Previous", variant="secondary")
                page_indicator = gr.Markdown("Page 0 of 0")
                next_page_btn = gr.Button("Next ▶", variant="secondary")

            with gr.Row():
              pdf_btn = gr.DownloadButton("📄 Export PDF", variant="primary")
              img_btn = gr.DownloadButton("🖼️ Export Image", variant="primary")

        with gr.Group(elem_classes="section-panel"):
            gr.Markdown("### Agent Log")
            log_output = gr.Textbox(
                label="Output Log",
                lines=16,
                value="System ready. Waiting for input...",
                interactive=False,
                elem_classes="log-terminal",
                show_label=False,
            )

    return (
        results_output,
        prev_page_btn,
        page_indicator,
        next_page_btn,
        pdf_btn,
        img_btn,
        log_output,
    )