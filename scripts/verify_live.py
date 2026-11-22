import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import llm_service
from llm_service import generate_questions
from pdf_utils import extract_report, prepare_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:7b")
    args = parser.parse_args()
    target = ROOT / "samples" / "outputs"
    target.mkdir(exist_ok=True)
    results = []
    original_request = llm_service.request_completion
    trace_index = 0
    traces = ROOT / ".pytest_cache" / "live_responses"
    traces.mkdir(parents=True, exist_ok=True)
    def traced_request(*args, **kwargs):
        nonlocal trace_index
        raw = original_request(*args, **kwargs)
        trace_index += 1
        (traces / f"last_response_{trace_index}.txt").write_text(raw)
        return raw
    llm_service.request_completion = traced_request
    (target / "verification.json").write_text("[]")
    for filename in ["sample_project_report", "library_report", "irrigation_report", "expense_report", "attendance_report"]:
        (target / f"{filename}.json").unlink(missing_ok=True)
        started = time.monotonic()
        report = extract_report((ROOT / "samples" / f"{filename}.pdf").read_bytes())
        text, sampled = prepare_report(report.text)
        try:
            questions = generate_questions(text, "Ollama", args.model)
            (target / f"{filename}.json").write_text(json.dumps(questions, ensure_ascii=False, indent=2))
            result = {"input": filename, "model": args.model, "pages": report.page_count,
                      "words": report.word_count, "counts": {k: len(v) for k, v in questions.items()},
                      "seconds": round(time.monotonic()-started, 1), "status": "passed schema validation"}
        except Exception as exc:
            result = {"input": filename, "status": "failed", "error": str(exc)}
        results.append(result)
        print(json.dumps(result), flush=True)
        (target / "verification.json").write_text(json.dumps(results, indent=2))
    if any(row["status"] == "failed" for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
