import asyncio
import importlib.util
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import bot
import llm_backend
from agents.orchestrator import AgentState, TeachingAgent, parse_plan_arguments
from tools.email import (
    SIGNATURE,
    _font_candidates,
    _font_supports_codepoints,
    build_email,
    create_package_attachments,
    markdown_to_simple_pdf,
    preview_email,
)
from tools.slides import extract_concepts, parse_slides, retrieve, summarize
from tools.web_search import search_web


class FakeUser:
    id = 123


class FakeDownloadedFile:
    def __init__(self, text):
        self.text = text

    async def download_to_drive(self, path):
        Path(path).write_text(self.text, encoding="utf-8")


class FakeDocument:
    file_name = "slides.txt"

    async def get_file(self):
        return FakeDownloadedFile("Tokenization\n---\nEmbeddings and attention")


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.document = FakeDocument()
        self.replies = []

    async def reply_text(self, text):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, text=""):
        self.effective_user = FakeUser()
        self.message = FakeMessage(text)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        bot.SESSIONS.clear()
        os.environ["SEARCH_BACKEND"] = "off"

    def test_text_slide_parsing_and_retrieval(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("Tokenization and embeddings\n---\nTransformers use attention for context")
            path = handle.name
        try:
            chunks = parse_slides(path)
        finally:
            os.unlink(path)

        self.assertEqual(len(chunks), 2)
        self.assertIn("Tokenization", summarize(chunks))
        concepts = extract_concepts(chunks)
        self.assertTrue(concepts)
        evidence = retrieve(chunks, "attention context", limit=1)
        self.assertEqual(evidence[0]["page"], "2")

    def test_parse_plan_arguments(self):
        args = parse_plan_arguments(
            "/plan audience: AUA NLP students; duration: 80; language: English; email: teacher@example.com"
        )
        self.assertEqual(args["audience"], "AUA NLP students")
        self.assertEqual(args["duration_minutes"], 80)
        self.assertEqual(args["language"], "English")
        self.assertEqual(args["recipient_email"], "teacher@example.com")

    def test_orchestrator_fallback_package_and_approval(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("Agentic workflow\n---\nEmail preview and confirmation")
            path = handle.name
        state = AgentState(user_id="test")
        agent = TeachingAgent(state)
        try:
            agent.ingest_slides(path)
        finally:
            os.unlink(path)

        agent.configure(
            audience="NLP students",
            duration_minutes=60,
            language="English",
            recipient_email="teacher@example.com",
        )
        package = agent.build_package()
        self.assertIn("Concept Map / Prerequisites", package)
        self.assertIn("Key topics", package)
        self.assertIn("Learning Objectives", package)
        self.assertIsNotNone(state.email_draft)
        self.assertFalse(state.approved)
        agent.approve()
        self.assertTrue(state.approved)

    def test_upload_does_not_generate_preview(self):
        update = FakeUpdate()

        asyncio.run(bot.handle_document(update, object()))

        state = bot.SESSIONS[str(FakeUser.id)]
        self.assertIn("Slides parsed successfully", update.message.replies[-1])
        self.assertIn("/plan audience:", update.message.replies[-1])
        self.assertEqual(state.package_markdown, "")
        self.assertIsNone(state.email_draft)
        self.assertFalse(state.approved)

    def test_start_and_help_use_generic_plan_example(self):
        start_update = FakeUpdate()
        help_update = FakeUpdate()

        asyncio.run(bot.start(start_update, object()))
        asyncio.run(bot.help_command(help_update, object()))

        self.assertIn("email: your@example.com", start_update.message.replies[-1])
        self.assertIn("email: your@example.com", help_update.message.replies[-1])
        self.assertNotIn("levon_gevorgyan@edu.aua.am", start_update.message.replies[-1])
        self.assertNotIn("levon_gevorgyan@edu.aua.am", help_update.message.replies[-1])
        self.assertIn("language field controls the output language", start_update.message.replies[-1])

    def test_plan_generates_preview(self):
        update = FakeUpdate(
            "/plan audience: AUA NLP students; duration: 50; language: English; email: teacher@example.com"
        )
        state = bot.SESSIONS.setdefault(str(FakeUser.id), AgentState(user_id=str(FakeUser.id)))
        agent = TeachingAgent(state)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("Tokenization\n---\nEmbeddings and attention")
            path = handle.name
        try:
            agent.ingest_slides(path)
        finally:
            os.unlink(path)

        with patch.object(llm_backend, "generate", side_effect=llm_backend.LLMError("offline")):
            asyncio.run(bot.plan(update, object()))

        self.assertTrue(state.package_markdown)
        self.assertIsNotNone(state.email_draft)
        self.assertFalse(state.approved)
        self.assertTrue(any("Preview before sending" in reply for reply in update.message.replies))

    def test_approve_changes_state_correctly(self):
        state = AgentState(user_id="test", package_markdown="# Package")
        agent = TeachingAgent(state)

        agent.approve()

        self.assertTrue(state.approved)

    def test_trace_shows_state_and_package_preview(self):
        update = FakeUpdate()
        state = bot.SESSIONS.setdefault(str(FakeUser.id), AgentState(user_id=str(FakeUser.id)))
        state.slide_path = "slides.pdf"
        state.package_markdown = "# Package\n\nLatest content"
        state.last_send_status = "not sent"
        state.log("Generated package.")

        asyncio.run(bot.trace(update, object()))

        reply = update.message.replies[-1]
        self.assertIn("Agent trace summary", reply)
        self.assertIn("Uploaded file: slides.pdf", reply)
        self.assertIn("Latest package preview", reply)
        self.assertIn("# Package", reply)
        self.assertIn("Last send status: not sent", reply)

    def test_send_requires_approval(self):
        update = FakeUpdate()
        state = bot.SESSIONS.setdefault(str(FakeUser.id), AgentState(user_id=str(FakeUser.id)))
        state.email_draft = build_email("teacher@example.com", "# Package", "Lecture")
        state.approved = False

        asyncio.run(bot.send(update, object()))

        self.assertEqual(
            update.message.replies[-1],
            "Please approve the latest preview with /approve before sending.",
        )

    def test_missing_email_in_plan_causes_clear_error_and_no_send(self):
        update = FakeUpdate("/plan audience: YSU NLP students; duration: 60; language: Armenian")
        state = bot.SESSIONS.setdefault(str(FakeUser.id), AgentState(user_id=str(FakeUser.id)))
        agent = TeachingAgent(state)
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("Tokenization\n---\nEmbeddings and attention")
            path = handle.name
        try:
            agent.ingest_slides(path)
        finally:
            os.unlink(path)

        with patch.object(TeachingAgent, "build_package") as build_package:
            asyncio.run(bot.plan(update, object()))

        self.assertEqual(
            update.message.replies[-1],
            "Please provide a recipient email in the /plan command.",
        )
        build_package.assert_not_called()
        self.assertEqual(state.recipient_email, "")
        self.assertIsNone(state.email_draft)
        self.assertFalse(state.approved)

        send_update = FakeUpdate()
        asyncio.run(bot.send(send_update, object()))
        self.assertEqual(
            send_update.message.replies[-1],
            "Please provide a recipient email in the /plan command.",
        )

    def test_no_default_recipient_is_used(self):
        self.assertEqual(AgentState(user_id="test").recipient_email, "")

    def test_email_preview_contains_no_send_side_effect(self):
        draft = build_email("teacher@example.com", "# Package", "Lecture", "English")
        preview = preview_email(draft)
        self.assertIn("To: teacher@example.com", preview)
        self.assertIn("Attachment", preview)
        self.assertIn("teaching_package.md", preview)
        if not draft.warnings:
            self.assertIn("teaching_package.pdf", preview)
        else:
            self.assertIn("PDF generation failed", preview)
        self.assertIn(SIGNATURE, preview)

    @unittest.skipUnless(
        importlib.util.find_spec("reportlab"),
        "ReportLab is required for PDF attachment generation.",
    )
    def test_markdown_and_pdf_attachment_generation(self):
        attachments, warnings = create_package_attachments("# Package\n\nBody")

        self.assertEqual(warnings, [])
        self.assertEqual([attachment.name for attachment in attachments], [
            "teaching_package.md",
            "teaching_package.pdf",
        ])
        self.assertTrue(attachments[1].content.startswith(b"%PDF-"))

    @unittest.skipUnless(
        importlib.util.find_spec("reportlab") and importlib.util.find_spec("pypdf"),
        "ReportLab and pypdf are required for PDF text extraction regression test.",
    )
    def test_armenian_pdf_text_extracts_without_question_marks(self):
        armenian = "# Հայերեն դասավանդման փաթեթ\n\n## Ուսումնական նպատակներ\n- Բացատրել թեման։"
        required = {ord(char) for char in armenian if ord(char) > 0x024F and not char.isspace()}
        self.assertTrue(
            any(_font_supports_codepoints(path, required, font_number) for path, font_number in _font_candidates()),
            "A Unicode font with Armenian coverage is required for this test.",
        )

        pdf_bytes = markdown_to_simple_pdf(armenian)

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(pdf_bytes))
        extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("Հայերեն", extracted)
        self.assertNotIn("????", extracted)

    def test_pdf_generation_failure_keeps_markdown_attachment(self):
        with patch("tools.email.markdown_to_simple_pdf", side_effect=RuntimeError("missing renderer")):
            attachments, warnings = create_package_attachments("# Package")

        self.assertEqual([attachment.name for attachment in attachments], ["teaching_package.md"])
        self.assertIn("PDF generation failed", warnings[0])

    def test_armenian_language_reaches_prompt_and_output(self):
        captured_prompts = []

        def fake_generate(messages, **kwargs):
            captured_prompts.append(messages[-1]["content"])
            return "# Հայերեն դասավանդման փաթեթ\n\n## Ուսումնական նպատակներ\n- Բացատրել թեման։"

        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("Tokenization\n---\nEmbeddings and attention")
            path = handle.name
        state = AgentState(user_id="test")
        agent = TeachingAgent(state)
        try:
            agent.ingest_slides(path)
        finally:
            os.unlink(path)

        agent.configure(
            audience="YSU NLP students",
            duration_minutes=60,
            language="Armenian",
            recipient_email="teacher@example.com",
        )
        with patch.object(llm_backend, "generate", side_effect=fake_generate):
            package = agent.build_package()

        self.assertIn("Output language: Armenian", captured_prompts[0])
        self.assertIn('Concept Map / Prerequisites', captured_prompts[0])
        self.assertIn("Հայերեն դասավանդման փաթեթ", package)
        self.assertIsNotNone(state.email_draft)
        self.assertIn("Բարեւ", state.email_draft.body)
        self.assertIn("Հայերեն դասավանդման փաթեթ", state.email_draft.attachment_text)

    def test_armenian_fallback_includes_concept_map(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            handle.write("Agentic workflow\n---\nLocal LLM backend\n---\nEmail approval")
            path = handle.name
        state = AgentState(user_id="test")
        agent = TeachingAgent(state)
        try:
            agent.ingest_slides(path)
        finally:
            os.unlink(path)

        agent.configure(
            audience="NLP students",
            duration_minutes=60,
            language="Armenian",
            recipient_email="teacher@example.com",
        )
        with patch.object(llm_backend, "generate", side_effect=llm_backend.LLMError("offline")):
            package = agent.build_package()

        self.assertIn("## Հասկացությունների քարտեզ / Նախապայմաններ", package)
        self.assertIn("Հիմնական թեմաներ", package)
        self.assertIn("Հավանական նախապայմաններ", package)

    def test_search_fallback_has_real_urls(self):
        os.environ["SEARCH_BACKEND"] = "off"
        results = search_web("NLP", limit=3)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(item["url"].startswith("https://") for item in results))


if __name__ == "__main__":
    unittest.main()
