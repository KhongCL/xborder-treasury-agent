"""Google Workspace integration tools for reconciliation outputs (OAuth)."""

from __future__ import annotations

import asyncio
import os
import pickle
from pathlib import Path
from typing import Any

import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _failure(error: str) -> dict[str, Any]:
    return {"success": False, "error": error}


def _normalize_results(results_df: Any) -> pd.DataFrame:
    if isinstance(results_df, pd.DataFrame):
        return results_df
    if isinstance(results_df, list):
        return pd.DataFrame(results_df)
    if results_df is None:
        return pd.DataFrame()
    return pd.DataFrame([results_df])


def _get_google_creds() -> tuple[Any | None, str | None]:
    client_secret_path = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "client_secret.json")
    token_path = os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "token.pickle")

    client_file = Path(client_secret_path)
    if not client_file.exists():
        return None, f"OAuth client secret not found: {client_file}"

    creds = None
    token_file = Path(token_path)
    if token_file.exists():
        try:
            with token_file.open("rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None

    try:
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return None, "Google OAuth support requires google-auth-oauthlib."

    if creds and creds.valid:
        return creds, None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_file), SCOPES)
        creds = flow.run_local_server(port=0)

    try:
        with token_file.open("wb") as token:
            pickle.dump(creds, token)
    except Exception:
        pass

    return creds, None


async def save_report_to_sheets(
    results_df: Any,
    spreadsheet_id: str | None = None,
    worksheet_name: str | None = None,
) -> dict[str, Any]:
    """Append reconciliation results to a Google Sheet tab using OAuth."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _save_report_to_sheets_sync, results_df, spreadsheet_id, worksheet_name
    )


def _save_report_to_sheets_sync(
    results_df: Any,
    spreadsheet_id: str | None,
    worksheet_name: str | None,
) -> dict[str, Any]:
    frame = _normalize_results(results_df)
    if frame.empty:
        return _failure("No results available to write to Google Sheets.")

    sheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
    if not sheet_id:
        return _failure("GOOGLE_SHEETS_SPREADSHEET_ID is not set.")

    tab_name = worksheet_name or os.getenv("GOOGLE_SHEETS_WORKSHEET") or "Reconciliation"

    try:
        import gspread
        from gspread.exceptions import WorksheetNotFound
    except ImportError:
        return _failure("Google Sheets support requires gspread. Install requirements.")

    creds, error = _get_google_creds()
    if error:
        return _failure(error)

    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id)
        try:
            worksheet = sheet.worksheet(tab_name)
        except WorksheetNotFound:
            worksheet = sheet.add_worksheet(
                title=tab_name,
                rows=max(1000, len(frame) + 10),
                cols=max(10, len(frame.columns) + 5),
            )

        header = worksheet.row_values(1)
        if not header:
            worksheet.append_row(list(frame.columns), value_input_option="USER_ENTERED")

        cleaned = frame.where(pd.notna(frame), "")
        rows = cleaned.values.tolist()
        if rows:
            worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    except Exception as exc:
        return _failure(f"Google Sheets update failed: {exc}")

    return {
        "success": True,
        "spreadsheet_id": sheet_id,
        "worksheet_name": tab_name,
        "rows_appended": len(frame),
    }


async def upload_invoice_to_drive(
    file_path: str,
    folder_id: str | None = None,
) -> dict[str, Any]:
    """Upload a file to a Google Drive folder using OAuth."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _upload_invoice_to_drive_sync, file_path, folder_id
    )


def _upload_invoice_to_drive_sync(
    file_path: str,
    folder_id: str | None,
) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return _failure(f"File not found: {path}")

    target_folder = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not target_folder:
        return _failure("GOOGLE_DRIVE_FOLDER_ID is not set.")

    creds, error = _get_google_creds()
    if error:
        return _failure(error)

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        return _failure(
            "Google Drive support requires google-api-python-client. Install requirements."
        )

    try:
        service = build("drive", "v3", credentials=creds)
        media = MediaFileUpload(str(path), resumable=False)
        metadata = {"name": path.name, "parents": [target_folder]}
        created = (
            service.files()
            .create(body=metadata, media_body=media, fields="id,name")
            .execute()
        )
    except Exception as exc:
        return _failure(f"Google Drive upload failed: {exc}")

    return {
        "success": True,
        "file_id": created.get("id"),
        "file_name": created.get("name", path.name),
        "folder_id": target_folder,
    }
