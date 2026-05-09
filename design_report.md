# Design Report: Agentic Telegram Teaching Assistant

## Architecture

The project implements a compact agentic workflow around Telegram commands. `bot.py` handles the Telegram UI, command routing, file download, and per-user session lookup. Session state is stored as one `AgentState` per Telegram user in memory. `agents/orchestrator.py` owns the workflow: slide ingestion, concept extraction, web research, package generation, preview creation, approval state, trace logs, and status reporting.

The tool layer is intentionally simple and auditable:

- `tools/slides.py` parses PDF, PPTX, TXT, and Markdown files into `SlideChunk(page, text)` records. It also provides short summaries, keyword concept extraction, and slide/page retrieval.
- `tools/web_search.py` searches DuckDuckGo HTML and falls back to three curated real NLP resources if search fails.
- `tools/email.py` builds a previewable email draft, creates UTF-8 Markdown plus PDF attachments, and sends through SMTP.
- `llm_backend.py` wraps a local OpenAI-compatible chat completions endpoint, suitable for either vLLM or llama.cpp.

The workflow is a finite-state design rather than a heavy graph framework. Uploading slides only parses and stores chunks; it does not generate a package. `/plan` requires `audience`, `duration`, `language`, and `email`, then runs research, local LLM draft generation, revision, and preview. `/approve` marks the latest preview as approved. `/send` refuses to send until the latest preview is approved. `/status` and `/trace` expose current state, recent logs, and the latest package preview.

## Local LLM Backend

The main system uses a local OpenAI-compatible LLM endpoint. No cloud model is used as the main backend. The wrapper is:

```python
generate(messages, temperature=0.2, max_tokens=1800)
```

It sends requests to `${LLM_BASE_URL}/chat/completions`, with `LLM_MODEL`, `LLM_API_KEY`, and timeout controlled by environment variables.

Recommended vLLM command:

```bash
python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8000
```

Recommended llama.cpp command:

```bash
llama-server -m models/qwen2.5-3b-instruct-q4_k_m.gguf --host 0.0.0.0 --port 8000 --ctx-size 8192
```

Model name: `Qwen/Qwen2.5-3B-Instruct` for vLLM, or a compatible Qwen2.5 3B instruct GGUF for llama.cpp. The GGUF example uses `Q4_K_M` quantization, which is a practical balance for laptops and small GPUs: much lower memory use than full precision while usually preserving enough instruction-following quality for this homework. The approximate context length used in the llama.cpp example is 8192 tokens. On CPU or small GPU hardware, generation is expected to take roughly 20-90 seconds depending on prompt length and machine speed; vLLM is faster when a supported GPU is available.

## Prompting and Agent Workflow

Prompts live in `agents/prompts.py`. The package prompt receives audience, duration, output language, slide summary, extracted concepts, retrieved slide evidence, and web resources. The local LLM first drafts the teaching package. A second revision prompt asks it to improve realism, timing, clarity, grounding, and link quality.

The final package is expected to include:

- title, audience, duration, and output language;
- slide summary with slide/page references;
- a concise Concept Map / Prerequisites section;
- learning objectives;
- timed teaching plan;
- in-class exercise and recap/checks;
- useful links with justifications;
- grounding notes distinguishing slide-based and web-based claims;
- a short professional email body.

If the local LLM is unavailable, the orchestrator records the error and produces a deterministic fallback package so the Telegram flow remains demoable. This fallback supports Armenian output and uses slide/page references and curated real URLs.

## Email, Attachments, and Approval

There is no default recipient. The recipient must come from the current `/plan` command. If the user omits `email: ...`, the bot replies:

```text
Please provide a recipient email in the /plan command.
```

The SMTP account configured in `.env` is the sender account only. For example, `SMTP_USERNAME=eduagentbot@gmail.com` means the bot sends from that Gmail account; it is not a default recipient.

Email sending is split into preview and delivery. `/plan` creates a preview only. `/approve` approves the latest preview. `/send` sends only if that latest preview is approved. The email body is localized for Armenian when `language: Armenian` or `language: Armenian/English` is requested and uses the current signature:

```text
Best,
Levon's Teaching Assistant Bot
```

The email draft includes both `teaching_package.md` and `teaching_package.pdf` when PDF generation succeeds. Markdown content is encoded as UTF-8. PDF generation uses ReportLab with an explicitly registered Unicode TTF/TTC font. The generator checks `TEACHING_BOT_PDF_FONT_PATH`, `assets/fonts/`, and common system font locations for fonts such as Noto Sans Armenian, Noto Sans, DejaVu Sans, or Arial Unicode. For Armenian/non-Latin text, the code verifies glyph coverage with `fonttools`; it does not fall back to Helvetica and create question-mark output. If PDF generation fails, the bot sends the Markdown attachment and reports a clear warning.

## Failure Handling and Security

The bot handles common failures without crashing:

- unsupported or unreadable slide files return a clear parse error;
- missing recipient email blocks `/plan` and `/send`;
- failed web search falls back to curated real URLs;
- unavailable local LLM is logged and triggers deterministic fallback generation;
- missing SMTP settings produce a user-facing email configuration error;
- failed Unicode PDF generation sends Markdown and reports a warning.

Secrets are loaded from environment variables. `.env.example` documents all configuration keys without secrets. `.env`, `.venv/`, generated attachments, and cache files are ignored by `.gitignore`.

## Practical Backend Comparison

| Backend | Latency | Simplicity | Hardware requirements | Notes |
| --- | --- | --- | --- | --- |
| llama.cpp | Moderate to slow on CPU; faster on Apple Silicon/GPU builds | Simple single binary/server once model is downloaded | Works on CPU and small GPUs; GGUF quantization reduces memory | Best default for a lightweight homework demo. `Q4_K_M` is a practical quality/memory tradeoff. |
| vLLM | Usually fastest when GPU is available | Easy OpenAI-compatible API, but install/runtime are heavier | Requires a compatible GPU for best results | Better throughput and latency for repeated demos if hardware supports it. |

## Evaluation

Test case 1, functional flow: upload `examples/sample_slides.pdf`, run `/plan audience: NLP students; duration: 60; language: English; email: teacher@example.com`, inspect the preview, run `/approve`, then `/send` with SMTP configured. Expected result: package is generated, preview appears before email, and email sending is blocked until approval.

Test case 2, grounding check: inspect the package grounding notes and verify that claims about local LLM, web research, preview, and email confirmation are traceable to slide/page chunks or listed web URLs. Expected result: slide-based claims are explicitly marked separately from web resources.

Test case 3, failure behavior: run `/plan` without `email:`, upload an unsupported file, or run `/send` before `/approve`. Expected result: the bot returns a clear error and `/status` or `/trace` shows the latest state and error.

Test case 4, Armenian/PDF behavior: run `/plan audience: NLP students; duration: 60; language: Armenian; email: teacher@example.com`. Expected result: package, preview, email body, Markdown, and PDF content are Armenian-capable; extracted PDF text should not turn into question marks when a Unicode font is available.

Latency note: a local llama.cpp 3B `Q4_K_M` model is expected to take roughly 20-90 seconds for full package generation on laptop-class hardware. The deterministic fallback returns in under a second and is used only to keep the integration flow testable when the model server is down.

## Limitations

The slide retriever is keyword-based rather than embedding/vector RAG. Session state is in memory, so a restart loses uploaded-file state. DuckDuckGo HTML can be rate-limited, although curated fallback resources prevent fake links. The `/trace` command is a lightweight trace view, not a full dashboard. vLLM vs llama.cpp comparison is practical/documentary rather than a formal benchmark.
