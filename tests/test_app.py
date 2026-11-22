import json
from io import BytesIO

import pytest
import requests
from pypdf import PdfWriter
from reportlab.pdfgen import canvas

from llm_service import GenerationError, generate_questions, parse_questions, request_completion, to_text
from pdf_utils import extract_report, prepare_report
from prompts import LEVELS


def make_questions():
    return {level: [{"question": f"What is {level} topic {i}?", "answer": "The report describes this topic. It explains the method."}
                    for i in range(5)] for level in LEVELS}


def make_pdf(pages):
    buf = BytesIO()
    document = canvas.Canvas(buf)
    for page in pages:
        document.drawString(40, 750, page)
        document.showPage()
    document.save()
    return buf.getvalue()


def test_extract_all_pages():
    report = extract_report(make_pdf([
        "A library management project tracks books, loans, readers and returns.",
        "The second page describes Python and SQLite for storing loan records."]))
    assert report.page_count == 2
    assert report.word_count == 21
    assert "[Page 2]" in report.text and "SQLite" in report.text


@pytest.mark.parametrize("data", [b"", b"not a PDF", make_pdf([""])])
def test_unreadable_reports(data):
    with pytest.raises(ValueError):
        extract_report(data)


def test_encrypted_report():
    writer = PdfWriter()
    writer.add_blank_page(600, 800)
    writer.encrypt("secret")
    buf = BytesIO()
    writer.write(buf)
    with pytest.raises(ValueError, match="password"):
        extract_report(buf.getvalue())


def test_partial_scanned_pdf():
    report = extract_report(make_pdf(["", "This report describes a library system that tracks loans and books."]))
    assert report.empty_pages == 1 and report.page_count == 2


def test_sampling_preserves_beginning_and_end():
    source = "INTRO" + "middle " * 10000 + "CONCLUSION"
    text, sampled = prepare_report(source)
    assert sampled and len(text) <= 24000
    assert text.startswith("INTRO") and text.endswith("CONCLUSION")
    assert "omitted report text" in text
    assert prepare_report("short") == ("short", False)


def test_valid_questions_and_export():
    data = make_questions()
    parsed = parse_questions("```json\n" + json.dumps(data) + "\n```")
    assert parsed == data
    assert sum(map(len, parsed.values())) == 15
    assert "HARD" in to_text(parsed)
    assert "Answer:" in to_text(parsed)


@pytest.mark.parametrize("raw", ["nonsense", "null", "[]", '{"easy": []}'])
def test_invalid_json_shapes(raw):
    with pytest.raises(ValueError):
        parse_questions(raw)


@pytest.mark.parametrize("change", ["count", "duplicate", "empty", "wrong_type", "extra_field", "one_sentence"])
def test_invalid_questions(change):
    data = make_questions()
    if change == "count":
        data["easy"].pop()
    elif change == "duplicate":
        data["hard"][0]["question"] = data["easy"][0]["question"].upper().replace("?", " !")
    elif change == "empty":
        data["medium"][0]["answer"] = "   "
    elif change == "wrong_type":
        data["easy"][0]["answer"] = None
    elif change == "one_sentence":
        data["easy"][0]["answer"] = "Only one sentence."
    else:
        data["easy"][0]["extra"] = "unexpected"
    with pytest.raises(ValueError):
        parse_questions(json.dumps(data))


def test_missing_api_key_no_network(monkeypatch):
    def should_not_call(*args, **kwargs):
        pytest.fail("No request should be sent without a key")
    monkeypatch.setattr(requests, "post", should_not_call)
    with pytest.raises(GenerationError, match="API key"):
        generate_questions("Report", "Groq", "test")


@pytest.mark.parametrize("error,match", [(requests.ConnectionError(), "Cannot connect"), (requests.Timeout(), "timed out")])
def test_connection_failures(monkeypatch, error, match):
    def fail(*args, **kwargs):
        raise error
    monkeypatch.setattr(requests, "post", fail)
    with pytest.raises(GenerationError, match=match):
        generate_questions("Report", "Ollama", "test")


def test_bounded_validation_retry(monkeypatch):
    responses = iter(["{}", json.dumps(make_questions())])
    seen = []
    def completion(messages, *args):
        seen.append(list(messages))
        return next(responses)
    monkeypatch.setattr("llm_service.request_completion", completion)
    assert generate_questions("The report describes this topic. It explains the method.", "Ollama", "test") == make_questions()
    assert len(seen) == 2 and len(seen[1]) == 4
    assert "Correct this validation error" in seen[1][-1]["content"]


def test_two_invalid_responses_fail(monkeypatch):
    monkeypatch.setattr("llm_service.request_completion", lambda *args: "{}")
    with pytest.raises(GenerationError, match="two attempts"):
        generate_questions("Report", "Ollama", "test")


@pytest.mark.parametrize("body", [[], None, {}, {"message": {"content": None}}, {"message": {"content": "{}"}, "done_reason": "length"}])
def test_malformed_provider_response(monkeypatch, body):
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return body
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: Response())
    with pytest.raises(GenerationError):
        request_completion([], "Ollama", "test", "", "http://localhost:11434")


@pytest.mark.parametrize("code,match", [(401, "API key"), (404, "not found"), (429, "rate limited"), (500, "provider returned an error")])
def test_http_errors(monkeypatch, code, match):
    response = requests.Response()
    response.status_code = code
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)
    with pytest.raises(GenerationError, match=match):
        request_completion([], "Groq", "test", "key", "")


def test_structured_answer_sentences_normalized():
    data = make_questions()
    data["easy"][0]["answer"] = ["The report describes this topic.", "It explains the method."]
    assert parse_questions(json.dumps(data)) == make_questions()


def test_trivial_question_rewording_is_duplicate():
    data = make_questions()
    data["easy"][0]["question"] = "Who are the intended users of this application?"
    data["hard"][0]["question"] = "What are the intended users of this application?"
    with pytest.raises(ValueError, match="duplicate"):
        parse_questions(json.dumps(data))


def test_repeated_answer_sentence_rejected():
    data = make_questions()
    data["easy"][0]["answer"] = ["The report describes this topic.", "THE REPORT DESCRIBES THIS TOPIC."]
    with pytest.raises(ValueError, match="two nonempty"):
        parse_questions(json.dumps(data))


def test_missing_answer_notice_is_not_repeated():
    data = make_questions()
    data["easy"][0]["answer"] = ["Not specified in the report.", "Not specified in the report."]
    parsed = parse_questions(json.dumps(data))
    assert parsed["easy"][0]["answer"] == "Not specified in the report. The report provides no further details on this point."
