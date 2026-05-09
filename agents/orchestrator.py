from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import llm_backend
from agents import prompts
from tools.email import EmailDraft, build_email
from tools.slides import SlideChunk, extract_concepts, parse_slides, retrieve, summarize
from tools.web_search import resources_to_markdown, search_web


@dataclass
class AgentState:
    user_id: str
    slide_path: str | None = None
    chunks: list[SlideChunk] = field(default_factory=list)
    audience: str = "NLP students"
    duration_minutes: int = 80
    language: str = "English"
    recipient_email: str = ""
    title: str = "Generated Lecture Plan"
    resources: list[dict[str, str]] = field(default_factory=list)
    package_markdown: str = ""
    email_draft: EmailDraft | None = None
    approved: bool = False
    logs: list[str] = field(default_factory=list)
    last_error: str = ""
    last_send_status: str = "not sent"

    def log(self, message: str) -> None:
        self.logs.append(message)
        self.logs[:] = self.logs[-30:]


class TeachingAgent:
    def __init__(self, state: AgentState):
        self.state = state

    def ingest_slides(self, path: str | Path) -> str:
        self.state.slide_path = str(path)
        self.state.chunks = parse_slides(path)
        self.state.approved = False
        self.state.package_markdown = ""
        self.state.email_draft = None
        self.state.log(f"Parsed {len(self.state.chunks)} slide/page chunks from {Path(path).name}.")
        if not self.state.chunks:
            raise ValueError("No readable text found in the uploaded file.")
        concepts = extract_concepts(self.state.chunks, limit=4)
        if concepts:
            self.state.title = " / ".join(concepts[:2]).title()
        return summarize(self.state.chunks)

    def configure(
        self,
        *,
        audience: str | None = None,
        duration_minutes: int | None = None,
        language: str | None = None,
        recipient_email: str | None = None,
    ) -> None:
        if audience:
            self.state.audience = audience
        if duration_minutes:
            self.state.duration_minutes = duration_minutes
        if language:
            self.state.language = language
        if recipient_email:
            self.state.recipient_email = recipient_email
        self.state.log("Updated planning settings.")

    def research(self, topic: str | None = None) -> list[dict[str, str]]:
        topic = topic or self.state.title
        query = f"{topic} NLP lecture teaching resources"
        self.state.resources = search_web(query, limit=3)
        self.state.log(f"Collected {len(self.state.resources)} web resources for: {query}")
        return self.state.resources

    def build_package(self) -> str:
        if not self.state.chunks:
            raise ValueError("Upload slides before running the planning workflow.")
        if not self.state.resources:
            self.research()

        concepts = extract_concepts(self.state.chunks)
        evidence = retrieve(self.state.chunks, " ".join(concepts), limit=6)
        slide_summary = summarize(self.state.chunks)
        concept_text = ", ".join(concepts) if concepts else "No concepts extracted."
        resource_text = resources_to_markdown(self.state.resources)
        prompt = prompts.LESSON_PACKAGE_PROMPT.format(
            audience=self.state.audience,
            duration_minutes=self.state.duration_minutes,
            language=self.state.language,
            slide_summary=slide_summary,
            concepts=concept_text,
            evidence=_evidence_to_text(evidence),
            resources=resource_text,
        )
        try:
            draft = llm_backend.generate(
                [
                    {"role": "system", "content": prompts.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=2200,
            )
            final = llm_backend.generate(
                [
                    {"role": "system", "content": prompts.SYSTEM_PROMPT},
                    {"role": "user", "content": prompts.REVISION_PROMPT.format(draft=draft)},
                ],
                temperature=0.1,
                max_tokens=2200,
            )
            self.state.log("Generated package with local LLM backend.")
        except llm_backend.LLMError as exc:
            self.state.last_error = str(exc)
            final = llm_backend.fallback_generate_package(
                title=self.state.title,
                audience=self.state.audience,
                duration_minutes=self.state.duration_minutes,
                language=self.state.language,
                slide_summary=slide_summary,
                concepts=concepts,
                resources=self.state.resources,
                evidence=evidence,
            )
            self.state.log("Local LLM unavailable; generated deterministic fallback package.")

        self.state.package_markdown = final
        if self.state.recipient_email:
            self.state.email_draft = build_email(
                self.state.recipient_email,
                self.state.package_markdown,
                self.state.title,
                self.state.language,
            )
        else:
            self.state.email_draft = None
        self.state.approved = False
        return final

    def approve(self) -> None:
        if not self.state.package_markdown:
            raise ValueError("Generate a package before approval.")
        self.state.approved = True
        self.state.log("User approved the latest preview.")

    def status(self) -> str:
        return (
            f"Slides: {self.state.slide_path or 'not uploaded'}\n"
            f"Chunks: {len(self.state.chunks)}\n"
            f"Audience: {self.state.audience}\n"
            f"Duration: {self.state.duration_minutes} minutes\n"
            f"Language: {self.state.language}\n"
            f"Recipient: {self.state.recipient_email or 'not set'}\n"
            f"Resources: {len(self.state.resources)}\n"
            f"Package ready: {'yes' if self.state.package_markdown else 'no'}\n"
            f"Approved: {'yes' if self.state.approved else 'no'}\n"
            f"Last send status: {self.state.last_send_status}\n"
            f"Last error: {self.state.last_error or 'none'}\n"
            f"Recent logs:\n- " + "\n- ".join(self.state.logs[-6:])
        )

    def trace(self) -> str:
        package_preview = self.state.package_markdown[:900].strip()
        if not package_preview:
            package_preview = "No generated package yet."
        elif len(self.state.package_markdown) > 900:
            package_preview += "\n..."
        logs = "\n".join(f"- {item}" for item in self.state.logs[-10:]) or "- No trace logs yet."
        return (
            "Agent trace summary\n"
            f"Uploaded file: {self.state.slide_path or 'not uploaded'}\n"
            f"Chunks parsed: {len(self.state.chunks)}\n"
            f"Audience: {self.state.audience}\n"
            f"Duration: {self.state.duration_minutes} minutes\n"
            f"Language: {self.state.language}\n"
            f"Recipient: {self.state.recipient_email or 'not set'}\n"
            f"Resources: {len(self.state.resources)}\n"
            f"Package ready: {'yes' if self.state.package_markdown else 'no'}\n"
            f"Approved: {'yes' if self.state.approved else 'no'}\n"
            f"Last send status: {self.state.last_send_status}\n"
            f"Last error: {self.state.last_error or 'none'}\n\n"
            "Latest package preview:\n"
            f"{package_preview}\n\n"
            "Recent trace logs:\n"
            f"{logs}"
        )


def parse_plan_arguments(text: str) -> dict[str, str | int]:
    result: dict[str, str | int] = {}
    duration = re.search(r"(?:duration|minutes|min)\s*[:=]\s*(\d+)", text, re.I)
    if duration:
        result["duration_minutes"] = int(duration.group(1))
    email = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    if email:
        result["recipient_email"] = email.group(0)
    for key in ("audience", "language"):
        match = re.search(rf"{key}\s*[:=]\s*([^;,\n]+)", text, re.I)
        if match:
            result[key] = match.group(1).strip()
    return result


def _evidence_to_text(evidence: list[dict[str, str]]) -> str:
    return "\n".join(f"- Slide/page {item['page']}: {item['text']}" for item in evidence)
