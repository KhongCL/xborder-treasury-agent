from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "demo_invoices"


INVOICES = [
    {
        "filename": "invoice_perfect_match_INV-001.pdf",
        "scenario": "Perfect Match",
        "accent": colors.HexColor("#1f6feb"),
        "vendor": "ACME EXPORT LTD",
        "vendor_subtitle": "Cross-border consulting and procurement",
        "invoice_id": "INV-001",
        "date": "2026-05-24",
        "due_date": "2026-05-31",
        "bill_to": "APU Demo SME Sdn Bhd",
        "currency": "USD",
        "amount": "100.00",
        "description": "International consulting invoice",
        "reference_note": "Bank reference expected: INV-001 PAYMENT",
        "footer": "Expected result: RM425.00 received exactly in local ledger.",
    },
    {
        "filename": "invoice_close_match_INV-002.pdf",
        "scenario": "Close Match - Bank Fee",
        "accent": colors.HexColor("#d97706"),
        "vendor": "GLOBAL TECH SOLUTIONS PTE LTD",
        "vendor_subtitle": "Cloud software licensing and support",
        "invoice_id": "INV-002",
        "date": "2026-05-24",
        "due_date": "2026-05-31",
        "bill_to": "APU Demo SME Sdn Bhd",
        "currency": "USD",
        "amount": "100.00",
        "description": "Software licensing fee",
        "reference_note": "Intermediary bank fees may be deducted during transfer.",
        "footer": "Expected result: RM416.50 received; 2.00% fee variance.",
    },
    {
        "filename": "invoice_no_match_INV-003.pdf",
        "scenario": "No Match",
        "accent": colors.HexColor("#7c3aed"),
        "vendor": "BERLIN DATA CORP GMBH",
        "vendor_subtitle": "European data infrastructure services",
        "invoice_id": "INV-003",
        "date": "2026-05-22",
        "due_date": "2026-05-29",
        "bill_to": "APU Demo SME Sdn Bhd",
        "currency": "EUR",
        "amount": "200.00",
        "description": "Cloud hosting services",
        "reference_note": "No matching bank reference exists in the demo ledger.",
        "footer": "Expected result: no matching transaction in local ledger.",
    },
]


def money(currency: str, amount: str) -> str:
    return f"{currency} {amount}"


def draw_label_value(page: canvas.Canvas, label: str, value: str, x: float, y: float) -> None:
    page.setFont("Helvetica-Bold", 8)
    page.setFillColor(colors.HexColor("#64748b"))
    page.drawString(x, y, label.upper())
    page.setFont("Helvetica", 10)
    page.setFillColor(colors.HexColor("#111827"))
    page.drawString(x, y - 12, value)


def generate_invoice(data: dict[str, str]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / data["filename"]
    page = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    accent = data["accent"]

    page.setFillColor(accent)
    page.rect(0, height - 28 * mm, width, 28 * mm, fill=True, stroke=False)

    page.setFillColor(colors.white)
    page.setFont("Helvetica-Bold", 22)
    page.drawString(20 * mm, height - 17 * mm, "INVOICE")
    page.setFont("Helvetica", 9)
    page.drawRightString(width - 20 * mm, height - 12 * mm, "SYNTHETIC DEMO")
    page.setFont("Helvetica-Bold", 11)
    page.drawRightString(width - 20 * mm, height - 20 * mm, data["scenario"])

    y = height - 43 * mm
    page.setFillColor(colors.HexColor("#111827"))
    page.setFont("Helvetica-Bold", 17)
    page.drawString(20 * mm, y, data["vendor"])
    page.setFont("Helvetica", 9)
    page.setFillColor(colors.HexColor("#475569"))
    page.drawString(20 * mm, y - 13, data["vendor_subtitle"])

    draw_label_value(page, "Invoice Number", data["invoice_id"], 132 * mm, y)
    draw_label_value(page, "Invoice Date", data["date"], 132 * mm, y - 34)
    draw_label_value(page, "Due Date", data["due_date"], 132 * mm, y - 68)

    page.setStrokeColor(colors.HexColor("#e5e7eb"))
    page.line(20 * mm, y - 84, width - 20 * mm, y - 84)

    y -= 110
    draw_label_value(page, "Bill To", data["bill_to"], 20 * mm, y)
    draw_label_value(page, "Currency", data["currency"], 92 * mm, y)
    draw_label_value(page, "Payment Terms", "Net 7 days", 132 * mm, y)

    y -= 58
    page.setFillColor(colors.HexColor("#f8fafc"))
    page.roundRect(20 * mm, y - 80, width - 40 * mm, 95, 5, fill=True, stroke=False)
    page.setStrokeColor(colors.HexColor("#cbd5e1"))
    page.roundRect(20 * mm, y - 80, width - 40 * mm, 95, 5, fill=False, stroke=True)

    page.setFillColor(accent)
    page.rect(20 * mm, y - 3, width - 40 * mm, 24, fill=True, stroke=False)
    page.setFillColor(colors.white)
    page.setFont("Helvetica-Bold", 9)
    page.drawString(25 * mm, y + 5, "DESCRIPTION")
    page.drawRightString(154 * mm, y + 5, "AMOUNT")
    page.drawRightString(width - 25 * mm, y + 5, "LINE TOTAL")

    page.setFillColor(colors.HexColor("#111827"))
    page.setFont("Helvetica", 10)
    page.drawString(25 * mm, y - 25, data["description"])
    page.drawRightString(154 * mm, y - 25, money(data["currency"], data["amount"]))
    page.drawRightString(width - 25 * mm, y - 25, money(data["currency"], data["amount"]))

    page.setStrokeColor(colors.HexColor("#e2e8f0"))
    page.line(25 * mm, y - 44, width - 25 * mm, y - 44)
    page.setFont("Helvetica-Bold", 12)
    page.drawRightString(154 * mm, y - 67, "Grand Total:")
    page.drawRightString(width - 25 * mm, y - 67, money(data["currency"], data["amount"]))

    y -= 120
    page.setFillColor(colors.HexColor("#0f172a"))
    page.setFont("Helvetica-Bold", 10)
    page.drawString(20 * mm, y, "Payment Notes")
    page.setFillColor(colors.HexColor("#334155"))
    page.setFont("Helvetica", 9)
    page.drawString(20 * mm, y - 16, data["reference_note"])
    page.drawString(20 * mm, y - 30, "Please include the invoice number in all remittance references.")

    page.setFillColor(colors.HexColor("#f1f5f9"))
    page.roundRect(20 * mm, 27 * mm, width - 40 * mm, 26 * mm, 5, fill=True, stroke=False)
    page.setFillColor(colors.HexColor("#334155"))
    page.setFont("Helvetica-Bold", 9)
    page.drawString(25 * mm, 42 * mm, "Demo expectation")
    page.setFont("Helvetica", 9)
    page.drawString(25 * mm, 34 * mm, data["footer"])

    page.setFillColor(colors.HexColor("#94a3b8"))
    page.setFont("Helvetica", 8)
    page.drawString(20 * mm, 15 * mm, "Generated for AI Marathon 2026 Global Treasury Agent prototype.")

    page.save()
    return path


def main() -> None:
    for invoice in INVOICES:
        print(generate_invoice(invoice))


if __name__ == "__main__":
    main()
