---
title: Xborder Treasury Agent
emoji: 📊
colorFrom: yellow
colorTo: yellow
sdk: gradio
sdk_version: 6.14.0
python_version: "3.13"
app_file: app.py
pinned: false
---

# Cross-Border Treasury Reconciliation Agent

This repository is a Gradio + LangGraph prototype for reconciling foreign invoices against a local MYR bank ledger.

The system is designed for a demo workflow:

1. Upload an invoice file.
2. Let an LLM-driven agent extract the invoice amount and currency.
3. Convert the amount into MYR using fixed demo FX rates.
4. Search a local ledger for an exact match or a near match within a fee tolerance.
5. Review the streamed agent log and export the results table as PDF or PNG.

## What the system does

The application combines a UI, an agent loop, and deterministic tools:

- `app.py` builds the Gradio app and wires UI events.
- `ui_components.py` defines the layout, controls, custom CSS, and export buttons.
- `app_helpers.py` bridges the Gradio UI to the async LangGraph execution, stores session results, paginates tables, and generates exports.
- `agent.py` builds the LangGraph workflow and binds the LLM to the reconciliation tools.
- `tools.py` implements invoice extraction, MYR conversion, and local ledger matching.
- `data/` contains demo invoices and the sample bank ledger.
- `tests/test_tools.py` covers the deterministic tool layer.

## End-to-end flow

The runtime flow is:

1. A user uploads a file from the UI.
2. `process_reconciliation()` in `app_helpers.py` creates a natural-language prompt for the agent.
3. `agent.py` runs a LangGraph loop with:
   - an `agent` node backed by `ChatOpenAI`
   - a `tools` node backed by `ToolNode`
4. The agent calls these tools in sequence:
   - `extract_invoice_data(file_path)`
   - `convert_currency(amount, from_currency, to_currency="MYR")`
   - `search_local_ledger(converted_amount, invoice_id, ledger_path, tolerance_percent)`
5. Tool outputs are streamed back to the UI log in real time.
6. When the ledger search finishes, the app appends a row to the session results table.
7. The user can export the accumulated table as PDF or PNG.

## Reconciliation statuses

The ledger matching logic in `tools.py` returns one of these statuses:

- `Matched`: The converted amount matches the MYR deposit exactly, within RM `0.01`.
- `Matched with Fee Variance`: The closest deposit is within the configured tolerance percentage.
- `Unmatched`: No reference match exists, or the closest deposit exceeds the tolerance.

The matching step first filters the ledger by `invoice_id` inside the transaction `reference`. Only then does it compare amounts. This prevents one invoice from accidentally matching another invoice's deposit.

## Supported files

### Files accepted by the Gradio upload control

- `.csv`
- `.xls`
- `.xlsx`
- `.pdf`

### Files supported by `extract_invoice_data()` directly

- `.csv`
- `.xlsx`
- `.pdf`
- `.txt`
- `.md`

Important limitations:

- PDF support is text extraction only via `pypdf`.
- OCR is not implemented for scanned images.
- Image files such as `.png` and `.jpg` are not supported by the current tool layer.

## Data expectations

### Invoice data

For structured invoice files, the extractor recognizes normalized column names such as:

- Amount: `invoice_amount`, `total_amount`, `grand_total`, `amount_paid`, `amount`, `total`
- Currency: `invoice_currency`, `currency`, `ccy`
- Invoice ID: `invoice_id`, `invoice_number`, `reference`, `ref`
- Date: `invoice_date`, `date`, `payment_date`

Example CSV:

```csv
invoice_id,invoice_date,currency,amount,customer,description
INV-001,2026-05-24,USD,100.00,Acme Export Ltd,International consulting invoice
```

For text and PDF inputs, the extractor looks for labels such as `Grand Total`, `Total`, `Amount`, and currency tokens like `USD`, `EUR`, `SGD`, `MYR`, `RM`, `$`, `EUR`, `S$`, and `GBP`.

### Ledger data

The local ledger CSV must contain these normalized columns:

- `transaction_id`
- `date`
- `reference`
- `amount_myr`

Bundled demo ledger:

```csv
transaction_id,date,reference,amount_myr
TXN001,2026-05-24,INV-001 PAYMENT,425.00
TXN002,2026-05-24,INV-002 PAYMENT,416.50
TXN003,2026-05-24,UNKNOWN PAYMENT,90.00
TXN004,2026-05-23,OFFICE SUPPLIES,150.00
```

## Demo FX rates

This prototype uses fixed synthetic MYR rates from `tools.py` so the demo is reproducible and does not depend on external FX APIs.

| Currency | MYR Rate |
| --- | ---: |
| `MYR` | 1.00 |
| `USD` | 4.25 |
| `SGD` | 3.30 |
| `EUR` | 4.80 |
| `GBP` | 5.70 |

## Setup

### Prerequisites

- Python matching the Space config, ideally `3.13`
- A Morpheus/Shoots API key exposed as `MORPHEUS_API_KEY`

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Configure the environment

Create a `.env` file in the project root:

```env
MORPHEUS_API_KEY=your_api_key_here
```

`agent.py` loads this variable with `python-dotenv`.

## Running the app

Start the Gradio UI locally:

```bash
python app.py
```

What you will see in the UI:

- Left panel:
  - file upload
  - source and target currency selectors
  - exchange-rate display
  - tolerance slider
  - process and clear buttons
- Right panel:
  - paginated results table
  - PDF and image export buttons
  - live agent log

## Tutorial: run the bundled demo

### Scenario 1: perfect match

1. Start the app with `python app.py`.
2. Upload `data/demo_invoices/invoice_perfect_match_INV-001.pdf` or `data/invoice_001.csv`.
3. Leave target currency as `MYR`.
4. Leave tolerance at `3.0`.
5. Click `Process Reconciliation`.

Expected outcome:

- Extracted invoice: `USD 100.00`
- Converted amount: `RM 425.00`
- Matching ledger row: `TXN001`
- Final status: `Matched`

### Scenario 2: bank fee variance

Use `data/demo_invoices/invoice_close_match_INV-002.pdf` or `data/invoice_002.csv`.

Expected outcome:

- Extracted invoice: `USD 100.00`
- Converted amount: `RM 425.00`
- Matching ledger row: `TXN002`
- Actual received amount: `RM 416.50`
- Variance: `2.00%`
- Final status: `Matched with Fee Variance`

### Scenario 3: no match

Use `data/demo_invoices/invoice_no_match_INV-003.pdf` or `data/invoice_003.csv`.

Expected outcome:

- Extracted invoice: `EUR 200.00`
- Converted amount: `RM 960.00`
- No ledger reference match for `INV-003`
- Final status: `Unmatched`

## Running the tool tests

The deterministic reconciliation tools can be tested without launching the UI:

```bash
python -m unittest tests/test_tools.py
```

The current test suite covers:

- structured CSV extraction
- text/PDF extraction
- exact ledger matches
- fee-variance matches
- unmatched ledger searches
- synthetic currency conversion

## Running the agent test harness

`agent.py` includes a simple CLI streaming test:

```bash
python agent.py
```

By default it runs this prompt against `./data/invoice_001.csv`:

```text
I have an invoice located at './data/invoice_001.csv'. Please extract, convert, and search the ./data/local_ledger.csv for a match.
```

This is useful if you want to inspect the raw LangGraph loop outside the Gradio UI.

## Export behavior

After one or more reconciliations, the app can export the cumulative session table:

- `Export PDF` generates a PDF in the temporary directory and exposes a download button.
- `Export Image` generates a PNG in the temporary directory and exposes a download button.

Exports are generated by rendering the DataFrame into an image first, then optionally converting that image to PDF.

## Programmatic usage

You can also use the tool layer directly in Python:

```python
from tools import extract_invoice_data, convert_currency, search_local_ledger

invoice = extract_invoice_data("data/invoice_001.csv")
fx = convert_currency(invoice["amount"], invoice["currency"])
result = search_local_ledger(
    fx["converted_amount"],
    invoice_id=invoice["invoice_id"],
    ledger_path="data/local_ledger.csv",
    tolerance_percent=3.0,
)

print(invoice)
print(fx)
print(result)
```

## Demo assets

The repository includes generated PDF demo invoices under `data/demo_invoices/`.

To regenerate them:

```bash
python scripts/generate_demo_invoices.py
```

That script uses `reportlab` and produces three scenarios:

| File | Scenario | Expected result |
| --- | --- | --- |
| `invoice_perfect_match_INV-001.pdf` | Exact amount match | `Matched` |
| `invoice_close_match_INV-002.pdf` | Small deduction by intermediary bank | `Matched with Fee Variance` |
| `invoice_no_match_INV-003.pdf` | Missing ledger reference | `Unmatched` |

## Important implementation notes

These are current behavior details worth knowing before you modify the system:

- The prototype is MYR-settlement focused. `convert_currency()` only supports conversion into `MYR`.
- The UI lets you choose a target currency, but the tool layer will reject non-MYR targets.
- The source currency dropdown updates the displayed exchange rate, but the actual conversion step uses the currency extracted from the uploaded invoice.
- The displayed exchange rate in the UI is informational only. The conversion tool uses `_DEMO_MYR_RATES` from `tools.py`.
- Results accumulate across multiple runs in one session until `Clear All` is pressed.
- Pagination is fixed at 25 rows per page.
- The UI import path goes through `app_helpers.py`, which imports `agent.py`, so the app needs a valid API key even though the tool tests do not.

## Troubleshooting

### `ModuleNotFoundError` for `pandas`, `pypdf`, or other packages

Install the project requirements first:

```bash
python -m pip install -r requirements.txt
```

### PDF extraction returns no invoice data

The PDF is probably scanned or image-only. This prototype needs text-based PDFs.

### The agent fails before reconciliation starts

Check:

- `MORPHEUS_API_KEY` is present
- the key has usable credits/quota
- the model endpoint configured in `agent.py` is reachable in your environment

### A non-MYR target currency fails

That is expected with the current implementation. The conversion tool is intentionally limited to `MYR`.

## Suggested extension points

If you want to evolve this prototype, the highest-value areas are:

- add OCR for image and scanned PDF invoices
- support live FX providers instead of synthetic rates
- let the UI choose a non-MYR settlement currency end to end
- store reconciliation history in a database instead of Gradio session state
- expand ledger matching beyond invoice-reference containment
- add integration tests for the Gradio-to-LangGraph bridge

## Repository layout

```text
.
|-- app.py
|-- agent.py
|-- app_helpers.py
|-- ui_components.py
|-- tools.py
|-- requirements.txt
|-- data/
|   |-- local_ledger.csv
|   |-- invoice_001.csv
|   |-- invoice_002.csv
|   |-- invoice_003.csv
|   `-- demo_invoices/
|-- scripts/
|   `-- generate_demo_invoices.py
`-- tests/
    `-- test_tools.py
```

## Summary

This codebase is a demo-oriented reconciliation system with:

- a polished Gradio front end
- an LLM agent loop orchestrated with LangGraph
- deterministic extraction, FX conversion, and ledger-matching tools
- bundled demo data for exact-match, fee-variance, and unmatched scenarios

Keep the YAML front matter at the top of this file if you deploy the project as a Hugging Face Space.
