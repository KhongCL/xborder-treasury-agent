import os
import re
import tempfile
from datetime import datetime
from typing import Any
import math

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from tools import convert_currency, search_local_ledger, _DEMO_MYR_RATES
import traceback


LOGS = []


def log_message(message: str) -> str:
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


CURRENCY_CHOICES = sorted(_DEMO_MYR_RATES.keys())


def get_exchange_rate(source_currency: str, target_currency: str) -> float:
    source = str(source_currency).upper().strip() if source_currency else "USD"
    target = str(target_currency).upper().strip() if target_currency else "MYR"

    if source == target:
        return 1.0
    if source not in _DEMO_MYR_RATES or target not in _DEMO_MYR_RATES:
        return 1.0

    source_rate = float(_DEMO_MYR_RATES[source])
    target_rate = float(_DEMO_MYR_RATES[target])
    return round(source_rate / target_rate, 4)


AMOUNT_COLUMNS = (
    "invoice_amount",
    "amount",
    "total_amount",
    "grand_total",
    "amount_paid",
)
CURRENCY_COLUMNS = ("invoice_currency", "currency", "ccy")
ID_COLUMNS = (
    "invoice_id",
    "invoice_number",
    "reference",
    "ref",
    "reference_id",
    "transaction_id",
)
DATE_COLUMNS = (
    "invoice_date",
    "date",
    "payment_date",
    "transaction_date",
)


def select_column(columns: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return None


def create_dataframe_image(df: pd.DataFrame) -> Image.Image:
    if df is None or len(df) == 0:
        raise ValueError("No data available to export")

    font = ImageFont.load_default()
    padding_x = 12
    padding_y = 8

    temp_img = Image.new("RGB", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    bbox = temp_draw.textbbox((0, 0), "Ag", font=font)
    row_height = (bbox[3] - bbox[1]) + padding_y
    header_height = row_height + 4

    col_widths = []
    for column in df.columns:
        bbox = temp_draw.textbbox((0, 0), str(column), font=font)
        max_width = bbox[2] - bbox[0]
        for raw_value in df[column]:
            try:
                if pd.isna(raw_value):
                    value = ""
                else:
                    value = str(raw_value)
            except Exception:
                value = str(raw_value)
            bbox = temp_draw.textbbox((0, 0), value, font=font)
            max_width = max(max_width, bbox[2] - bbox[0])
        col_widths.append(max_width + padding_x)

    total_width = sum(col_widths) + 20
    total_height = header_height + row_height * len(df) + 20

    image = Image.new("RGB", (max(800, total_width), total_height), "white")
    draw = ImageDraw.Draw(image)

    x = 10
    y = 10
    draw.rectangle([x, y, x + total_width - 20, y + header_height], fill="#f0f0f0", outline="black", width=1)
    cell_x = x
    for idx, column in enumerate(df.columns):
        draw.text((cell_x + 4, y + 4), str(column), fill="black", font=font)
        cell_x += col_widths[idx]

    y += header_height
    for _, row in df.iterrows():
        cell_x = x
        for idx, column in enumerate(df.columns):
            raw_value = row[column]
            try:
                text_value = "" if pd.isna(raw_value) else str(raw_value)
            except Exception:
                text_value = str(raw_value)
            draw.text((cell_x + 4, y + 4), text_value, fill="black", font=font)
            cell_x += col_widths[idx]
        y += row_height

    return image


def save_dataframe_image(df: pd.DataFrame, filename: str) -> str:
    image = create_dataframe_image(df)
    filename = str(filename)
    output_path = os.path.join(tempfile.gettempdir(), filename)
    image.save(output_path, format="PNG")
    return output_path


def save_dataframe_pdf(df: pd.DataFrame, filename: str) -> str:
    image = create_dataframe_image(df).convert("RGB")
    filename = str(filename)
    output_path = os.path.join(tempfile.gettempdir(), filename)
    image.save(output_path, format="PDF")
    return output_path


def generate_pdf(results_df: pd.DataFrame) -> tuple[str | None, str]:
    if results_df is None or len(results_df) == 0:
        return None, "ERROR: No reconciliation results available to export."
    try:
        filename = f"reconciliation_{int(datetime.now().timestamp())}.pdf"
        output_path = save_dataframe_pdf(results_df, filename)
        output_path = str(output_path)
        if not os.path.exists(output_path):
            return None, "ERROR: PDF generation failed."
        return output_path, "PDF generated successfully."
    except Exception as exc:
        tb = traceback.format_exc()
        LOGS.append(f"PDF export error: {tb}")
        return None, f"ERROR: PDF export failed - {type(exc).__name__}: {exc!r}\n{tb}"


def generate_image(results_df: pd.DataFrame) -> tuple[str | None, str]:
    if results_df is None or len(results_df) == 0:
        return None, "ERROR: No reconciliation results available to export."
    try:
        filename = f"reconciliation_{int(datetime.now().timestamp())}.png"
        output_path = save_dataframe_image(results_df, filename)
        output_path = str(output_path)
        if not os.path.exists(output_path):
            return None, "ERROR: Image generation failed."
        return output_path, "Image generated successfully."
    except Exception as exc:
        tb = traceback.format_exc()
        LOGS.append(f"Image export error: {tb}")
        return None, f"ERROR: Image export failed - {type(exc).__name__}: {exc!r}\n{tb}"


def process_reconciliation(
    file_upload,
    source_currency: str,
    target_currency: str,
    exchange_rate: float,
    tolerance_threshold: float,
    auto_match: bool,
) -> tuple[pd.DataFrame, str, pd.DataFrame, int, str, None, None]:
    try:
        log_text = log_message(f"Starting reconciliation: {source_currency} → {target_currency}")

        if not file_upload:
            log_text = log_message("ERROR: No file uploaded")
            return pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

        if isinstance(file_upload, str):
            filename = os.path.basename(file_upload)
        else:
            filename = getattr(file_upload, "name", None) or getattr(file_upload, "filename", None) or str(file_upload)

        log_text = log_message(f"Reading file: {filename}")
        df = read_uploaded_csv(file_upload)

        if df is None or len(df) == 0:
            log_text = log_message("ERROR: Uploaded file contains no rows")
            return pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

        log_text = log_message(
            f"File loaded with {len(df)} rows and columns: {', '.join(df.columns.tolist())}"
        )

        normalized_columns = {
            re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_"): col
            for col in df.columns
        }
        amount_col = select_column(normalized_columns, AMOUNT_COLUMNS)
        currency_col = select_column(normalized_columns, CURRENCY_COLUMNS)
        invoice_id_col = select_column(normalized_columns, ID_COLUMNS)
        invoice_date_col = select_column(normalized_columns, DATE_COLUMNS)

        if amount_col is None or currency_col is None:
            missing = []
            if amount_col is None:
                missing.append("invoice_amount / amount")
            if currency_col is None:
                missing.append("invoice_currency / currency")
            log_text = log_message(f"ERROR: Missing required columns: {', '.join(missing)}")
            return pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

        log_text = log_message(f"Exchange rate applied: {exchange_rate}")
        log_text = log_message(f"Tolerance threshold: {tolerance_threshold}%")
        log_text = log_message(f"Auto-matching: {'ENABLED' if auto_match else 'DISABLED'}")

        results = []
        for _, row in df.iterrows():
            invoice_id = (
                str(row[invoice_id_col])
                if invoice_id_col and pd.notna(row[invoice_id_col])
                else None
            )
            invoice_date = (
                str(row[invoice_date_col])
                if invoice_date_col and pd.notna(row[invoice_date_col])
                else None
            )
            invoice_amount = row[amount_col]
            invoice_currency = (
                str(row[currency_col])
                if pd.notna(row[currency_col])
                else source_currency
            )

            exchange_rate_used = float(exchange_rate)
            converted_rm_amount = None
            status = "Conversion Error"
            reason = "Unable to convert invoice amount"
            ledger_transaction_id = None
            ledger_amount_myr = None
            difference_myr = None
            variance_percent = None

            if str(target_currency).upper().strip() == "MYR":
                convert_result = convert_currency(invoice_amount, invoice_currency, target_currency)
                if convert_result.get("success", False):
                    converted_rm_amount = convert_result["converted_rm_amount"]
                    exchange_rate_used = convert_result["rate"]
                    status = "Conversion Only"
                    reason = convert_result.get("calculation", "Converted successfully")
                else:
                    reason = convert_result.get("error")
            else:
                try:
                    converted_rm_amount = round(float(invoice_amount) * exchange_rate_used, 2)
                    status = "Conversion Only"
                    reason = (
                        f"Converted using manual exchange rate {exchange_rate_used:.4f} "
                        f"from {invoice_currency} to {target_currency}"
                    )
                except (TypeError, ValueError) as exc:
                    reason = f"Conversion error: {exc}"

            if converted_rm_amount is not None and auto_match:
                ledger_result = search_local_ledger(
                    converted_rm_amount,
                    invoice_id,
                    tolerance_percent=tolerance_threshold,
                )
                if ledger_result.get("success", False):
                    status = ledger_result.get("status", "Unmatched")
                    reason = ledger_result.get("reason", reason)
                    transaction = ledger_result.get("transaction") or {}
                    ledger_transaction_id = transaction.get("transaction_id")
                    ledger_amount_myr = transaction.get("amount_myr")
                    difference_myr = ledger_result.get("difference_myr")
                    variance_percent = ledger_result.get("variance_percent")
                else:
                    if converted_rm_amount is not None:
                        status = "Ledger Error"
                        reason = ledger_result.get("error")

            results.append(
                {
                    "invoice_id": invoice_id,
                    "invoice_date": invoice_date,
                    "invoice_amount": invoice_amount,
                    "invoice_currency": invoice_currency,
                    "converted_rm_amount": converted_rm_amount,
                    "exchange_rate": exchange_rate_used,
                    "conversion_detail": reason,
                    "status": status,
                    "reason": reason,
                    "ledger_transaction_id": ledger_transaction_id,
                    "ledger_amount_myr": ledger_amount_myr,
                    "difference_myr": difference_myr,
                    "variance_percent": variance_percent,
                }
            )

        results_df = pd.DataFrame(results)
        if len(results_df) == 0:
            log_text = log_message("No valid reconciliation rows were generated.")
        else:
            log_text = log_message(f"Processed {len(results_df)} reconciliation rows.")
            log_text = log_message("Reconciliation process completed successfully")

        page_df, current_page, total_pages = paginate_dataframe(results_df, 1)
        page_label = build_page_label(current_page, total_pages)
        return page_df, log_text, results_df, current_page, page_label, None, None

    except Exception as e:
        log_text = log_message(f"ERROR: {str(e)}")
        return pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None


def clear_logs():
    global LOGS
    LOGS = []
    return ""


def clear_file():
    return None


def clear_all():
    clear_logs()
    return None, pd.DataFrame(), "", pd.DataFrame(), 1, "Page 0 of 0", None, None


def paginate_dataframe(df: pd.DataFrame, page: int, page_size: int = 25) -> tuple[pd.DataFrame, int, int]:
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
