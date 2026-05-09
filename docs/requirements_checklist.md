# Homework Requirements Checklist

Audit date: 2026-05-09  
Project: `agentic-teaching-bot`

## Requirements Checklist

| Requirement from homework | Status | Evidence in the project | Notes or remaining fixes |
| --- | --- | --- | --- |
| Expected flow: `/start` gives short help/example | Met | `bot.py` implements `start()` and registers `CommandHandler("start", start)`. The message says to upload a PDF and run `/plan ... email: your@example.com`. | Current message is generic and does not expose a personal email. |
| Expected flow: user uploads lecture slides, preferably PDF | Met | `bot.py::handle_document()` downloads Telegram documents; `tools/slides.py::parse_slides()` supports `.pdf`, `.pptx`, `.txt`, and `.md`; `examples/sample_slides.pdf` exists. | PPTX support is implemented as a bonus through direct XML extraction. |
| Expected flow: user provides lecture duration, target audience, output language, and recipient email | Met | `agents/orchestrator.py::parse_plan_arguments()` parses `audience`, `duration`, `language`, and email; `bot.py::plan()` rejects missing email with `Please provide a recipient email in the /plan command.` | Good: no default recipient is used. |
| Expected flow: after upload, bot parses slides but does not generate full preview | Met | `bot.py::handle_document()` calls `agent.ingest_slides()` and replies `Slides parsed successfully. Now run: /plan ...`; `tests/test_workflow.py::test_upload_does_not_generate_preview`. | Matches the corrected homework flow. |
| Expected flow: bot parses slides, calls local LLM, searches web, drafts package, and shows preview after `/plan` | Met | `TeachingAgent.build_package()` calls `research()` if needed, builds prompt, calls `llm_backend.generate()` twice, stores `package_markdown`, builds `email_draft`; `bot.py::plan()` sends `preview_email(...)`. | If local LLM is unavailable, deterministic fallback is used and logged. That is acceptable for reliability, but demo should show local LLM running if possible. |
| Expected flow: bot sends email only after approval | Met | `bot.py::send()` checks `agent.state.email_draft` and `agent.state.approved`; `TeachingAgent.approve()` sets approval only after package exists; `tests/test_workflow.py::test_send_requires_approval`. | `/approve` is implemented even though not in the minimal command list. |
| Minimal command: `/start` | Met | `bot.py` registers `CommandHandler("start", start)`. | None. |
| Minimal command: `/help` | Met | `HELP_TEXT` and `CommandHandler("help", help_command)` in `bot.py`. | Help explains email is required and `language:` controls output language. |
| Minimal command: `/plan` | Met | `bot.py::plan()` and `CommandHandler("plan", plan)`. | Requires uploaded slides and recipient email. |
| Minimal command: `/research` | Met | `bot.py::research()` calls `agent.research(topic)` and returns compact resource list. | Useful for demoing the web research step independently. |
| Minimal command: `/status` | Met | `bot.py::status()` replies with `agent.status()`; `AgentState.logs` records workflow events. | Status includes uploaded file, chunks, audience, duration, language, recipient, resources, package ready, approval, last error, and recent logs. |
| Minimal command: `/send` | Met | `bot.py::send()` sends only approved `email_draft`. | Clear errors for missing email draft and missing approval. |
| Extra command: `/approve` | Met | `bot.py::approve()` and `TeachingAgent.approve()`; tests cover state change. | This command satisfies the expected preview-confirm-send flow. |
| Architecture: Telegram Bot API | Met | `python-telegram-bot` in `requirements.txt`; `Application.builder().token(token).build()` in `bot.py`. | None. |
| Architecture: session state | Met | Global `SESSIONS: dict[str, AgentState]` in `bot.py`; `AgentState` dataclass in `agents/orchestrator.py`. | In-memory state is acceptable for homework; production would need persistence. |
| Architecture: agent/orchestrator | Met | `agents/orchestrator.py::TeachingAgent` coordinates ingestion, configuration, research, package generation, approval, and status. | Simple finite-state design is clear and debuggable. |
| Architecture: slide parser/retriever | Met | `tools/slides.py` includes `parse_slides()`, `summarize()`, `extract_concepts()`, and `retrieve()`. | Retrieval is lightweight keyword overlap, not vector RAG. Acceptable for assignment scale, but could be improved. |
| Architecture: web search tool | Met | `tools/web_search.py::search_web()` uses DuckDuckGo HTML and curated fallback URLs. | Avoids fake references by falling back to known real NLP resources. |
| Architecture: email sender | Met | `tools/email.py::build_email()`, `preview_email()`, and `send_email()` implement draft, preview, attachments, SMTP sending. | Uses environment variables for SMTP. |
| Architecture: logger/status | Met | `AgentState.log()` records recent workflow events; `TeachingAgent.status()` exposes logs and errors; `/trace` shows a compact trace and latest package preview. | `/trace` is a lightweight text trace rather than a graphical dashboard. |
| Architecture: local LLM backend through vLLM or llama.cpp | Met | `llm_backend.py::generate(messages, temperature, max_tokens)` calls an OpenAI-compatible `/chat/completions` endpoint; README and `design_report.md` document vLLM and llama.cpp commands. | Main system is local-LLM oriented. |
| Local LLM: vLLM supported | Met | README command: `python -m vllm.entrypoints.openai.api_server --model Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8000`. | Good. |
| Local LLM: llama.cpp supported | Met | README command: `llama-server -m models/qwen2.5-3b-instruct-q4_k_m.gguf --host 0.0.0.0 --port 8000 --ctx-size 8192`. | Good. |
| Local LLM: `generate(messages, temperature, max_tokens)` wrapper | Met | `llm_backend.py::generate(messages, temperature=0.2, max_tokens=1800)`. | Signature matches homework recommendation. |
| Local LLM: model name documented | Met | README and `design_report.md` use `Qwen/Qwen2.5-3B-Instruct`; `.env.example` has `LLM_MODEL=local-model`. | README is clearer than `.env.example`; acceptable. |
| Local LLM: quantization documented if any | Met | README and `design_report.md` explicitly document `Q4_K_M`, why it was selected, and runtime/hardware tradeoffs. | Good. |
| Local LLM: context length documented | Met | README llama.cpp command includes `--ctx-size 8192`; design report says the command uses `--ctx-size 8192`. | vLLM context length is not separately specified; model default is implied. |
| Local LLM: exact server command documented | Met | README and design report include exact vLLM and llama.cpp commands. | None. |
| Local LLM: no cloud model as main system | Met | `llm_backend.py` only targets `LLM_BASE_URL`; README says local LLM; design report says local OpenAI-compatible server. | No cloud SDK dependency exists. |
| Agent workflow: slide ingestion with slide/page references | Met | `SlideChunk.page`; `_evidence_to_text()` emits `Slide/page {page}`; fallback package has grounding notes with slide/page references. | Good. |
| Agent workflow: short summary | Met | `tools/slides.py::summarize()`; `TeachingAgent.ingest_slides()` returns summary; `build_package()` includes `slide_summary` in prompt. | Upload no longer displays summary, but summary is still part of planning. |
| Agent workflow: concept map/main concepts/prerequisites | Met | `extract_concepts()` lists main concepts; prompts require "Concept Map / Prerequisites"; deterministic English and Armenian fallbacks include the section. | Good. |
| Agent workflow: timed teaching plan | Met | Prompt requires timed plan; fallback output includes `## Timed Teaching Plan` or Armenian equivalent with minute ranges. | Tests check package generation, but not detailed timing sum. |
| Agent workflow: examples/exercises/recap | Met | Prompt requires exercise and recap/check; fallback has `## In-Class Exercise` and recap row. | Good. |
| Agent workflow: at least 3 external resources with URLs and justifications | Met | `search_web(query, limit=3)`; fallback resources list three real URLs; `resources_to_markdown()` includes URL and snippet. | DuckDuckGo parsing can fail, but curated fallback preserves the requirement. |
| Agent workflow: revision/quality check | Met | `TeachingAgent.build_package()` calls `llm_backend.generate()` once for draft and once with `prompts.REVISION_PROMPT`. | If LLM is unavailable, fallback skips model revision but still produces structured output. |
| Agent workflow: professional email body | Met | `tools/email.py::_localized_email_text()` builds English/Armenian email body with `Levon's Teaching Assistant Bot` signature; package fallback and `examples/sample_output.md` include current signature. | Good. |
| Agent workflow: email only after confirmation | Met | `/plan` previews; `/approve` marks latest preview; `/send` requires approval. | Good. |
| Minimum technical expectation: four tools exposed | Met | Slide parsing/retrieval: `tools/slides.py`; web search: `tools/web_search.py`; email sending: `tools/email.py`; logging/status: `AgentState.log()` and `/status`. | Tools are simple Python modules, not separate framework tool objects. Acceptable. |
| Final package includes title | Met | Prompt requires H1 title; fallback starts with `# {title}`. | LLM output depends on model following prompt, but fallback is compliant. |
| Final package includes audience and duration | Met | Prompt and fallback include audience/duration. | Good. |
| Final package includes learning objectives | Met | Prompt and fallback include objectives. | Good. |
| Final package includes timed plan | Met | Prompt and fallback include timed plan. | Good. |
| Final package includes at least one exercise | Met | Prompt and fallback include in-class exercise. | Good. |
| Final package includes useful links | Met | Prompt and fallback include useful links; search fallback has real URLs. | Good. |
| Final package includes short email body | Met | Prompt and fallback include email body; actual outgoing email body generated by `tools/email.py`. | Sample output is stale. |
| Secrets are not committed | Partially Met | `.env.example` contains no secrets; README warns not to commit secrets; code reads env vars. | A real `.env` file exists locally in the project tree. It was not inspected here and should not be committed. Ensure `.gitignore` excludes `.env` before submission. |
| Environment variables are used | Met | `TELEGRAM_BOT_TOKEN`, `LLM_*`, `SEARCH_*`, `SMTP_*`, and `TEACHING_BOT_PDF_FONT_PATH` are read from env. | Good. |
| Email preview appears before sending | Met | `bot.py::plan()` replies with `Preview before sending`; tests cover preview generation. | Good. |
| Bad files handled without crashing | Met | `handle_document()` catches exceptions and replies `Could not parse the file: ...`; `parse_slides()` raises clear unsupported-file errors. | Good. |
| Missing email handled without crashing | Met | `bot.py::plan()` and `bot.py::send()` reply `Please provide a recipient email in the /plan command.`; tests cover it. | Good. |
| Failed web search handled without crashing | Met | `tools/web_search.py::search_web()` catches exceptions and returns curated fallback resources. | Good. |
| Recommended structure: `README.md` | Met | Present at repo root. | Good. |
| Recommended structure: `.env.example` | Met | Present at repo root. | Good. |
| Recommended structure: `bot.py` | Met | Present at repo root. | Good. |
| Recommended structure: `llm_backend.py` | Met | Present at repo root. | Good. |
| Recommended structure: `agents/orchestrator.py` | Met | Present. | Good. |
| Recommended structure: `agents/prompts.py` | Met | Present. | Good. |
| Recommended structure: `tools/slides.py` | Met | Present. | Good. |
| Recommended structure: `tools/web_search.py` | Met | Present. | Good. |
| Recommended structure: `tools/email.py` | Met | Present. | Good. |
| Recommended structure: `examples/sample_slides.pdf` | Met | Present. | Good. |
| Recommended structure: `examples/sample_output.md` | Met | Present and regenerated with current signature, Armenian/English content, grounding notes, and Markdown/PDF attachment note. | Good. |
| Structure differences | Met | Additional `tests/`, `docs/`, `assets/fonts/`, `design_report.md`, `requirements.txt`. | Differences are acceptable and improve deliverables. Remove `__pycache__/`, `.venv/`, and `.env` from any final commit if tracked. |
| Individual deliverable: setup instructions | Met | README has setup, run, LLM server commands, tests, env notes. | Good. |
| Individual deliverable: `.env.example` | Met | Present, no secrets, includes Telegram/LLM/search/SMTP/PDF font env vars. | Good. |
| Individual deliverable: sample generated teaching package | Met | `examples/sample_output.md` exists and reflects current language/signature/attachment behavior. | Good. |
| Individual deliverable: design report 2-4 pages | Met | `design_report.md` exists with architecture, model choice, prompts, reliability, evaluation, limitations. | Likely within 2-4 pages when rendered, but update it for latest PDF/font changes and no-default-recipient behavior. |
| Individual deliverable: evaluation section with at least 3 test cases | Met | `design_report.md` has three test cases plus latency note; `tests/test_workflow.py` has 16 unit tests. | Good. |
| Individual deliverable: demo instructions upload -> plan -> research -> preview -> email | Met | README has an explicit demo sequence: upload -> `/plan` -> optional `/research` -> preview -> `/status`/`/trace` -> `/approve` -> `/send`. | Good. |
| Evaluation: functional test | Met | `design_report.md` test case 1; unit tests cover upload, plan, approve, send gates. | Good. |
| Evaluation: grounding check | Met | `design_report.md` test case 2; fallback package has grounding notes. | Good. |
| Evaluation: failure test | Met | `design_report.md` test case 3; unit tests cover missing email, send before approval, PDF failure. | Good. |
| Evaluation: latency note | Met | `design_report.md` includes expected local llama.cpp latency and fallback latency. | Good. |
| Bonus: Armenian or bilingual Armenian/English plans | Met | Prompts instruct Armenian/bilingual output; fallback has Armenian sections; `tools/email.py` localizes Armenian email body; tests cover Armenian prompt/output and PDF extraction. | Bilingual output depends on LLM following prompt; deterministic fallback treats Armenian/English as Armenian plus bilingual email body. |
| Bonus: PDF or Markdown attachment | Met | `tools/email.py::create_package_attachments()` always creates UTF-8 Markdown and tries PDF; PDF uses registered Unicode font. | If PDF generation fails, Markdown is still sent with warning. |
| Bonus: simple dashboard for inspecting agent traces | Partially Met | `/trace` command exposes uploaded file, current state, latest package preview, last send status, and recent logs. | Text trace only, not a graphical dashboard. |
| Bonus: compare vLLM vs llama.cpp latency/output quality | Partially Met | README and `design_report.md` include a practical comparison of latency, simplicity, and hardware requirements. | Not a measured benchmark with graphs. |

## Estimated Grading Score

| Category | Estimated points | Justification |
| --- | ---: | --- |
| Telegram bot UX /10 | 10 | Clear commands, upload guidance, preview-before-send, approval gate, `/status`, `/trace`, and clear error messages. |
| Local LLM backend /12 | 12 | Clean OpenAI-compatible local wrapper, vLLM/llama.cpp commands, env config, no cloud main system, explicit model/quantization/context documentation. |
| Slide understanding/RAG /15 | 13 | PDF/PPTX/TXT/MD parsing, chunks with slide/page refs, summary, retrieval, concept extraction, and explicit concept map/prerequisites section. Retrieval is keyword-based rather than embedding/vector RAG. |
| Agent workflow /18 | 16 | Multi-step workflow with ingestion, research, LLM draft, revision, preview, approval, send, logs. Minor gap: fallback path does not run model revision and concept-map section could be clearer. |
| Web research /10 | 9 | DuckDuckGo search plus curated real fallback URLs and snippets. Could improve source relevance ranking and richer justifications. |
| Email integration /8 | 8 | Env-based SMTP, professional localized body, explicit confirmation, Markdown/PDF attachments, Unicode PDF handling, missing config errors. |
| Output quality /15 | 13 | Improved title/summary/objectives/timing/exercise/grounding, Armenian support, useful links. Sample output is stale and should be regenerated. |
| Evaluation/report /8 | 8 | Design report covers architecture, workflow, local LLM details, quantization, failure handling, backend comparison, evaluation, and latency; tests are strong. |
| Code quality /4 | 4 | Modular, readable, focused tests, graceful fallbacks, no cloud lock-in. Check final commit excludes `.env`, `.venv`, and `__pycache__`. |
| **Total /100** | **95** | Strong submission. Remaining gaps are mostly optional: vector RAG, graphical dashboard, and measured backend benchmarks. |

## Bonus Checklist

| Bonus idea | Status | Evidence | Smallest remaining fix |
| --- | --- | --- | --- |
| Armenian or bilingual Armenian/English plans | Met | `agents/prompts.py`, `llm_backend.py` Armenian fallback, `tools/email.py` Armenian email body, Armenian PDF test. | For bilingual, add a unit test with `language: Armenian/English`. |
| PDF or Markdown attachment | Met | `tools/email.py` creates `teaching_package.md` and `teaching_package.pdf` when PDF generation succeeds; Markdown remains on PDF failure. | None. |
| Simple dashboard for inspecting agent traces | Partially Met | `/trace` command provides a text trace and latest package preview. | Add a graphical dashboard only if extra time remains. |
| Compare vLLM vs llama.cpp latency/output quality | Partially Met | README and design report include a concise practical comparison. | Add measured benchmark numbers only if extra time remains. |

## Highest-Priority Fixes Before Submission

1. Ensure `.env`, `.venv/`, and `__pycache__/` are not tracked in the submitted repository.
2. Optionally add measured vLLM vs llama.cpp benchmark numbers if you have time and hardware access.
