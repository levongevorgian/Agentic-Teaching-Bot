from __future__ import annotations

import base64
import html
import re
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SlideChunk:
    page: int
    text: str


def parse_slides(path: str | Path) -> list[SlideChunk]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    if suffix == ".pptx":
        return _parse_pptx(path)
    if suffix in {".txt", ".md"}:
        return _parse_text(path)
    raise ValueError(f"Unsupported file type: {suffix or 'unknown'}")


def summarize(chunks: list[SlideChunk], max_chars: int = 900) -> str:
    if not chunks:
        return "No slide text could be extracted."
    joined = " ".join(chunk.text for chunk in chunks)
    joined = re.sub(r"\s+", " ", joined).strip()
    if len(joined) <= max_chars:
        return joined
    return joined[: max_chars - 3].rstrip() + "..."


def retrieve(chunks: list[SlideChunk], query: str, limit: int = 6) -> list[dict[str, str]]:
    query_terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_]+", query)}
    scored: list[tuple[int, SlideChunk]] = []
    for chunk in chunks:
        words = {term.lower() for term in re.findall(r"[A-Za-z0-9_]+", chunk.text)}
        score = len(query_terms & words)
        if score or len(scored) < limit:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (item[0], -item[1].page), reverse=True)
    return [
        {"page": str(chunk.page), "text": chunk.text}
        for score, chunk in scored[:limit]
        if chunk.text.strip()
    ]


def extract_concepts(chunks: list[SlideChunk], limit: int = 8) -> list[str]:
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "are", "was", "you",
        "your", "slide", "lecture", "about", "into", "using", "use", "can", "will",
    }
    counts: dict[str, int] = {}
    for chunk in chunks:
        for phrase in re.findall(r"\b[A-Z][A-Za-z0-9]*(?:\s+[A-Z][A-Za-z0-9]*){0,3}\b", chunk.text):
            key = phrase.strip()
            if len(key) > 2 and key.lower() not in stop:
                counts[key] = counts.get(key, 0) + 2
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{4,}", chunk.text.lower()):
            if word not in stop:
                counts[word] = counts.get(word, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    return [item[0] for item in ranked[:limit]]


def _parse_text(path: Path) -> list[SlideChunk]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    parts = re.split(r"\n\s*---+\s*\n|\f", text)
    return [SlideChunk(i + 1, _clean(part)) for i, part in enumerate(parts) if _clean(part)]


def _parse_pptx(path: Path) -> list[SlideChunk]:
    chunks: list[SlideChunk] = []
    with zipfile.ZipFile(path) as archive:
        slide_names = sorted(
            [name for name in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml", name)],
            key=lambda name: int(re.search(r"slide(\d+)\.xml", name).group(1)),
        )
        for name in slide_names:
            xml = archive.read(name).decode("utf-8", errors="ignore")
            texts = [html.unescape(item) for item in re.findall(r"<a:t>(.*?)</a:t>", xml)]
            page = int(re.search(r"slide(\d+)\.xml", name).group(1))
            text = _clean(" ".join(texts))
            if text:
                chunks.append(SlideChunk(page, text))
    return chunks


def _parse_pdf(path: Path) -> list[SlideChunk]:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        chunks = []
        for index, page in enumerate(reader.pages, start=1):
            text = _clean(page.extract_text() or "")
            if text:
                chunks.append(SlideChunk(index, text))
        if chunks:
            return chunks
    except Exception:
        pass
    return _parse_pdf_basic(path)


def _parse_pdf_basic(path: Path) -> list[SlideChunk]:
    data = path.read_bytes()
    chunks: list[SlideChunk] = []
    pos = 0
    page = 1
    while True:
        start = data.find(b"stream\n", pos)
        if start < 0:
            break
        body_start = start + len(b"stream\n")
        end = data.find(b"endstream", body_start)
        if end < 0:
            break
        raw = data[body_start:end].strip()
        text = _decode_pdf_stream(raw)
        if text:
            extracted = _extract_pdf_text_ops(text)
            if extracted:
                chunks.append(SlideChunk(page, extracted))
                page += 1
        pos = end + len(b"endstream")
    return chunks


def _decode_pdf_stream(raw: bytes) -> str:
    candidates = [raw]
    try:
        candidates.append(base64.a85decode(raw, adobe=True))
    except Exception:
        try:
            candidates.append(base64.a85decode(raw, adobe=False))
        except Exception:
            pass
    for candidate in candidates:
        try:
            return zlib.decompress(candidate).decode("latin1", errors="ignore")
        except Exception:
            continue
    return ""


def _extract_pdf_text_ops(stream_text: str) -> str:
    pieces = []
    for match in re.finditer(r"\((.*?)\)\s*Tj", stream_text, re.S):
        pieces.append(_unescape_pdf_string(match.group(1)))
    return _clean(" ".join(pieces))


def _unescape_pdf_string(value: str) -> str:
    value = value.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    value = re.sub(r"\\([nrtbf])", " ", value)
    value = re.sub(r"\\[0-7]{1,3}", " ", value)
    return value


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

