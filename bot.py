from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = lambda: None

from agents.orchestrator import AgentState, TeachingAgent, parse_plan_arguments
from tools.email import preview_email, send_email


load_dotenv()

SESSIONS: dict[str, AgentState] = {}


def get_agent(user_id: str) -> TeachingAgent:
    state = SESSIONS.setdefault(user_id, AgentState(user_id=user_id))
    return TeachingAgent(state)


HELP_TEXT = """I prepare teaching packages from lecture slides.

Commands:
/start - show a short example
/help - list commands and limitations
/plan audience: your audience, e.g. NLP students; duration: number of minutes, e.g. 60; language: your output language, e.g. Armenian or English; email: your@example.com
/research optional topic - collect supporting resources
/status - show uploaded files, state, and errors
/trace - show a compact agent trace and latest package preview
/approve - approve the latest preview
/send - send the approved package by email

Upload a PDF first. PPTX, TXT, and Markdown are also supported.
The email field is required in /plan.
The language field controls the output language of the generated teaching package."""


async def start(update, context) -> None:
    await update.message.reply_text(
        "I prepare teaching packages from lecture slides.\n\n"
        "Upload a PDF, then run:\n"
        "/plan audience: your audience, e.g. NLP students; duration: number of minutes, e.g. 60; "
        "language: your output language, e.g. Armenian or English; email: your@example.com\n\n"
        "The email field is required. The language field controls the output language of the generated teaching package.\n"
        "Use /help for all commands."
    )


async def help_command(update, context) -> None:
    await update.message.reply_text(HELP_TEXT)


async def handle_document(update, context) -> None:
    agent = get_agent(str(update.effective_user.id))
    document = update.message.document
    suffix = Path(document.file_name or "").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
    try:
        file = await document.get_file()
        await file.download_to_drive(tmp_path)
        agent.ingest_slides(tmp_path)
        await update.message.reply_text(
            "Slides parsed successfully. Now run:\n"
            "/plan audience: your audience, e.g. NLP students; duration: number of minutes, e.g. 60; "
            "language: your output language, e.g. Armenian or English; email: your@example.com"
        )
    except Exception as exc:
        agent.state.last_error = str(exc)
        await update.message.reply_text(f"Could not parse the file: {exc}")


async def plan(update, context) -> None:
    agent = get_agent(str(update.effective_user.id))
    args = parse_plan_arguments(update.message.text or "")
    if "recipient_email" not in args:
        agent.state.recipient_email = ""
        agent.state.email_draft = None
        agent.state.approved = False
        await update.message.reply_text("Please provide a recipient email in the /plan command.")
        return
    agent.configure(**args)
    await update.message.reply_text("Running planning workflow. This may take a moment.")
    try:
        package = await asyncio.to_thread(agent.build_package)
        preview = preview_email(agent.state.email_draft) if agent.state.email_draft else package
        await update.message.reply_text(f"Preview before sending:\n\n{preview[:3500]}")
    except Exception as exc:
        agent.state.last_error = str(exc)
        await update.message.reply_text(f"Planning failed: {exc}")


async def research(update, context) -> None:
    agent = get_agent(str(update.effective_user.id))
    topic = " ".join(context.args) if context.args else None
    resources = await asyncio.to_thread(agent.research, topic)
    text = "\n".join(f"- {item['title']}: {item['url']}\n  {item['snippet']}" for item in resources)
    await update.message.reply_text(text or "No resources found.")


async def status(update, context) -> None:
    agent = get_agent(str(update.effective_user.id))
    await update.message.reply_text(agent.status()[:3500])


async def trace(update, context) -> None:
    agent = get_agent(str(update.effective_user.id))
    await update.message.reply_text(agent.trace()[:3500])


async def approve(update, context) -> None:
    agent = get_agent(str(update.effective_user.id))
    try:
        agent.approve()
        await update.message.reply_text("Approved. Use /send to email the latest package.")
    except Exception as exc:
        await update.message.reply_text(str(exc))


async def send(update, context) -> None:
    agent = get_agent(str(update.effective_user.id))
    if not agent.state.email_draft:
        await update.message.reply_text("Please provide a recipient email in the /plan command.")
        return
    if not agent.state.approved:
        await update.message.reply_text("Please approve the latest preview with /approve before sending.")
        return
    try:
        warnings = await asyncio.to_thread(send_email, agent.state.email_draft)
        agent.state.last_send_status = "sent"
        message = "Email sent."
        if warnings:
            agent.state.last_send_status = "sent with warnings"
            message += "\n\nWarnings:\n" + "\n".join(f"- {warning}" for warning in warnings)
        await update.message.reply_text(message)
    except Exception as exc:
        agent.state.last_error = str(exc)
        agent.state.last_send_status = f"failed: {exc}"
        await update.message.reply_text(f"Email not sent: {exc}")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in the environment.")
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("research", research))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("trace", trace))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("send", send))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.run_polling()


if __name__ == "__main__":
    main()
