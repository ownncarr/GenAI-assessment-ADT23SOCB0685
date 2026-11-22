# Verification record

Development machine: macOS Apple Silicon, 16 GB memory. Python 3.14, Ollama `qwen2.5:7b` (final default) and `qwen2.5:3b` (initial checks). Test PDFs are synthetic and contain no private data.

## Automated checks

Run `python -m pytest -q` after installing `requirements-dev.txt`.

Executed on 22 November 2026: **36 passed**. The installed dependency environment also passed `python -m pip check`.

The suite covers extraction from multiple pages, exact word counts, empty/corrupt/blank/encrypted PDFs, partially unreadable pages, distributed long-report sampling, strict question counts and categories, duplicate detection, missing fields, empty answers, sentence validation, TXT export, missing credentials, timeouts, connection failures, HTTP errors, malformed API responses and bounded retry behavior.

## Five real report inputs

Run `python scripts/verify_live.py` with Ollama running and `qwen2.5:7b` installed. Use `--model qwen2.5:3b` to test the smaller model. Executed on 22 November 2026: **5/5 live inputs completed**, each with exactly 15 questions split 5/5/5 and valid answer fields. Actual JSON outputs and timings are recorded in `samples/outputs/verification.json`; each report's full output is stored alongside it.

| Input | Subject | Expected behavior |
|---|---|---|
| `sample_project_report.pdf` | Smart Campus Helpdesk | Questions about Flask routes, SQLite tickets and stated limitations |
| `library_report.pdf` | Library Loan Tracker | Questions about Tkinter, SQLite, loans and manual tests |
| `irrigation_report.pdf` | Soil Moisture Irrigation Monitor | Questions about Arduino, sensor calibration, hysteresis and bench tests |
| `expense_report.pdf` | Personal Expense Dashboard | Questions about CSV validation, pandas, Streamlit and non-persistent data |
| `attendance_report.pdf` | QR Classroom Attendance | Questions about Flask, SQLite constraints, duplicate scans and QR sharing |

Manual answer review found that local-model outputs can still add unstated justifications or infer user roles. Structural checks do not detect these errors. Review every answer against the PDF; the application and README make this limitation explicit.

These inputs test the complete local PDF → prompt → model → validated 15 questions path. Schema validation does not establish factual accuracy. Inspect the saved answers against their corresponding PDFs before using them as viva study material.

## Browser verification

Start Streamlit, install the Playwright Chromium browser, then run `python scripts/verify_ui.py`. The script uses real local generation, not a mocked model.

Checks include the initial screen, disabled generation without a report, report metadata, five question expanders in each difficulty tab, a live generated result, valid JSON and TXT downloads, clearing results when the PDF changes, blank/corrupt PDF errors, missing Groq key handling, unavailable local server handling and browser JavaScript errors.

The browser run with `qwen2.5:7b` passed all listed checks. Downloaded JSON was also revalidated for category counts, sentence counts and required fields. Factual accuracy requires reviewing answers against the report.

The last completed browser run is recorded in `screenshots/verification.json`.

## Screenshot evidence

- `screenshots/01_upload.png`: upload screen and local model settings.
- `screenshots/02_easy.png`: Easy questions with one answer expanded.
- `screenshots/03_medium.png`: Medium questions with one answer expanded.
- `screenshots/04_hard.png`: Hard questions with one answer expanded.
- `screenshots/05_invalid_pdf.png`: unreadable/blank document error.

These are genuine browser captures. Screenshots and sample outputs can vary when the model is run again.

## Verification limits

Groq transport and errors are covered by simulated provider responses; no live Groq generation is claimed without a real API key. OCR, load testing and exhaustive grounding verification are outside this mini-project's scope. Rejected intermediate model responses may appear in diagnostic files during development; they are never shown as completed UI results.
