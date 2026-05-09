from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from textwrap import wrap


SIGNATURE = "Levon's Teaching Assistant Bot"
FONT_ENV_VAR = "TEACHING_BOT_PDF_FONT_PATH"
FONT_NAME = "TeachingUnicode"


@dataclass
class Attachment:
    name: str
    content: bytes
    maintype: str
    subtype: str


@dataclass
class EmailDraft:
    recipient: str
    subject: str
    body: str
    attachments: list[Attachment]
    warnings: list[str]

    @property
    def attachment_name(self) -> str:
        return self.attachments[0].name if self.attachments else ""

    @property
    def attachment_text(self) -> str:
        for attachment in self.attachments:
            if attachment.subtype in {"markdown", "x-r-markdown", "plain"}:
                return attachment.content.decode("utf-8", errors="replace")
        return ""


def build_email(
    recipient: str,
    package_markdown: str,
    title: str,
    language: str = "English",
) -> EmailDraft:
    subject, body = _localized_email_text(title, language)
    attachments, warnings = create_package_attachments(package_markdown)
    return EmailDraft(
        recipient=recipient,
        subject=subject,
        body=body,
        attachments=attachments,
        warnings=warnings,
    )


def _localized_email_text(title: str, language: str) -> tuple[str, str]:
    normalized = language.lower()
    if "armenian" in normalized or "հայ" in normalized:
        subject = f"Դասավանդման փաթեթ. {title}"
        body = (
            "Բարեւ,\n\n"
            "Կից ուղարկում եմ ստեղծված դասավանդման փաթեթը Markdown եւ PDF ձեւաչափերով։ "
            "Այն ներառում է ժամանակացույցով դասի պլան, լսարանային վարժություն, օգտակար աղբյուրներ "
            "եւ հիմնավորման նշումներ՝ սլայդների/էջերի հղումներով։\n\n"
            f"Հարգանքով,\n{SIGNATURE}"
        )
        if "english" in normalized:
            body += (
                "\n\nHello,\n\nThe generated teaching package is attached in Markdown and PDF formats.\n\n"
                f"Best,\n{SIGNATURE}"
            )
        return subject, body

    return (
        f"Teaching package: {title}",
        "Hello,\n\n"
        "Attached is the generated teaching package in Markdown and PDF formats. "
        "It includes the timed plan, in-class exercise, supporting resources, and "
        "grounding notes with slide/page references.\n\n"
        f"Best,\n{SIGNATURE}",
    )


def create_package_attachments(package_markdown: str) -> tuple[list[Attachment], list[str]]:
    attachments = [
        Attachment(
            name="teaching_package.md",
            content=package_markdown.encode("utf-8"),
            maintype="text",
            subtype="markdown",
        )
    ]
    warnings: list[str] = []
    try:
        attachments.append(
            Attachment(
                name="teaching_package.pdf",
                content=markdown_to_simple_pdf(package_markdown),
                maintype="application",
                subtype="pdf",
            )
        )
    except Exception as exc:
        warnings.append(
            f"PDF generation failed; only the Markdown attachment is available: {exc}"
        )
    return attachments, warnings


def preview_email(draft: EmailDraft, max_chars: int = 1500) -> str:
    attachment_preview = draft.attachment_text[:max_chars]
    if len(draft.attachment_text) > max_chars:
        attachment_preview += "\n..."
    attachment_names = ", ".join(attachment.name for attachment in draft.attachments) or "none"
    warnings = ""
    if draft.warnings:
        warnings = "\n\nWarnings:\n" + "\n".join(f"- {warning}" for warning in draft.warnings)
    return (
        f"To: {draft.recipient}\n"
        f"Subject: {draft.subject}\n\n"
        f"{draft.body}\n\n"
        f"Attachments: {attachment_names}{warnings}\n\n"
        f"Markdown preview:\n{attachment_preview}"
    )


def send_email(draft: EmailDraft) -> list[str]:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    sender = os.getenv("SMTP_FROM", username).strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"

    missing = [
        name
        for name, value in {
            "SMTP_HOST": host,
            "SMTP_USERNAME": username,
            "SMTP_PASSWORD": password,
            "SMTP_FROM/SMTP_USERNAME": sender,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Email is not configured. Missing: {', '.join(missing)}")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = draft.recipient
    message["Subject"] = draft.subject
    message.set_content(draft.body)
    for attachment in draft.attachments:
        message.add_attachment(
            attachment.content,
            maintype=attachment.maintype,
            subtype=attachment.subtype,
            filename=attachment.name,
        )

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(username, password)
        smtp.send_message(message)
    return draft.warnings


def markdown_to_simple_pdf(markdown: str) -> bytes:
    try:
        return _markdown_to_reportlab_pdf(markdown)
    except Exception as exc:
        raise RuntimeError(
            "PDF generation requires ReportLab and a registered Unicode font with coverage "
            f"for the requested text. Set {FONT_ENV_VAR} or place a font in assets/fonts/."
        ) from exc


def _markdown_to_reportlab_pdf(markdown: str) -> bytes:
    from io import BytesIO

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page_width, page_height = letter
    margin = 0.7 * inch
    y = page_height - margin
    line_height = 13
    required_codepoints = _required_codepoints(markdown)
    font_name = _register_unicode_font(pdfmetrics, TTFont, required_codepoints)

    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Teaching Package")

    def new_page() -> None:
        nonlocal y
        pdf.showPage()
        pdf.setFont(font_name, 10)
        y = page_height - margin

    pdf.setFont(font_name, 10)
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            y -= line_height
            if y < margin:
                new_page()
            continue
        is_heading = line.startswith("#")
        line = line.lstrip("#").strip().replace("**", "").replace("__", "").replace("`", "")
        pdf.setFont(font_name, 14 if is_heading else 10)
        for wrapped in wrap(line, width=88) or [""]:
            if y < margin:
                new_page()
                pdf.setFont(font_name, 14 if is_heading else 10)
            pdf.drawString(margin, y, wrapped)
            y -= 18 if is_heading else line_height
        pdf.setFont(font_name, 10)

    pdf.save()
    return buffer.getvalue()


def _register_unicode_font(pdfmetrics, TTFont, required_codepoints: set[int]) -> str:
    for path, font_number in _font_candidates():
        if _font_supports_codepoints(path, required_codepoints, font_number):
            try:
                pdfmetrics.registerFont(
                    TTFont(FONT_NAME, str(path), subfontIndex=font_number)
                )
            except TypeError:
                try:
                    pdfmetrics.registerFont(TTFont(FONT_NAME, str(path)))
                except Exception:
                    continue
            except Exception:
                continue
            return FONT_NAME
    raise RuntimeError("No configured PDF font supports the required characters.")


def _font_candidates() -> list[tuple[Path, int]]:
    repo_root = Path(__file__).resolve().parents[1]
    configured = os.getenv(FONT_ENV_VAR, "").strip()
    candidates: list[tuple[Path, int]] = []
    if configured:
        candidates.append((Path(configured).expanduser(), 0))
    candidates.extend(
        [
            (repo_root / "assets" / "fonts" / "NotoSansArmenian-Regular.ttf", 0),
            (repo_root / "assets" / "fonts" / "NotoSans-Regular.ttf", 0),
            (repo_root / "assets" / "fonts" / "DejaVuSans.ttf", 0),
            (repo_root / "assets" / "fonts" / "Arial Unicode.ttf", 0),
            (Path("/System/Library/Fonts/NotoSansArmenian.ttc"), 0),
            (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"), 0),
            (Path("/Library/Fonts/Arial Unicode.ttf"), 0),
            (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), 0),
            (Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"), 0),
            (Path("/usr/local/share/fonts/dejavu/DejaVuSans.ttf"), 0),
            (Path("/usr/local/share/fonts/NotoSans-Regular.ttf"), 0),
        ]
    )
    return candidates


def _font_supports_codepoints(path: Path, codepoints: set[int], font_number: int = 0) -> bool:
    if not path.exists():
        return False
    if not codepoints:
        return True
    try:
        from fontTools.ttLib import TTFont as FontToolsTTFont

        font = FontToolsTTFont(str(path), fontNumber=font_number)
        supported: set[int] = set()
        for table in font["cmap"].tables:
            supported.update(table.cmap.keys())
        font.close()
        return codepoints.issubset(supported)
    except Exception:
        return False


def _required_codepoints(text: str) -> set[int]:
    return {ord(char) for char in text if ord(char) > 0x024F and not char.isspace()}

