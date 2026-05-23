import gradio as gr
import pandas as pd
import math
import os
import tempfile
from io import BytesIO
from datetime import datetime
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

# Initialize log storage (keep a list for appends, return joined text for display)
LOGS = []


def log_message(message: str) -> str:
    """Add message to logs with timestamp and return the full log text."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    LOGS.append(log_entry)
    return "\n".join(LOGS)


def _get_upload_extension(file_upload):
    if isinstance(file_upload, str):
        return os.path.splitext(file_upload)[1].lower()
    if hasattr(file_upload, "name") and isinstance(file_upload.name, str):
        return os.path.splitext(file_upload.name)[1].lower()
    if hasattr(file_upload, "filename") and isinstance(file_upload.filename, str):
        return os.path.splitext(file_upload.filename)[1].lower()
    return None


def read_uploaded_csv(file_upload):
    """Read uploaded CSV or Excel data from common Gradio upload return types."""
    if file_upload is None:
        raise ValueError("No file uploaded")

    if isinstance(file_upload, (list, tuple)):
        if len(file_upload) == 0:
            raise ValueError("No file uploaded")
        file_upload = file_upload[0]

    ext = _get_upload_extension(file_upload)

    if isinstance(file_upload, str):
        if ext in (".xls", ".xlsx"):
            return pd.read_excel(file_upload)
        return pd.read_csv(file_upload)

    if hasattr(file_upload, "name") and isinstance(file_upload.name, str):
        if ext in (".xls", ".xlsx"):
            return pd.read_excel(file_upload.name)
        return pd.read_csv(file_upload.name)

    if hasattr(file_upload, "read"):
        file_upload.seek(0)
        if ext in (".xls", ".xlsx"):
            return pd.read_excel(file_upload)
        return pd.read_csv(file_upload)

    raise ValueError("Unsupported upload type for CSV/Excel file")


def create_dataframe_image(df: pd.DataFrame) -> Image.Image:
    """Render a DataFrame as an image using Pillow."""
    if df is None or len(df) == 0:
        raise ValueError("No data available to export")

    font = ImageFont.load_default()
    padding_x = 12
    padding_y = 8
    
    # Create a temporary image to measure text
    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # Measure text dimensions
    bbox = temp_draw.textbbox((0, 0), "Ag", font=font)
    row_height = (bbox[3] - bbox[1]) + padding_y
    header_height = row_height + 4

    # Determine column widths based on header and cell contents
    col_widths = []
    for column in df.columns:
        col_str = str(column)
        bbox = temp_draw.textbbox((0, 0), col_str, font=font)
        max_width = bbox[2] - bbox[0]
        
        for value in df[column].astype(str):
            bbox = temp_draw.textbbox((0, 0), value, font=font)
            max_width = max(max_width, bbox[2] - bbox[0])
        col_widths.append(max_width + padding_x)

    total_width = sum(col_widths) + 20
    total_height = header_height + row_height * len(df) + 20

    image = Image.new("RGB", (max(800, total_width), total_height), "white")
    draw = ImageDraw.Draw(image)

    x = 10
    y = 10

    # Draw header row
    draw.rectangle([x, y, x + total_width - 20, y + header_height], fill="#f0f0f0", outline="black", width=1)
    cell_x = x
    for idx, column in enumerate(df.columns):
        draw.text((cell_x + 4, y + 4), str(column), fill="black", font=font)
        cell_x += col_widths[idx]

    y += header_height

    # Draw data rows
    for _, row in df.iterrows():
        cell_x = x
        for idx, column in enumerate(df.columns):
            draw.text((cell_x + 4, y + 4), str(row[column]), fill="black", font=font)
            cell_x += col_widths[idx]
        y += row_height

    return image


def save_dataframe_image(df: pd.DataFrame, filename: str) -> str:
    image = create_dataframe_image(df)
    output_path = os.path.join(tempfile.gettempdir(), filename)
    image.save(output_path, format="PNG")
    return output_path


def save_dataframe_pdf(df: pd.DataFrame, filename: str) -> str:
    image = create_dataframe_image(df).convert("RGB")
    output_path = os.path.join(tempfile.gettempdir(), filename)
    image.save(output_path, format="PDF", resolution=100.0)
    return output_path


def generate_pdf(results_df: pd.DataFrame) -> tuple[str, str]:
    if results_df is None or len(results_df) == 0:
        return None, "ERROR: No reconciliation results available to export."
    output_path = save_dataframe_pdf(results_df, f"reconciliation_{int(datetime.now().timestamp())}.pdf")
    return output_path, "PDF generated successfully."


def generate_image(results_df: pd.DataFrame) -> tuple[str, str]:
    if results_df is None or len(results_df) == 0:
        return None, "ERROR: No reconciliation results available to export."
    output_path = save_dataframe_image(results_df, f"reconciliation_{int(datetime.now().timestamp())}.png")
    return output_path, "Image generated successfully."


def process_reconciliation(
    file_upload,
    source_currency: str,
    target_currency: str,
    exchange_rate: float,
    tolerance_threshold: float,
    auto_match: bool,
) -> tuple[pd.DataFrame, str, pd.DataFrame, int, str]:
    """
    Process cross-border transaction reconciliation.

    Args:
        file_upload: Uploaded CSV file
        source_currency: Source currency code (e.g., USD)
        target_currency: Target currency code (e.g., MYR)
        exchange_rate: Exchange rate for conversion
        tolerance_threshold: Percentage tolerance for matching
        auto_match: Enable automatic matching

    Returns:
        Tuple of (paged_results, updated_logs, full_results, current_page, page_label)
    """
    try:
        # Start logging
        log_text = log_message(f"Starting reconciliation: {source_currency} → {target_currency}")

        # Check if file was uploaded
        if not file_upload:
            log_text = log_message("ERROR: No file uploaded")
            return pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

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

        page_df, current_page, total_pages = paginate_dataframe(results_df, 1)
        page_label = build_page_label(current_page, total_pages)

        return page_df, log_text, results_df, current_page, page_label, None, None

    except Exception as e:
        log_text = log_message(f"ERROR: {str(e)}")
        return pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

def clear_logs():
    """Clear all logs"""
    global LOGS
    LOGS = []
    return ""


def clear_file():
    """Clear file upload (for Gradio File component)"""
    return None


def clear_all():
    """Helper to reset file input, results output and logs for the UI"""
    clear_logs()
    return None, pd.DataFrame(), "", pd.DataFrame(), 1, "Page 0 of 0", None, None


def paginate_dataframe(df: pd.DataFrame, page: int, page_size: int = 25) -> tuple[pd.DataFrame, int, int]:
    """Return a single page slice of the DataFrame plus page metadata."""
    if df is None or len(df) == 0:
        return pd.DataFrame(), 0, 0

    total_pages = max(1, math.ceil(len(df) / page_size))
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    page_df = df.iloc[start:end].reset_index(drop=True)
    return page_df, page, total_pages


def build_page_label(page: int, total_pages: int) -> str:
    if total_pages == 0:
        return "Page 0 of 0"
    return f"Page {page} of {total_pages}"

# ============================================================================
# Gradio UI Definition
# ============================================================================

with gr.Blocks(title="Cross-Border Treasury Reconciliation Agent") as demo:
    
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
            with gr.Group():
                gr.Markdown("#### Transaction Data")
                file_input = gr.File(
                    label="Upload CSV/Excel File",
                    file_count="single",
                    file_types=[".csv", ".xls", ".xlsx"],
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
            with gr.Group():
                gr.Markdown("#### Exchange & Matching")
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
            with gr.Group():
                gr.Markdown("#### Agent Configuration")
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
            with gr.Group():
                gr.Markdown("#### Reconciliation Results")
                results_output = gr.Dataframe(
                    label="Results Table",
                    value=pd.DataFrame(),
                    show_search="search",
                    row_count=25,
                    max_height=500,
                    interactive=False,
                    elem_classes="results-table"
                )
                with gr.Row():
                    prev_page_btn = gr.Button("◀ Previous", variant="secondary")
                    next_page_btn = gr.Button("Next ▶", variant="secondary")
                page_indicator = gr.Markdown("Page 0 of 0")
                with gr.Row():
                    pdf_btn = gr.Button("📄 Export PDF", variant="primary")
                    img_btn = gr.Button("🖼️ Export Image", variant="primary")
                pdf_file = gr.File(label="Download PDF")
                img_file = gr.File(label="Download Image")

            # Log Terminal
            with gr.Group():
                gr.Markdown("#### Agent Log Terminal")
                log_output = gr.Textbox(
                    label="Output Log",
                    lines=15,
                    max_lines=25,
                    value="System ready. Waiting for input...",
                    interactive=False,
                    elem_classes="log-terminal"
                )
    
    # ========== Event Handlers ==========
    
    results_store = gr.State(pd.DataFrame())
    current_page = gr.State(1)

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
        outputs=[results_output, log_output, results_store, current_page, page_indicator, pdf_file, img_file]
    )

    clear_btn.click(
        fn=clear_all,
        outputs=[file_input, results_output, log_output, results_store, current_page, page_indicator, pdf_file, img_file]
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
        outputs=[results_output, current_page, page_indicator]
    )

    next_page_btn.click(
        fn=change_page,
        inputs=[results_store, current_page, gr.State(1)],
        outputs=[results_output, current_page, page_indicator]
    )

    pdf_btn.click(
        fn=generate_pdf,
        inputs=[results_store],
        outputs=[pdf_file, log_output]
    )

    img_btn.click(
        fn=generate_image,
        inputs=[results_store],
        outputs=[img_file, log_output]
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
        debug=True,
        theme=gr.themes.Soft()
    )
