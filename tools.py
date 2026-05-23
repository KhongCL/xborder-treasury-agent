"""Tools for extracting structured information from treasury documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd


_AMOUNT_COLUMNS = (
    "invoice_amount",
    "total_amount",
    "grand_total",
    "amount_paid",
    "amount",
    "total",
)
_CURRENCY_COLUMNS = ("invoice_currency", "currency", "ccy")
_ID_COLUMNS = ("invoice_id", "invoice_number", "reference", "ref")
_DATE_COLUMNS = ("invoice_date", "date", "payment_date")
_SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".pdf", ".txt", ".md"}
_DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent / "data" / "local_ledger.csv"
_LEDGER_COLUMNS = ("transaction_id", "date", "reference", "amount_myr")

_CURRENCY_TOKEN = r"(?:MYR|RM|USD|US\$|\$|EUR|€|SGD|S\$|GBP|£)"
_NUMBER_TOKEN = r"[0-9][0-9,]*(?:\.[0-9]{1,2})?"


def extract_invoice_data(file_path: str) -> dict[str, Any]:
    """Extract an invoice total and currency from a PDF, spreadsheet, or text file.

    The returned dictionary is safe for an agent tool call: failures are returned
    as structured results instead of crashing the workflow.
    """
    path = Path(file_path)

    if not path.exists():
        return _failure(f"Invoice file not found: {path}")
    if path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(_SUPPORTED_SUFFIXES))
        return _failure(f"Unsupported invoice type '{path.suffix}'. Use: {supported}.")

    try:
        if path.suffix.lower() in {".csv", ".xlsx"}:
            result = _extract_from_table(_read_table(path))
        else:
            result = _extract_from_text(_read_document_text(path))
    except (OSError, ValueError, ImportError) as exc:
        return _failure(str(exc))

    if result is None:
        return _failure(
            "Could not find an invoice total and currency. Include fields such as "
            "'Total: USD 100.00' or columns named 'amount' and 'currency'."
        )

    amount, currency, invoice_id, invoice_date = result
    return {
        "success": True,
        "source_file": path.name,
        "source_format": path.suffix.lower().lstrip("."),
        "invoice_id": invoice_id,
        "invoice_date": invoice_date,
        "amount": amount,
        "currency": currency,
        # These aliases align with the current AgentState field names.
        "invoice_amount": amount,
        "invoice_currency": currency,
    }


def search_local_ledger(
    converted_amount: float,
    invoice_id: str | None = None,
    ledger_path: str | None = None,
    tolerance_percent: float = 3.0,
) -> dict[str, Any]:
    """Find an RM bank deposit matching a converted invoice total.

    Providing ``invoice_id`` keeps independent demo invoices from matching each
    other's deposits. A difference within ``tolerance_percent`` is treated as a
    likely cross-border transfer fee rather than a failed payment.
    """
    try:
        expected_amount = round(float(converted_amount), 2)
        tolerance = float(tolerance_percent)
    except (TypeError, ValueError):
        return _failure("Converted amount and tolerance must be numeric values.")

    if expected_amount <= 0:
        return _failure("Converted amount must be greater than zero.")
    if tolerance < 0:
        return _failure("Tolerance percent cannot be negative.")

    path = Path(ledger_path) if ledger_path else _DEFAULT_LEDGER_PATH
    if not path.exists():
        return _failure(f"Bank ledger file not found: {path}")

    try:
        frame = pd.read_csv(path)
    except (OSError, ValueError) as exc:
        return _failure(f"Could not read bank ledger: {exc}")

    columns = {_normalize_column(column): column for column in frame.columns}
    missing = [column for column in _LEDGER_COLUMNS if column not in columns]
    if missing:
        return _failure(
            "Bank ledger is missing required columns: " + ", ".join(missing)
        )

    transactions = frame.copy()
    amount_column = columns["amount_myr"]
    reference_column = columns["reference"]
    transactions[amount_column] = pd.to_numeric(
        transactions[amount_column], errors="coerce"
    )
    transactions = transactions.dropna(subset=[amount_column])

    if invoice_id:
        transactions = transactions[
            transactions[reference_column]
            .astype(str)
            .str.contains(re.escape(invoice_id), case=False, na=False)
        ]
        if transactions.empty:
            return _unmatched_result(
                expected_amount,
                tolerance,
                invoice_id,
                f"No bank transaction references invoice {invoice_id}.",
            )

    if transactions.empty:
        return _unmatched_result(
            expected_amount,
            tolerance,
            invoice_id,
            "No valid transactions were available in the bank ledger.",
        )

    transactions["_difference_myr"] = (
        transactions[amount_column] - expected_amount
    ).abs()
    transactions["_variance_percent"] = (
        transactions["_difference_myr"] / expected_amount * 100
    )
    best = transactions.sort_values("_difference_myr").iloc[0]

    difference = round(float(best["_difference_myr"]), 2)
    variance = round(float(best["_variance_percent"]), 2)
    actual_amount = round(float(best[amount_column]), 2)
    transaction = {
        "transaction_id": str(best[columns["transaction_id"]]),
        "date": str(best[columns["date"]]),
        "reference": str(best[reference_column]),
        "amount_myr": actual_amount,
    }

    if difference <= 0.01:
        status = "Matched"
        reason = "Exact MYR amount match found in local bank ledger."
    elif variance <= tolerance:
        status = "Matched with Fee Variance"
        direction = "below" if actual_amount < expected_amount else "above"
        reason = (
            f"Deposit is RM {difference:.2f} {direction} the expected amount "
            f"({variance:.2f}% variance), within the {tolerance:.2f}% fee tolerance."
        )
    else:
        status = "Unmatched"
        reason = (
            f"Closest deposit varies by RM {difference:.2f} ({variance:.2f}%), "
            f"exceeding the {tolerance:.2f}% fee tolerance."
        )

    return {
        "success": True,
        "status": status,
        "invoice_id": invoice_id,
        "expected_amount_myr": expected_amount,
        "difference_myr": difference,
        "variance_percent": variance,
        "tolerance_percent": tolerance,
        "transaction": transaction,
        "reason": reason,
    }


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path)


def _read_document_text(path: Path) -> str:
    if path.suffix.lower() in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")

    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError(
                "PDF extraction requires pypdf. Install project requirements first."
            ) from exc
        pages = [page.extract_text() or "" for page in PdfReader(str(path)).pages]
        return "\n".join(pages)

    raise ValueError(
        "Image OCR is not enabled in this prototype. Use a text-based PDF, CSV, or Excel invoice."
    )


def _extract_from_table(
    frame: pd.DataFrame,
) -> tuple[float, str, str | None, str | None] | None:
    if frame.empty:
        return None

    normalized = {_normalize_column(column): column for column in frame.columns}
    amount_column = _select_column(normalized, _AMOUNT_COLUMNS)
    currency_column = _select_column(normalized, _CURRENCY_COLUMNS)

    if amount_column and currency_column:
        for _, row in frame.iterrows():
            amount = _parse_number(row[amount_column])
            currency = _normalize_currency(str(row[currency_column]))
            if amount is not None and currency:
                return (
                    amount,
                    currency,
                    _row_value(row, normalized, _ID_COLUMNS),
                    _row_value(row, normalized, _DATE_COLUMNS),
                )

    table_text = "\n".join(
        " ".join(str(value) for value in row if pd.notna(value))
        for row in frame.itertuples(index=False, name=None)
    )
    return _extract_from_text(table_text)


def _extract_from_text(
    text: str,
) -> tuple[float, str, str | None, str | None] | None:
    currency_first_pattern = re.compile(
        rf"(?P<prefix>{_CURRENCY_TOKEN})\s*(?P<amount>{_NUMBER_TOKEN})",
        re.IGNORECASE,
    )

    match = None
    for label in (
        r"grand\s+total",
        r"total\s+due",
        r"invoice\s+total",
        r"amount\s+paid",
        r"total",
        r"amount",
    ):
        labelled_pattern = re.compile(
            rf"(?<![A-Za-z]){label}\s*[:=-]?\s*(?P<prefix>{_CURRENCY_TOKEN})?\s*"
            rf"(?P<amount>{_NUMBER_TOKEN})\s*(?P<suffix>{_CURRENCY_TOKEN})?",
            re.IGNORECASE,
        )
        match = labelled_pattern.search(text)
        if match:
            break

    match = match or currency_first_pattern.search(text)
    if not match:
        return None

    amount = _parse_number(match.group("amount"))
    currency_token = match.groupdict().get("prefix") or match.groupdict().get("suffix")
    currency = _normalize_currency(currency_token or "") or _currency_in_text(text)
    if amount is None or currency is None:
        return None

    return amount, currency, _extract_invoice_id(text), _extract_date(text)


def _select_column(columns: dict[str, Any], candidates: tuple[str, ...]) -> Any | None:
    for candidate in candidates:
        if candidate in columns:
            return columns[candidate]
    return None


def _row_value(
    row: pd.Series, columns: dict[str, Any], candidates: tuple[str, ...]
) -> str | None:
    column = _select_column(columns, candidates)
    if column is None or pd.isna(row[column]):
        return None
    return str(row[column])


def _normalize_column(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _parse_number(value: Any) -> float | None:
    match = re.search(_NUMBER_TOKEN, str(value))
    if not match:
        return None
    return float(match.group(0).replace(",", ""))


def _normalize_currency(value: str) -> str | None:
    token = value.upper().replace(" ", "")
    return {
        "RM": "MYR",
        "MYR": "MYR",
        "USD": "USD",
        "US$": "USD",
        "$": "USD",
        "EUR": "EUR",
        "€": "EUR",
        "SGD": "SGD",
        "S$": "SGD",
        "GBP": "GBP",
        "£": "GBP",
    }.get(token)


def _currency_in_text(text: str) -> str | None:
    match = re.search(_CURRENCY_TOKEN, text, re.IGNORECASE)
    return _normalize_currency(match.group(0)) if match else None


def _extract_invoice_id(text: str) -> str | None:
    match = re.search(
        r"(?:invoice\s*(?:id|no|number|#)|reference|ref)\s*[:#-]?\s*([A-Z0-9-]+)",
        text,
        re.IGNORECASE,
    )
    return match.group(1) if match else None


def _extract_date(text: str) -> str | None:
    match = re.search(
        r"\b(?:20\d{2}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]20\d{2})\b",
        text,
    )
    return match.group(0) if match else None


def _failure(error: str) -> dict[str, Any]:
    return {"success": False, "error": error}


def _unmatched_result(
    expected_amount: float,
    tolerance: float,
    invoice_id: str | None,
    reason: str,
) -> dict[str, Any]:
    return {
        "success": True,
        "status": "Unmatched",
        "invoice_id": invoice_id,
        "expected_amount_myr": expected_amount,
        "difference_myr": None,
        "variance_percent": None,
        "tolerance_percent": tolerance,
        "transaction": None,
        "reason": reason,
    }
