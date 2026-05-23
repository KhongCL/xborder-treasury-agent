import tempfile
import unittest
from pathlib import Path

from tools import extract_invoice_data


class ExtractInvoiceDataTests(unittest.TestCase):
    def test_extracts_structured_csv_invoice(self):
        with tempfile.TemporaryDirectory() as directory:
            invoice = Path(directory) / "invoice.csv"
            invoice.write_text(
                "invoice_id,invoice_date,currency,amount\n"
                "INV-001,2026-05-24,USD,100.00\n",
                encoding="utf-8",
            )

            result = extract_invoice_data(str(invoice))

        self.assertTrue(result["success"])
        self.assertEqual(result["invoice_id"], "INV-001")
        self.assertEqual(result["invoice_date"], "2026-05-24")
        self.assertEqual(result["invoice_currency"], "USD")
        self.assertEqual(result["invoice_amount"], 100.0)

    def test_extracts_labelled_text_total_and_normalizes_rm(self):
        with tempfile.TemporaryDirectory() as directory:
            invoice = Path(directory) / "receipt.txt"
            invoice.write_text(
                "Invoice Number: MY-009\nDate: 24/05/2026\nGrand Total: RM 421.50\n",
                encoding="utf-8",
            )

            result = extract_invoice_data(str(invoice))

        self.assertTrue(result["success"])
        self.assertEqual(result["invoice_id"], "MY-009")
        self.assertEqual(result["invoice_currency"], "MYR")
        self.assertEqual(result["invoice_amount"], 421.5)

    def test_prefers_grand_total_over_subtotal(self):
        with tempfile.TemporaryDirectory() as directory:
            invoice = Path(directory) / "receipt.txt"
            invoice.write_text(
                "Subtotal: USD 98.00\nTotal: USD 100.00\nGrand Total: USD 102.00\n",
                encoding="utf-8",
            )

            result = extract_invoice_data(str(invoice))

        self.assertTrue(result["success"])
        self.assertEqual(result["invoice_amount"], 102.0)

    def test_returns_agent_readable_error_for_missing_file(self):
        result = extract_invoice_data("does-not-exist.pdf")

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])


if __name__ == "__main__":
    unittest.main()
