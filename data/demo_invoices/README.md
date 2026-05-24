# Demo Invoice Scenarios

Use these synthetic invoice PDFs for the 3-minute demo video.

| File | Invoice | Expected MYR | Ledger Result |
|---|---:|---:|---|
| `invoice_perfect_match_INV-001.pdf` | USD 100.00 | RM 425.00 | Matched |
| `invoice_close_match_INV-002.pdf` | USD 100.00 | RM 425.00 | Matched with Fee Variance |
| `invoice_no_match_INV-003.pdf` | EUR 200.00 | RM 960.00 | Unmatched |

Notes:

- The close-match case uses `TXN002` in `data/local_ledger.csv`.
- `USD 100.00 x 4.25 = RM 425.00`.
- `TXN002` received `RM 416.50`, which is exactly a 2.00% deduction.
- The PDFs are text-based, so `extract_invoice_data()` can read them with `pypdf`.
