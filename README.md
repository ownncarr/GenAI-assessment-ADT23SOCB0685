# AI Viva Question Generator · PS28

Students often do not know which questions an examiner will ask about their project. This lightweight Streamlit application reads a project report PDF and generates 15 viva questions with short answers: five Easy, five Medium and five Hard. Questions are based on the uploaded report.

## Features

- Drag-and-drop PDF upload with filename, page count and extracted word count.
- Local generation through Ollama, or cloud generation through Groq.
- Strict JSON validation, exactly five questions per category and duplicate checks.
- Report-grounded prompting with explicit instructions to identify missing information.
- Easy/Medium/Hard tabs with expandable answers.
- TXT and JSON downloads.
- Clear messages for unreadable, empty, scanned and encrypted PDFs, missing keys, unavailable models, connection failures and malformed output.
- Report and settings changes clear previous results.

## Stack

Python 3.10+, Streamlit, pypdf, requests and python-dotenv. No database, login, training or vector store is required.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate the environment with `.venv\Scripts\activate`.

Optional environment configuration:

```bash
cp .env.example .env
```

The app works without a `.env` file. Never commit real API keys.

### Ollama: run locally

Install and open Ollama, then download the default model:

```bash
ollama pull qwen2.5:7b
```

If Ollama is not running, start the desktop app or run `ollama serve`. The default endpoint is `http://localhost:11434`. The model selector lists available text models; choose **Other model…** to enter another installed model such as `llama3.2:3b`. Embedding models cannot generate questions.

`qwen2.5:7b` is the default local model. The smaller `qwen2.5:3b` is also supported and was used for initial pipeline tests. Select it in the sidebar if you prefer the smaller download and memory footprint. Generation speed depends on hardware, context length and other running applications.

### Groq: API alternative

Select Groq in the sidebar and enter a key, or configure:

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Groq model availability depends on your provider account. You can edit the model name in the sidebar. Groq mode sends the extracted report text to Groq; local mode sends it to the configured Ollama server. The app does not write uploaded reports or keys to disk.

## Run

```bash
streamlit run app.py
```

Open the URL printed in the terminal, normally `http://localhost:8501`.

1. Select Ollama or Groq and the desired model.
2. Upload `samples/sample_project_report.pdf` or your own report.
3. Review document information and extracted text.
4. Click **Generate Viva Questions**.
5. Open answers in each difficulty tab and download TXT or JSON.

## Input and output

The supplied sample describes a Smart Campus Helpdesk using Python, Flask, SQLite, HTML and Bootstrap. Four additional synthetic project reports cover a library tracker, irrigation monitor, expense dashboard and QR attendance system. They are deliberately small examples, not research datasets.

JSON downloads use this structure, with exactly five objects in each array:

```json
{
  "easy": [{"question": "...", "answer": "..."}],
  "medium": [{"question": "...", "answer": "..."}],
  "hard": [{"question": "...", "answer": "..."}]
}
```

The abbreviated example above shows the schema only. Authentic model outputs are saved in `samples/outputs/`. They are examples for review, not fixed application responses. The app always generates from the uploaded report.

## Architecture and viva explanation

```text
PDF upload → pypdf extraction → report excerpt selection → examiner prompt
→ Ollama/Groq → JSON validation → difficulty tabs → TXT/JSON downloads
```

| File | Responsibility |
|---|---|
| `app.py` | Streamlit UI, document state, provider settings and downloads |
| `pdf_utils.py` | PDF validation, metadata and report excerpt selection |
| `prompts.py` | Examiner instructions and structured response schema |
| `llm_service.py` | HTTP requests, error handling, validation and text export |
| `.env.example` | Optional provider configuration template |
| `tests/test_app.py` | Automated PDF, validation and provider failure checks |
| `scripts/` | Sample creation, live verification and browser verification |
| `screenshots/` | Genuine screenshots captured from the running application |

The model returns two short sentences per answer, which the app joins into a normal paragraph. The prompt requires report-grounded facts, permits faithful paraphrases and asks the model to mark missing information explicitly. Repeated missing-information notices are normalized into a readable two-sentence message. TXT and JSON exports contain standard question/answer strings.

If the model returns malformed JSON, wrong counts, incomplete answers or duplicate questions, the app asks it to correct the result once. Network failures are reported directly. Invalid results are never displayed as a completed preparation set.

## Explaining the project in a viva

- **Why Streamlit?** It provides uploads, settings, tabs and downloads directly in Python, keeping the project small.
- **Why JSON?** A fixed structure makes category counts, required fields and downloads straightforward to validate.
- **How is hallucination reduced?** The prompt requires facts from the report, forbids invented details and instructs the model to identify missing information. Structured output and validation check the format; human review checks meaning.
- **Is this model training or RAG?** No training, embeddings or vector database are used. Relevant report text is sent directly to the model.
- **What is the trade-off?** A local model keeps report processing on your machine, but its answers can still contain errors. Check generated explanations against the report.
- **Why no OCR?** The assignment focuses on a lightweight text-PDF pipeline. Scanned reports receive a clear error rather than unreliable empty-input generation.

## Limitations

- Scanned pages need OCR before uploading. Images, charts and tables without readable text cannot be understood by this text-only pipeline.
- Uploads are limited to 20 MB and 200 pages.
- Reports over 24,000 extracted characters are sampled throughout their length. Omitted content can contain relevant information; shorter reports receive full coverage.
- A syntactically valid answer can still be inaccurate. Automated checks validate structure, not factual accuracy or every paraphrased duplicate. Verify answers against the report.
- Very short reports may not support 15 substantively different questions. Missing details should be identified explicitly rather than invented.
- Local models can take several minutes. Each provider request has a five-minute read timeout; one validation retry may be needed.
- Groq requires an internet connection and valid credentials. No live Groq verification is claimed without credentials.

## Testing and screenshots

Start Ollama with `qwen2.5:7b` installed for the live checks. Run Streamlit in a separate terminal before the browser checks.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
python scripts/create_samples.py
python scripts/verify_live.py
PLAYWRIGHT_BROWSERS_PATH=.playwright python -m playwright install chromium
PLAYWRIGHT_BROWSERS_PATH=.playwright python scripts/verify_ui.py
```

Verified on 22 November 2026: 36 automated checks passed, five sample PDFs each produced 15 questions split 5/5/5, and browser checks passed for uploads, result tabs, downloads, report changes and error handling. These checks validate application behavior and output structure; answers still require factual review against the report.

Live generation records are in `samples/outputs/verification.json`. Browser verification and five genuine screenshots are in `screenshots/`. Screenshots can be used in the mini-project report.
