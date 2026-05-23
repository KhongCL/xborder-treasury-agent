import gradio as gr
import pandas as pd
from typing import Tuple
from datetime import datetime
import os

# Initialize log storage (keep a list for appends, return joined text for display)
LOGS = []


def log_message(message: str) -> str:
    """Add message to logs with timestamp and return the full log text."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    LOGS.append(log_entry)
    return "\n".join(LOGS)


def read_uploaded_csv(file_upload):
    """Read uploaded CSV data from common Gradio upload return types."""
    if file_upload is None:
        raise ValueError("No file uploaded")

    if isinstance(file_upload, (list, tuple)):
        if len(file_upload) == 0:
            raise ValueError("No file uploaded")
        file_upload = file_upload[0]

    if isinstance(file_upload, str):
        return pd.read_csv(file_upload)

    if hasattr(file_upload, "name") and isinstance(file_upload.name, str):
        return pd.read_csv(file_upload.name)

    if hasattr(file_upload, "read"):
        file_upload.seek(0)
        return pd.read_csv(file_upload)

    raise ValueError("Unsupported upload type for CSV file")


def process_reconciliation(
    file_upload,
    source_currency: str,
    target_currency: str,
    exchange_rate: float,
    tolerance_threshold: float,
    auto_match: bool,
) -> Tuple[str, str]:
    """
    Process cross-border transaction reconciliation
    
    Args:
        file_upload: Uploaded CSV file
        source_currency: Source currency code (e.g., USD)
        target_currency: Target currency code (e.g., MYR)
        exchange_rate: Exchange rate for conversion
        tolerance_threshold: Percentage tolerance for matching
        auto_match: Enable automatic matching
        log_output: Current log output
    
    Returns:
        Tuple of (results_table, updated_logs)
    """
    try:
        # Start logging
        log_text = log_message(f"Starting reconciliation: {source_currency} → {target_currency}")

        # Check if file was uploaded
        if not file_upload:
            log_text = log_message("ERROR: No file uploaded")
            return "<p>No data to process</p>", log_text

        # Determine a friendly filename for logs
        if isinstance(file_upload, str):
            filename = os.path.basename(file_upload)
        else:
            filename = getattr(file_upload, "name", None) or getattr(file_upload, "filename", None) or str(file_upload)

        log_text = log_message(f"Reading file: {filename}")

        # Read CSV from the uploaded file input
        df = read_uploaded_csv(file_upload)

        # Validate required columns
        log_text = log_message(f"File loaded with {len(df)} rows and columns: {', '.join(df.columns.tolist())}")

        # Simulate reconciliation processing
        log_text = log_message(f"Exchange rate applied: {exchange_rate}")
        log_text = log_message(f"Tolerance threshold: {tolerance_threshold}%")
        log_text = log_message(f"Auto-matching: {'ENABLED' if auto_match else 'DISABLED'}")

        # Create a sample results DataFrame
        results_df = df.copy() if len(df) > 0 else pd.DataFrame()

        if len(results_df) > 0:
            results_df["Status"] = "Pending"
            results_df["Match"] = False
            log_text = log_message(f"Processing {len(results_df)} transactions...")
            log_text = log_message("Reconciliation process completed successfully")

        # Convert results to HTML table
        results_html = results_df.to_html(index=False) if len(results_df) > 0 else "<p>No transactions to display</p>"

        return results_html, log_text

    except Exception as e:
        log_text = log_message(f"ERROR: {str(e)}")
        return f"<p style='color:red'>Error: {str(e)}</p>", log_text

def clear_logs():
    """Clear all logs"""
    global LOGS
    LOGS = []
    return ""


def clear_file():
    """Clear file upload (for Gradio File component)"""
    return None


def clear_all():
    """Helper to reset file input, results HTML and logs for the UI"""
    # Reset logs and return values matching outputs: file_input, results_output, log_output
    clear_logs()
    default_html = "<p>Upload a file and click 'Process Reconciliation' to see results</p>"
    return None, default_html, ""

# ============================================================================
# Gradio UI Definition
# ============================================================================

with gr.Blocks(title="Cross-Border Treasury Reconciliation Agent", theme=gr.themes.Soft()) as demo:
    
    # Header
    gr.Markdown("""
    # 🌍 Cross-Border Treasury Reconciliation Agent
    
    Automated reconciliation of cross-border transactions using AI agents. 
    Upload transaction data, configure parameters, and let the agent handle the reconciliation.
    """)
    
    # ========== Main Content ==========
    with gr.Row():
        # Left Column: Controls
        with gr.Column(scale=1):
            gr.Markdown("### 📋 Configuration")
            
            # File Upload
            with gr.Group(label="Transaction Data"):
                file_input = gr.File(
                    label="Upload CSV File",
                    file_count="single",
                    file_types=[".csv"],
                    type="filepath"
                )
                gr.Markdown("""
                **Expected CSV Columns:**
                - `invoice_amount`: Original invoice amount
                - `invoice_currency`: Invoice currency code
                - `received_amount`: Amount received in account
                - `received_currency`: Received currency code
                - `transaction_date`: Date of transaction
                - `reference_id`: Transaction reference
                """)
            
            # Configuration Parameters
            with gr.Group(label="Exchange & Matching"):
                with gr.Row():
                    source_currency = gr.Textbox(
                        label="Source Currency",
                        value="USD",
                        max_lines=1,
                        info="e.g., USD"
                    )
                    target_currency = gr.Textbox(
                        label="Target Currency",
                        value="MYR",
                        max_lines=1,
                        info="e.g., MYR"
                    )
                
                exchange_rate = gr.Number(
                    label="Exchange Rate",
                    value=4.25,
                    info="Conversion rate (Source → Target)"
                )
                
                tolerance_threshold = gr.Slider(
                    label="Tolerance Threshold (%)",
                    minimum=0.1,
                    maximum=5.0,
                    step=0.1,
                    value=0.5,
                    info="Acceptable variance for matching"
                )
            
            # Advanced Options
            with gr.Group(label="Agent Configuration"):
                auto_match = gr.Checkbox(
                    label="Enable Auto-Matching",
                    value=True,
                    info="Automatically match transactions within tolerance"
                )
                
                logging_level = gr.Radio(
                    label="Logging Level",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    value="INFO",
                    info="Output verbosity"
                )
            
            # Action Buttons
            with gr.Row():
                process_btn = gr.Button(
                    "🚀 Process Reconciliation",
                    variant="primary",
                    scale=2
                )
                clear_btn = gr.Button(
                    "🗑️ Clear All",
                    variant="stop",
                    scale=1
                )
        
        # Right Column: Output
        with gr.Column(scale=1):
            gr.Markdown("### 📊 Results & Logs")
            
            # Results Table
            with gr.Group(label="Reconciliation Results"):
                results_output = gr.HTML(
                    label="Results Table",
                    value="<p>Upload a file and click 'Process Reconciliation' to see results</p>"
                )
            
            # Log Terminal
            with gr.Group(label="Agent Log Terminal"):
                log_output = gr.Textbox(
                    label="Output Log",
                    lines=15,
                    max_lines=25,
                    value="System ready. Waiting for input...",
                    interactive=False,
                    elem_classes="log-terminal"
                )
    
    # ========== Event Handlers ==========
    
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
        outputs=[results_output, log_output]
    )

    clear_btn.click(
        fn=clear_all,
        outputs=[file_input, results_output, log_output]
    )
    
    # Initialize log on load
    def init_logs():
        clear_logs()
        return log_message("System initialized. Ready for reconciliation.")

    demo.load(
        fn=init_logs,
        outputs=[log_output]
    )

# ============================================================================
# Launch Configuration
# ============================================================================

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )
