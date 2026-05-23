import tempfile
import unittest
from pathlib import Path

from tools import extract_invoice_data, search_local_ledger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = PROJECT_ROOT / "data" / "local_ledger.csv"


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


class SearchLocalLedgerTests(unittest.TestCase):
    def test_returns_exact_match_for_invoice_reference(self):
        result = search_local_ledger(425.0, "INV-001", str(LEDGER_PATH))

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "Matched")
        self.assertEqual(result["transaction"]["transaction_id"], "TXN001")
        self.assertEqual(result["difference_myr"], 0.0)

    def test_flags_small_difference_as_fee_variance(self):
        result = search_local_ledger(425.0, "INV-002", str(LEDGER_PATH))

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "Matched with Fee Variance")
        self.assertEqual(result["transaction"]["transaction_id"], "TXN002")
        self.assertEqual(result["difference_myr"], 3.5)
        self.assertLess(result["variance_percent"], 3.0)

    def test_returns_unmatched_when_invoice_has_no_bank_reference(self):
        result = search_local_ledger(300.0, "INV-003", str(LEDGER_PATH))

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "Unmatched")
        self.assertIsNone(result["transaction"])


if __name__ == "__main__":
    unittest.main()
