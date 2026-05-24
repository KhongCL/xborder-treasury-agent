import tempfile
import unittest
from pathlib import Path

from tools import convert_currency, extract_invoice_data, search_local_ledger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = PROJECT_ROOT / "data" / "local_ledger.csv"
DEMO_INVOICE_DIR = PROJECT_ROOT / "data" / "demo_invoices"


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

    def test_extracts_perfect_match_demo_pdf(self):
        result = extract_invoice_data(
            str(DEMO_INVOICE_DIR / "invoice_perfect_match_INV-001.pdf")
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["invoice_id"], "INV-001")
        self.assertEqual(result["invoice_currency"], "USD")
        self.assertEqual(result["invoice_amount"], 100.0)

    def test_extracts_close_match_demo_pdf(self):
        result = extract_invoice_data(
            str(DEMO_INVOICE_DIR / "invoice_close_match_INV-002.pdf")
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["invoice_id"], "INV-002")
        self.assertEqual(result["invoice_currency"], "USD")
        self.assertEqual(result["invoice_amount"], 100.0)

    def test_extracts_no_match_demo_pdf(self):
        result = extract_invoice_data(
            str(DEMO_INVOICE_DIR / "invoice_no_match_INV-003.pdf")
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["invoice_id"], "INV-003")
        self.assertEqual(result["invoice_currency"], "EUR")
        self.assertEqual(result["invoice_amount"], 200.0)


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
        self.assertEqual(result["difference_myr"], 8.5)
        self.assertEqual(result["variance_percent"], 2.0)
        self.assertLess(result["variance_percent"], 3.0)

    def test_returns_unmatched_when_invoice_has_no_bank_reference(self):
        result = search_local_ledger(300.0, "INV-003", str(LEDGER_PATH))

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "Unmatched")
        self.assertIsNone(result["transaction"])


class ConvertCurrencyTests(unittest.TestCase):
    def test_converts_usd_invoice_to_expected_myr_amount(self):
        result = convert_currency(100.0, "USD")

        self.assertTrue(result["success"])
        self.assertEqual(result["converted_rm_amount"], 425.0)
        self.assertEqual(result["rate"], 4.25)

    def test_converts_sgd_invoice_for_second_demo_scenario(self):
        result = convert_currency(50.0, "SGD")

        self.assertTrue(result["success"])
        self.assertEqual(result["converted_rm_amount"], 165.0)

    def test_normalizes_rm_as_myr_without_changing_amount(self):
        result = convert_currency(421.50, "RM")

        self.assertTrue(result["success"])
        self.assertEqual(result["from_currency"], "MYR")
        self.assertEqual(result["converted_rm_amount"], 421.50)

    def test_rejects_unconfigured_currency(self):
        result = convert_currency(100.0, "JPY")

        self.assertFalse(result["success"])
        self.assertIn("Unsupported source currency", result["error"])


if __name__ == "__main__":
    unittest.main()
