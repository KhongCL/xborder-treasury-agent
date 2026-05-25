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

**Built for the AI Marathon 2026 - Global Treasury Agent Challenge**

Live Demo: [https://huggingface.co/spaces/KhongCL/xborder-treasury-agent](https://huggingface.co/spaces/KhongCL/xborder-treasury-agent)

Small and Medium Enterprises (SMEs) lose hundreds of hours and thousands of dollars annually manually reconciling cross-border payments. When an invoice is billed for $100 USD, the local bank often receives RM 416.50 instead of the exact RM 425.00 exchange rate due to hidden intermediary bank fees. Traditional matching systems fail here.

This autonomous AI agent solves this by:
1. Extracting data directly from foreign payment proofs (PDFs/Images).
2. Converting currencies using historical spot rates.
3. Intelligently scanning local bank ledgers to detect **"Fee Variances"**—autonomously approving close matches that fall within a user-defined bank fee tolerance threshold (e.g., 3%).

<div align="center">
  <img width="100%" alt="Xborder Dashboard" src="https://github.com/user-attachments/assets/a2b30612-ac7d-4deb-b530-29a971a9795b" />
</div>
<br>


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

## Code walkthrough

This section explains how the code is organized and what each major function is responsible for.

### `app.py`

`app.py` is the composition root for the application.

It does four things:

1. Imports the reusable UI builders from `ui_components.py`.
2. Imports the operational helpers from `app_helpers.py`.
3. Creates the Gradio `Blocks` app and persistent `State` objects.
4. Wires buttons, pagination, export actions, and startup log initialization.

Key ideas in this file:

- `results_store = gr.State(pd.DataFrame())` keeps the cumulative reconciliation results for the current session.
- `current_page = gr.State(1)` tracks pagination state for the results table.
- `process_btn.click(...)` connects the UI to `process_reconciliation()`, which is the async bridge into the agent.
- `prev_page_btn.click(...)` and `next_page_btn.click(...)` call `change_page()` to show slices of the stored DataFrame.
- `pdf_btn.click(...)` and `img_btn.click(...)` call the export helpers.
- `demo.load(...)` clears old logs and writes the startup message when the app launches.
- `safe_clear(...)` intercepts the clear button to ensure the "Unlock 'Clear All'" safety checkbox is ticked, preventing accidental data loss during live sessions.

In practice, `app.py` does not implement business logic. It only coordinates UI events and shared state.

### `ui_components.py`

`ui_components.py` is purely presentation code.

It contains:

- `CSS`: the custom stylesheet for layout, cards, table appearance, terminal-like logs, and export buttons
- `THEME_TOGGLE_JS`: a small script that switches the Gradio theme via the `__theme` query parameter
- `build_header()`: renders the top header bar
- `build_configuration_panel(...)`: builds the upload form and reconciliation controls
- `build_results_panel()`: builds the results table, paging buttons, export buttons, and log viewer

Why this split matters:

- `app.py` stays focused on behavior and event wiring.
- `ui_components.py` stays focused on layout and styling.
- changing the UI structure is isolated from changing the reconciliation logic

### `app_helpers.py`

`app_helpers.py` is the operational glue layer between Gradio and LangGraph.

The most important function is `process_reconciliation(...)`.

Its job is to:

1. validate the uploaded file
2. derive the file path from the Gradio upload object
3. build the agent prompt
4. create the initial LangGraph state
5. stream agent events from `app.astream(...)`
6. translate tool outputs into UI logs and table rows
7. keep the cumulative `results_store` updated

Important helper functions in this file:

- `log_message(...)`: appends a timestamped entry to the in-memory `LOGS` list and returns the full log text for the UI
- `get_exchange_rate(...)`: computes a display-only rate from `_DEMO_MYR_RATES`
- `generate_pdf(...)` and `generate_image(...)`: create downloadable exports from the current results DataFrame
- `paginate_dataframe(...)`: returns a single page slice of the stored results
- `build_page_label(...)`: formats the page indicator text
- `clear_all(...)`: resets the uploaded file, logs, results table, page state, and export buttons

One implementation detail to understand:

`process_reconciliation(...)` reads tool outputs from the streamed LangGraph messages, parses the JSON content, and constructs the final DataFrame row only after the ledger search returns a `status`.

### `agent.py`

`agent.py` defines the agent runtime.

Core parts:

- `load_dotenv()` loads `MORPHEUS_API_KEY`
- `AgentState` describes the shared graph state
- `llm = ChatOpenAI(...)` configures the model client against the Morpheus endpoint
- `tools = [extract_invoice_data, convert_currency, search_local_ledger]` defines the callable tool set
- `run_agent(...)` prepends the system prompt and asks the LLM what to do next
- `should_continue(...)` decides whether the graph should execute tools again or stop
- `workflow = StateGraph(AgentState)` builds the graph
- `app = workflow.compile()` turns the graph into the executable object used by the UI

The graph shape is simple:

- entry point: `agent`
- conditional edge: `agent -> tools` if the model issued a tool call
- loop edge: `tools -> agent`
- terminal condition: `agent -> END` when the model returns a final answer without another tool call

This is why the project behaves like an autonomous tool-using agent instead of a single prompt-response call.

### `tools.py`

`tools.py` contains the deterministic business logic. This is the most important file for correctness.

#### `extract_invoice_data(file_path)`

This function:

- validates the file path and file type
- reads tables with `pandas`
- reads text-based PDFs with `pypdf`
- extracts amount, currency, invoice ID, and date
- returns structured dictionaries instead of raising agent-breaking exceptions

Implementation details:

- structured files go through `_extract_from_table(...)`
- unstructured text goes through `_extract_from_text(...)`
- helper functions such as `_normalize_column(...)`, `_parse_number(...)`, `_normalize_currency(...)`, `_extract_invoice_id(...)`, and `_extract_date(...)` handle data cleanup

#### `convert_currency(amount, from_currency, to_currency="MYR")`

This function is intentionally simple:

- validates the numeric amount
- normalizes the currency token
- looks up the source rate in `_DEMO_MYR_RATES`
- returns a structured result with the converted MYR amount and a human-readable calculation string

It is deterministic by design so the demo is reproducible.

#### `search_local_ledger(converted_amount, invoice_id, ledger_path, tolerance_percent)`

This function:

- validates numeric inputs
- reads the ledger CSV
- checks that required columns exist
- filters rows by `invoice_id` inside the `reference` column
- computes absolute MYR difference and variance percentage
- picks the closest candidate
- returns `Matched`, `Matched with Fee Variance`, or `Unmatched`

The reference filter is a deliberate safety mechanism. Without it, the nearest amount could belong to the wrong invoice.

### `tests/test_tools.py`

The tests focus on the deterministic layer rather than the full UI or LLM path.

They verify:

- CSV extraction works
- text extraction works
- demo PDFs are parseable
- exact ledger matches are recognized
- small fee deductions are classified correctly
- unsupported currencies fail cleanly

This is the correct testing focus for the current architecture because the tool layer contains the business rules, while the agent layer mainly orchestrates those tools.

### `scripts/generate_demo_invoices.py`

This script exists to support repeatable demos.

It uses `reportlab` to generate three synthetic invoices with:

- different vendors
- different invoice IDs
- different currencies and amounts
- different expected reconciliation outcomes

Because the PDFs are generated as text-based documents, `extract_invoice_data()` can read them reliably with `pypdf`.

## State and data flow

A useful way to read the code is to track the data objects that move through the system:

- UI upload input:
  - starts in `app.py`
  - is passed into `process_reconciliation(...)`
- agent message history:
  - starts as a single `HumanMessage`
  - is extended by LangGraph as tool calls and model responses are produced
- `initial_state` / `AgentState` fields:
  - `invoice_amount`
  - `invoice_currency`
  - `converted_rm_amount`
  - `reconciliation_status`
- session results table:
  - lives in `results_store`
  - is appended after each completed reconciliation
- logs:
  - live in the module-level `LOGS` list
  - are rewritten into the log textbox after every streamed update

If you want to debug the app, this is the right order to inspect:

1. Was the invoice parsed correctly by `extract_invoice_data()`?
2. Was the amount converted correctly by `convert_currency()`?
3. Did `search_local_ledger()` receive the correct `invoice_id` and amount?
4. Did `process_reconciliation()` parse the tool JSON and append the output row?
5. Did `app.py` update the right Gradio outputs?

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
<div align="center">
  <img width="400" alt="Scenario 1 PDF" src="https://github.com/user-attachments/assets/c70412f9-3b5e-42ea-9049-424c87acb061" />
</div>

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
<div align="center">
  <img width="400" alt="Scenario 2 PDF" src="https://github.com/user-attachments/assets/60bc4442-3946-4ac3-adb5-24778e18dba2" />
</div>


Use `data/demo_invoices/invoice_close_match_INV-002.pdf` or `data/invoice_002.csv`.

Expected outcome:

- Extracted invoice: `USD 100.00`
- Converted amount: `RM 425.00`
- Matching ledger row: `TXN002`
- Actual received amount: `RM 416.50`
- Variance: `2.00%`
- Final status: `Matched with Fee Variance`

### Scenario 3: no match
<div align="center">
  <img width="400" alt="Scenario 3 PDF" src="https://github.com/user-attachments/assets/1ff43df4-ad54-4f76-9b87-3810a15169b0" />
</div>


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
