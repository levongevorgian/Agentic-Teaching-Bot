# Agentic Telegram Teaching Assistant

Telegram bot for the AUA NLP homework. It accepts lecture slides, extracts slide/page evidence, researches supporting resources, generates a teaching package with a local LLM, previews the email, and sends only after approval.

## Features

- Telegram commands: `/start`, `/help`, `/plan`, `/research`, `/status`, `/trace`, `/approve`, `/send`
- Slide parsing for PDF, PPTX, TXT, and Markdown
- Local LLM backend through vLLM or llama.cpp
- Web research with real URL fallback resources
- Preview-before-send approval workflow
- UTF-8 Markdown and Unicode-safe PDF attachments
- Armenian or Armenian/English output when requested with `language:`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` before running the bot. Never commit `.env`.

```bash
TELEGRAM_BOT_TOKEN=123456:telegram-token

LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL=Qwen/Qwen2.5-3B-Instruct
LLM_API_KEY=local
LLM_TIMEOUT_SECONDS=90

SEARCH_BACKEND=duckduckgo
SEARCH_TIMEOUT_SECONDS=10

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=eduagentbot@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=eduagentbot@gmail.com
SMTP_USE_TLS=true

TEACHING_BOT_PDF_FONT_PATH=
```

`SMTP_USERNAME` / `SMTP_FROM` configure the sender account only. `eduagentbot@gmail.com` may be the sender account, but it is not a default recipient. The recipient must always come from the user’s `/plan ... email: ...` command.

For Armenian PDF output, install a Unicode font with Armenian coverage. The PDF generator checks:

1. `TEACHING_BOT_PDF_FONT_PATH`
2. `assets/fonts/NotoSansArmenian-Regular.ttf`
3. `assets/fonts/NotoSans-Regular.ttf`
4. `assets/fonts/DejaVuSans.ttf`
5. `assets/fonts/Arial Unicode.ttf`
6. common system font locations

If needed, download Noto Sans Armenian or DejaVu Sans and place it in `assets/fonts/`, or set `TEACHING_BOT_PDF_FONT_PATH=/absolute/path/to/font.ttf`.

## Local LLM Startup

Use one of these local OpenAI-compatible backends.

vLLM:

```bash
source .venv/bin/activate
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8000
```

llama.cpp:

```bash
llama-server -m models/qwen2.5-3b-instruct-q4_k_m.gguf --host 0.0.0.0 --port 8000 --ctx-size 8192
```

Then set:

```bash
LLM_BASE_URL=http://localhost:8000/v1
LLM_MODEL=Qwen/Qwen2.5-3B-Instruct
LLM_API_KEY=local
```

## Model and Quantization

- Model: `Qwen/Qwen2.5-3B-Instruct` or compatible Qwen2.5 3B instruct GGUF.
- GGUF quantization: `Q4_K_M`.
- Context length: the llama.cpp command uses `--ctx-size 8192`.
- Why `Q4_K_M`: it reduces memory usage enough for laptop/small-GPU demos while preserving useful instruction-following quality for lesson planning.
- Runtime expectation: llama.cpp on laptop-class hardware may take roughly 20-90 seconds for a full package. vLLM is usually faster on a supported GPU.

## Run the Bot

In a second terminal after the LLM server is running:

```bash
source .venv/bin/activate
python bot.py
```

## Demo Workflow

1. Open the Telegram bot and run:

```text
/start
```

2. Upload `examples/sample_slides.pdf` or another PDF slide deck.

3. Run `/plan`. English example:

```text
/plan audience: NLP students; duration: 60; language: English; email: your@example.com
```

Armenian example:

```text
/plan audience: NLP students; duration: 60; language: Armenian; email: your@example.com
```

The bot generates a preview only. The `email:` field is required. The `language:` field controls the generated teaching package, preview, email body, Markdown attachment, and PDF attachment.

4. Optionally show web research:

```text
/research agentic teaching bot NLP resources
```

5. Inspect the preview returned by `/plan`. It should show recipient, subject, professional email body, attachment names, and Markdown preview.

6. Inspect state or trace:

```text
/status
/trace
```

7. Approve the latest preview:

```text
/approve
```

8. Send the email:

```text
/send
```

The bot sends only after `/approve`. If `/send` is called before approval, it returns a clear error.

## Output Example

A generated example is available in:

```text
examples/sample_output.md
```

It demonstrates Armenian/English output, a concise concept map/prerequisites section, slide/page grounding, useful links, Markdown/PDF attachment notes, and the current signature:

```text
Best,
Levon's Teaching Assistant Bot
```

## Attachments

Email delivery attaches:

- `teaching_package.md`
- `teaching_package.pdf`

Markdown is encoded as UTF-8. PDF generation uses ReportLab with `pdfmetrics.registerFont(TTFont(...))` and verifies non-Latin glyph coverage with `fonttools`. If Unicode PDF generation fails, the bot keeps the Markdown attachment and reports a warning instead of sending a broken question-mark PDF.

## Repository Structure

```text
agentic-teaching-bot/
  README.md
  .env.example
  .gitignore
  bot.py
  llm_backend.py
  design_report.md
  agents/
    orchestrator.py
    prompts.py
  tools/
    slides.py
    web_search.py
    email.py
  assets/
    fonts/
      README.md
  docs/
    requirements_checklist.md
  examples/
    sample_slides.pdf
    sample_output.md
  tests/
    test_workflow.py
```

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

If you want the Armenian PDF extraction test to run instead of skip, use the project virtualenv with `reportlab`, `pypdf`, and `fonttools` installed:

```bash
source .venv/bin/activate
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests
```

## Troubleshooting

### Telegram timeout

- Confirm the bot is running with `python bot.py`.
- Check `TELEGRAM_BOT_TOKEN` in `.env`.
- Stop any other process polling the same Telegram bot token.
- If the local LLM is slow, `/plan` may take time; use `/status` or check terminal logs.

### SMTP issues

- Use an app password for Gmail, not the normal account password.
- Set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, and `SMTP_USE_TLS=true`.
- Confirm `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM` are set.
- Remember: SMTP config is the sender account. The recipient must be supplied in `/plan`.

### Unicode PDF issues

- Install dependencies: `pip install -r requirements.txt`.
- Add a Unicode font with Armenian coverage to `assets/fonts/`, or set `TEACHING_BOT_PDF_FONT_PATH`.
- Recommended fonts: Noto Sans Armenian, Noto Sans, DejaVu Sans, Arial Unicode.
- If no suitable font is found, the bot sends Markdown and reports a PDF warning rather than sending a corrupted PDF.

## Notes

The app keeps sessions in memory for simplicity. It uses environment variables for all secrets and refuses to send email before explicit approval. If web search or the local LLM is unavailable, the workflow records the error and uses deterministic fallbacks so the system can still be demonstrated.
