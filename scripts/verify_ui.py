import argparse
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from llm_service import parse_questions
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".playwright"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:7b")
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1080}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501")
        expect(page.get_by_role("heading", name="AI Viva Question Generator", exact=True)).to_be_visible()
        expect(page.get_by_role("button", name="Generate Viva Questions", exact=True)).to_be_disabled()
        expect(page.get_by_text("Ollama connected", exact=False)).to_be_visible()
        page.get_by_role("combobox", name="Local model", exact=True).click()
        page.get_by_role("option", name=args.model, exact=True).click()
        page.screenshot(path=str(ROOT / "screenshots" / "01_upload.png"), full_page=True)
        print("Initial screen and disabled generation button passed", flush=True)
        page.locator('input[type="file"]').set_input_files(str(ROOT / "samples" / "library_report.pdf"))
        expect(page.get_by_text("Extracted words", exact=True)).to_be_visible()
        page.get_by_role("button", name="Generate Viva Questions", exact=True).click()
        ready = page.get_by_text("15 questions ready", exact=False)
        failed = page.get_by_text("Could not validate", exact=False).or_(page.get_by_text("The model timed out", exact=False))
        expect(ready.or_(failed)).to_be_visible(timeout=600000)
        expect(ready).to_be_visible()
        page.get_by_role("tab", name="Easy · 5 questions").click()
        for index, level in enumerate(("Easy", "Medium", "Hard"), 2):
            page.get_by_role("tab", name=f"{level} · 5 questions").click()
            panel = page.get_by_role("tabpanel")
            expect(panel.locator('details')).to_have_count(5)
            panel.locator('summary').first.click()
            page.get_by_text('Your viva preparation set', exact=True).evaluate('(el) => el.scrollIntoView({block: "start"})')
            page.wait_for_timeout(500)
            page.screenshot(path=str(ROOT / "screenshots" / f"0{index}_{level.lower()}.png"), full_page=True)
        with page.expect_download() as download:
            page.get_by_role("button", name="Download JSON", exact=True).click()
        content = json.loads(Path(download.value.path()).read_text())
        assert set(content) == {"easy", "medium", "hard"}
        assert all(len(items) == 5 for items in content.values())
        assert parse_questions(json.dumps(content)) == content
        with page.expect_download() as download:
            page.get_by_role("button", name="Download TXT", exact=True).click()
        assert "HARD" in Path(download.value.path()).read_text()
        print("Live generation, all difficulty tabs and TXT/JSON downloads passed", flush=True)
        page.locator('input[type="file"]').set_input_files(str(ROOT / "samples" / "expense_report.pdf"))
        expect(page.get_by_text("Document: expense_report.pdf", exact=True)).to_be_visible()
        expect(page.get_by_text("Your viva preparation set", exact=True)).to_have_count(0)
        page.locator('input[type="file"]').set_input_files(str(ROOT / "samples" / "blank_report.pdf"))
        expect(page.get_by_text("Too little readable text was found.", exact=False)).to_be_visible()
        page.screenshot(path=str(ROOT / "screenshots" / "05_invalid_pdf.png"), full_page=True)
        page.locator('input[type="file"]').set_input_files(str(ROOT / "samples" / "invalid_report.pdf"))
        expect(page.get_by_text("Could not read this PDF.", exact=False)).to_be_visible()
        print("Report change clears results; blank/corrupt PDF error flows passed", flush=True)
        page.locator('input[type="file"]').set_input_files(str(ROOT / "samples" / "library_report.pdf"))
        page.get_by_text("Groq", exact=True).click()
        expect(page.get_by_label("Groq API key", exact=True)).to_be_visible()
        page.get_by_role("button", name="Generate Viva Questions", exact=True).click()
        expect(page.get_by_text("Enter your Groq API key in the sidebar.", exact=True)).to_be_visible()
        page.get_by_text("Ollama", exact=True).click()
        page.get_by_label("Ollama server", exact=True).fill("http://127.0.0.1:1")
        page.get_by_label("Ollama server", exact=True).press("Enter")
        page.get_by_role("button", name="Generate Viva Questions", exact=True).click()
        expect(page.get_by_text("Cannot connect to the model provider.", exact=False)).to_be_visible()
        print("Missing Groq key and actual unavailable Ollama error flows passed", flush=True)
        assert not errors, errors
        browser.close()
        (ROOT / "screenshots" / "verification.json").write_text(json.dumps({
            "browser": "Chromium via Playwright", "model": args.model, "status": "passed",
            "checks": ["initial screen", "disabled button without PDF", "live Ollama generation", "five expanders per tab",
                       "TXT download", "JSON download", "stale results cleared on upload change", "blank PDF", "corrupt PDF", "missing Groq key", "unavailable Ollama", "no browser JS errors"]}, indent=2))


if __name__ == "__main__":
    main()
