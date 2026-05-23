import gradio as gr
import pandas as pd
from typing import Tuple
from datetime import datetime
import os

# Initialize log output
logs = []

def log_message(message: str):
    """Add message to logs with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    logs.append(log_entry)
    return "\n".join(logs)

def process_reconciliation(
    file_upload,
    source_currency: str,
    target_currency: str,
    exchange_rate: float,
    tolerance_threshold: float,
    auto_match: bool,
    log_output: str
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
    global logs
    
    try:
        # Log the start of processing
        logs = log_message(f"Starting reconciliation: {source_currency} → {target_currency}")
        
        # Check if file was uploaded
        if file_upload is None:
            logs = log_message("ERROR: No file uploaded")
            return "No data to process", "\n".join(logs)
        
        # Read the uploaded file
        logs = log_message(f"Reading file: {file_upload.name}")
        df = pd.read_csv(file_upload)
        
        # Validate required columns
        logs = log_message(f"File loaded with {len(df)} rows and columns: {', '.join(df.columns.tolist())}")
        
        # Simulate reconciliation processing
        logs = log_message(f"Exchange rate applied: {exchange_rate}")
        logs = log_message(f"Tolerance threshold: {tolerance_threshold}%")
        logs = log_message(f"Auto-matching: {'ENABLED' if auto_match else 'DISABLED'}")
        
        # Create a sample results DataFrame
        results_df = df.copy() if len(df) > 0 else pd.DataFrame()
        
        if len(results_df) > 0:
            results_df['Status'] = 'Pending'
            results_df['Match'] = False
            logs = log_message(f"Processing {len(results_df)} transactions...")
            logs = log_message("Reconciliation process completed successfully")
        
        # Convert results to HTML table
        results_html = results_df.to_html() if len(results_df) > 0 else "<p>No transactions to display</p>"
        
        return results_html, "\n".join(logs)
    
    except Exception as e:
        logs = log_message(f"ERROR: {str(e)}")
        return f"<p style='color:red'>Error: {str(e)}</p>", "\n".join(logs)

def clear_logs():
    """Clear all logs"""
    global logs
    logs = []
    return "", ""

def clear_file():
    """Clear file upload"""
    return None

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
            log_output
        ],
        outputs=[results_output, log_output]
    )
    
    clear_btn.click(
        fn=lambda: (clear_file(), clear_logs(), "", ""),
        outputs=[file_input, log_output, results_output, log_output]
    )
    
    # Initialize log on load
    demo.load(
        fn=lambda: "[2026-05-23 00:00:00] System initialized. Ready for reconciliation.",
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
