import os
import re
import tempfile
from datetime import datetime
from typing import Any
import math
import asyncio
import json

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# Removed convert_currency and search_local_ledger imports here,
# because the Agent will now handle them autonomously through agent.py.
from tools import _DEMO_MYR_RATES
import traceback
from langchain_core.messages import HumanMessage
import importlib
import sys
import os

LOGS = []


def set_api_key(new_key: str) -> str:
    """Save a new API key to .env, set it in the current process env, and reload agent module.

    Returns a status message suitable for showing in the UI log.
    """
    try:
        if not new_key or not isinstance(new_key, str) or new_key.strip() == "":
            return "ERROR: API key is empty."
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        # Read existing .env lines (if any)
        existing = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                existing = f.readlines()

        key_line = f"SHOOTS_API_KEY={new_key.strip()}\n"
        found = False
        for i, line in enumerate(existing):
            if line.startswith("SHOOTS_API_KEY="):
                existing[i] = key_line
                found = True
                break

        if not found:
            existing.append(key_line)

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(existing)

        # Set environment variables for current process
        os.environ["SHOOTS_API_KEY"] = new_key.strip()
        os.environ["OPENAI_API_KEY"] = new_key.strip()

        # Try to reload agent module so next reconciliation picks up the new key
        try:
            if "agent" in sys.modules:
                importlib.reload(sys.modules["agent"])
            else:
                importlib.import_module("agent")
        except Exception as exc:
            return f"WARNING: API saved to .env, env updated, but reloading agent failed: {exc}"

        return "API key updated and agent reloaded successfully."
    except Exception as exc:
        return f"ERROR updating API key: {exc}"

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
        if ext in (".xls", ".xlsx"): return pd.read_excel(file_upload)
        return pd.read_csv(file_upload)
    if hasattr(file_upload, "name") and isinstance(file_upload.name, str):
        if ext in (".xls", ".xlsx"): return pd.read_excel(file_upload.name)
        return pd.read_csv(file_upload.name)
    if hasattr(file_upload, "read"):
        file_upload.seek(0)
        if ext in (".xls", ".xlsx"): return pd.read_excel(file_upload)
        return pd.read_csv(file_upload)
    
    raise ValueError("Unsupported upload type for CSV/Excel file")

CURRENCY_CHOICES = sorted(_DEMO_MYR_RATES.keys())

def get_exchange_rate(source_currency: str, target_currency: str) -> float:
    source = str(source_currency).upper().strip() if source_currency else "USD"
    target = str(target_currency).upper().strip() if target_currency else "MYR"
    if source == target: return 1.0
    if source not in _DEMO_MYR_RATES or target not in _DEMO_MYR_RATES: return 1.0
    return round(float(_DEMO_MYR_RATES[source]) / float(_DEMO_MYR_RATES[target]), 4)

AMOUNT_COLUMNS = ("invoice_amount", "amount", "total_amount", "grand_total", "amount_paid")
CURRENCY_COLUMNS = ("invoice_currency", "currency", "ccy")
ID_COLUMNS = ("invoice_id", "invoice_number", "reference", "ref", "reference_id", "transaction_id")
DATE_COLUMNS = ("invoice_date", "date", "payment_date", "transaction_date")

def select_column(columns: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return None

# --- Image and PDF Generation Helpers remain exactly the same ---
def create_dataframe_image(df: pd.DataFrame) -> Image.Image:
    if df is None or len(df) == 0: raise ValueError("No data available to export")
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
            value = "" if pd.isna(raw_value) else str(raw_value)
            bbox = temp_draw.textbbox((0, 0), value, font=font)
            max_width = max(max_width, bbox[2] - bbox[0])
        col_widths.append(max_width + padding_x)

    total_width = sum(col_widths) + 20
    total_height = header_height + row_height * len(df) + 20
    image = Image.new("RGB", (max(800, total_width), total_height), "white")
    draw = ImageDraw.Draw(image)

    x = y = 10
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
            text_value = "" if pd.isna(raw_value) else str(raw_value)
            draw.text((cell_x + 4, y + 4), text_value, fill="black", font=font)
            cell_x += col_widths[idx]
        y += row_height
    return image

def save_dataframe_image(df: pd.DataFrame, filename: str) -> str:
    output_path = os.path.join(tempfile.gettempdir(), str(filename))
    create_dataframe_image(df).save(output_path, format="PNG")
    return output_path

def save_dataframe_pdf(df: pd.DataFrame, filename: str) -> str:
    output_path = os.path.join(tempfile.gettempdir(), str(filename))
    create_dataframe_image(df).convert("RGB").save(output_path, format="PDF")
    return output_path

def generate_pdf(results_df: pd.DataFrame) -> tuple[str | None, str]:
    if results_df is None or len(results_df) == 0:
        return None, "ERROR: No reconciliation results available to export."
    try:
        filename = f"reconciliation_{int(datetime.now().timestamp())}.pdf"
        output_path = save_dataframe_pdf(results_df, filename)
        if not os.path.exists(output_path): return None, "ERROR: PDF generation failed."
        return output_path, "PDF generated successfully."
    except Exception as exc:
        return None, f"ERROR: PDF export failed - {exc}"

def generate_image(results_df: pd.DataFrame) -> tuple[str | None, str]:
    if results_df is None or len(results_df) == 0:
        return None, "ERROR: No reconciliation results available to export."
    try:
        filename = f"reconciliation_{int(datetime.now().timestamp())}.png"
        output_path = save_dataframe_image(results_df, filename)
        if not os.path.exists(output_path): return None, "ERROR: Image generation failed."
        return output_path, "Image generated successfully."
    except Exception as exc:
        return None, f"ERROR: Image export failed - {exc}"

# --- THE NEW ASYNC AGENT INTEGRATION ---

async def process_reconciliation(
    file_upload,
    source_currency: str,
    target_currency: str,
    exchange_rate: float,
    tolerance_threshold: float,
    auto_match: bool,
):
    """
    This is the async generator function that bridges Gradio to LangGraph.
    It yields UI updates (dataframes and logs) in real-time as the agent thinks.
    """
    log_text = log_message(f"Starting Agentic Reconciliation...")
    yield pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

    if not file_upload:
        log_text = log_message("ERROR: No file uploaded")
        yield pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None
        return

    # Extract file path
    if isinstance(file_upload, str):
        filepath = file_upload
    else:
        filepath = getattr(file_upload, "name", None) or getattr(file_upload, "filename", None) or str(file_upload)

    log_text = log_message(f"Uploading file: {os.path.basename(filepath)} to Agent Context.")
    yield pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

    # Construct the prompt instructing the LangGraph agent
    prompt = (
        f"I have an invoice located at '{filepath}'. "
        f"Please extract the data, convert it to {target_currency}, and search the local ledger "
        f"('./data/local_ledger.csv') for a match with a {tolerance_threshold}% tolerance."
    )

    initial_state = {
        "messages": [HumanMessage(content=prompt)],
        "invoice_amount": 0.0,
        "invoice_currency": "",
        "converted_rm_amount": 0.0,
        "reconciliation_status": "unprocessed"
    }

    results = [] # We will store the final agent conclusions here

    try:
        # If agent is already loaded, reload it so any updated env vars are picked up.
        if "agent" in sys.modules:
            agent_module = importlib.reload(sys.modules["agent"])
        else:
            agent_module = importlib.import_module("agent")
        app = getattr(agent_module, "app")
    except Exception as exc:
        log_text = log_message(f"ERROR: Failed to initialize agent - {exc}")
        yield pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None
        return

    # STREAM THE AGENT THOUGHTS LIVE
    try:
        async for event in app.astream(initial_state):
            for node_name, state_update in event.items():
                messages = state_update.get("messages", [])
                for msg in messages:
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        # The agent decided to use a tool
                        tool_name = msg.tool_calls[0]['name']
                        log_text = log_message(f"⚙️ Agent executing tool: {tool_name}...")
                        yield pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None
                    
                    elif hasattr(msg, "content") and msg.content:
                        # Check if this is the final summary (it usually won't have <think> tags if it's the end)
                        if "<think>" in msg.content:
                            clean_thought = msg.content.split("</think>")[0].replace("<think>", "").strip()
                            log_text = log_message(f"🧠 Agent Reasoning: {clean_thought[:100]}...") # truncate for UI
                        else:
                            log_text = log_message(f"✅ Agent Final Conclusion: \n{msg.content}")
                        
                        yield pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None

                        # If this is the final output, let's parse the last known state to populate the UI table
                        # (In a real production app, we would extract structured JSON, but we will mock the table row for the hackathon UI based on the tool outputs)
                        
                # Update the State tracking variables based on tool outputs
                if node_name == "tools":
                     for msg in messages:
                         if hasattr(msg, "content"):
                             try:
                                 # The tools return JSON strings, so we can parse them to build the UI Table!
                                 tool_data = json.loads(msg.content)
                                 if "invoice_amount" in tool_data:
                                     initial_state["invoice_amount"] = tool_data["invoice_amount"]
                                     initial_state["invoice_currency"] = tool_data.get("currency", "USD")
                                 if "converted_rm_amount" in tool_data:
                                     initial_state["converted_rm_amount"] = tool_data["converted_rm_amount"]
                                 if "status" in tool_data:
                                     initial_state["reconciliation_status"] = tool_data["status"]
                                     
                                     # We reached the final tool, build the row!
                                     results.append({
                                         "invoice_id": tool_data.get("invoice_id", "UNKNOWN"),
                                         "invoice_amount": initial_state["invoice_amount"],
                                         "invoice_currency": initial_state["invoice_currency"],
                                         "converted_rm_amount": initial_state["converted_rm_amount"],
                                         "status": tool_data["status"],
                                         "reason": tool_data.get("reason", ""),
                                         "variance_percent": tool_data.get("variance_percent", 0.0)
                                     })
                             except:
                                 pass
    except Exception as exc:
        error_message = str(exc)
        if "usage cap exceeded" in error_message.lower() or "402" in error_message:
            user_message = (
                "ERROR: AI subscription usage cap exceeded. "
                "Please add balance to the Shoots/OpenAI account or use a valid paid API key."
            )
        else:
            user_message = f"ERROR: AI agent failed - {error_message}"
        log_text = log_message(user_message)
        yield pd.DataFrame(), log_text, pd.DataFrame(), 1, "Page 0 of 0", None, None
        return

    # Final UI Table Update
    results_df = pd.DataFrame(results)
    page_df, current_page, total_pages = paginate_dataframe(results_df, 1)
    page_label = build_page_label(current_page, total_pages)
    
    log_text = log_message("Reconciliation workflow completed.")
    yield page_df, log_text, results_df, current_page, page_label, None, None


def clear_logs():
    global LOGS
    LOGS = []
    return ""

def clear_file(): return None

def clear_all():
    clear_logs()
    return None, pd.DataFrame(), "", pd.DataFrame(), 1, "Page 0 of 0", None, None

def paginate_dataframe(df: pd.DataFrame, page: int, page_size: int = 25) -> tuple[pd.DataFrame, int, int]:
    if df is None or len(df) == 0: return pd.DataFrame(), 0, 0
    total_pages = max(1, math.ceil(len(df) / page_size))
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end].reset_index(drop=True), page, total_pages

def build_page_label(page: int, total_pages: int) -> str:
    if total_pages == 0: return "Page 0 of 0"
    return f"Page {page} of {total_pages}"