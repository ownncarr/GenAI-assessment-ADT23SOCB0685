import json
import re
import unicodedata

import requests

from prompts import LEVELS, QUESTION_SCHEMA, messages_for


class GenerationError(ValueError):
    pass


def parse_questions(raw: str) -> dict:
    if not isinstance(raw, str):
        raise ValueError("The model response must be text containing JSON.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("The model did not return valid JSON.") from exc
    if not isinstance(data, dict) or set(data) != set(LEVELS):
        raise ValueError("Expected exactly the easy, medium and hard arrays.")
    seen = set()
    result = {}
    for level in LEVELS:
        items = data[level]
        if not isinstance(items, list) or len(items) != 5:
            raise ValueError(f"Expected exactly five {level} questions.")
        result[level] = []
        for item in items:
            if not isinstance(item, dict) or set(item) != {"question", "answer"}:
                raise ValueError("Every item must contain question and answer fields only.")
            if item["answer"] == ["Not specified in the report.", "Not specified in the report."]:
                item = {**item, "answer": ["Not specified in the report.", "The report provides no further details on this point."]}
            if isinstance(item["answer"], list):
                sentences = item["answer"]
                if len(sentences) != 2 or len({" ".join(str(s).split()).casefold() for s in sentences}) != 2 or any(not isinstance(s, str) or not s.strip() for s in sentences):
                    raise ValueError(f"Answer arrays must contain exactly two nonempty sentence strings for: {item['question']} Use different report sentences, or the missing-information notice.")
                item = {**item, "answer": " ".join(s.strip() for s in sentences)}
            if any(not isinstance(item[key], str) or not item[key].strip() for key in ("question", "answer")):
                raise ValueError("Questions and answers must be nonempty strings.")
            sentence_count = len(re.findall(r"[.!?]+[\"”']?(?=\s|$)", item["answer"].strip()))
            if not 2 <= sentence_count <= 4:
                raise ValueError("Every answer must contain 2-4 complete sentences with terminal punctuation.")
            question_body = re.sub(r"^(?:what|who|which)\s+(?:is|are)\s+", "", item["question"].strip(), flags=re.I)
            normalized = "".join(c for c in unicodedata.normalize("NFKC", question_body).casefold() if c.isalnum())
            if not normalized or normalized in seen:
                raise ValueError(f"The model returned a duplicate or invalid question: {item['question']} Choose a different report topic.")
            seen.add(normalized)
            result[level].append({key: item[key].strip() for key in ("question", "answer")})
    return result


def available_models(base_url: str) -> list[str]:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        response.raise_for_status()
        return [m["name"] for m in response.json()["models"]
                if "completion" in m.get("capabilities", ["completion"])
                and "embed" not in m["name"].lower()]
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return []


def request_completion(messages: list, provider: str, model: str, api_key: str, base_url: str) -> str:
    if provider == "Ollama":
        url = f"{base_url.rstrip('/')}/api/chat"
        headers = {}
        payload = {"model": model, "stream": False, "format": QUESTION_SCHEMA,
                   "options": {"temperature": 0.2, "num_ctx": 16384, "num_predict": 4096}, "messages": messages}
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {"model": model, "temperature": 0.2, "max_tokens": 4096,
                   "response_format": {"type": "json_object"}, "messages": messages}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=(10, 300))
        response.raise_for_status()
    except requests.Timeout as exc:
        raise GenerationError("The model timed out. Try a smaller model or a shorter report, then generate again.") from exc
    except requests.ConnectionError as exc:
        raise GenerationError("Cannot connect to the model provider. For Ollama, start Ollama and check its server address. For Groq, check your internet connection.") from exc
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 0
        explanation = {401: "Groq rejected the API key. Check your key.",
                       403: "Access was denied by the model provider.",
                       404: "Model or endpoint not found. Check the model name; for Ollama, download it with ollama pull.",
                       413: "The report exceeds the provider request limit. Upload a shorter report or select another model.",
                       429: "The provider is rate limited. Wait a moment and try again.",
                       400: "The provider rejected the request. Check model support and report length."}.get(code, "The model provider returned an error. Check its status and try again.")
        raise GenerationError(explanation) from exc
    except requests.RequestException as exc:
        raise GenerationError("The request failed. Check the provider connection and try again.") from exc
    try:
        data = response.json()
        if provider == "Ollama":
            if data.get("done_reason") == "length":
                raise GenerationError("The model stopped before completing its answer. Try a shorter report or another model.")
            content = data["message"]["content"]
        else:
            if data["choices"][0].get("finish_reason") == "length":
                raise GenerationError("The model output was incomplete. Try a shorter report or another model.")
            content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty content")
        return content
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        if isinstance(exc, GenerationError):
            raise
        raise GenerationError("The provider returned an unreadable response. Try again or select another model.") from exc


def generate_questions(report: str, provider: str, model: str, api_key: str = "", base_url: str = "http://localhost:11434") -> dict:
    if provider not in ("Ollama", "Groq"):
        raise GenerationError("Select Ollama or Groq.")
    if not model.strip():
        raise GenerationError("Enter a model name.")
    if provider == "Groq" and not api_key.strip():
        raise GenerationError("Enter your Groq API key in the sidebar.")
    if not report.strip():
        raise GenerationError("Upload a readable report before generating questions.")
    messages = messages_for(report)
    for attempt in range(2):
        raw = request_completion(messages, provider, model.strip(), api_key.strip(), base_url)
        try:
            return parse_questions(raw)
        except ValueError as exc:
            if attempt:
                raise GenerationError(f"Could not validate the questions after two attempts: {exc} Try another model or generate again.") from exc
            messages += [{"role": "assistant", "content": raw},
                         {"role": "user", "content": f"Correct this validation error: {exc} Return the complete corrected JSON, exactly five unique questions in each array."}]
    raise AssertionError("unreachable")


def to_text(questions: dict) -> str:
    lines = ["AI Viva Question Generator", ""]
    for level in LEVELS:
        lines += [level.upper(), "=" * len(level), ""]
        for number, item in enumerate(questions[level], 1):
            lines += [f"Q{number}. {item['question']}", f"Answer: {item['answer']}", ""]
    return "\n".join(lines)
