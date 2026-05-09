from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Iterable

from tools.email import SIGNATURE


class LLMError(RuntimeError):
    """Raised when the configured local LLM backend cannot complete a request."""


def _env(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def generate(
    messages: Iterable[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1800,
) -> str:
    """Call a vLLM/llama.cpp OpenAI-compatible chat-completions endpoint."""
    base_url = _env("LLM_BASE_URL", "http://localhost:8000/v1").rstrip("/")
    model = _env("LLM_MODEL", "local-model")
    api_key = _env("LLM_API_KEY", "local")
    timeout = float(_env("LLM_TIMEOUT_SECONDS", "90"))
    payload = {
        "model": model,
        "messages": list(messages),
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LLMError(f"Local LLM request failed: {exc}") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected LLM response shape: {data}") from exc


def fallback_generate_package(
    *,
    title: str,
    audience: str,
    duration_minutes: int,
    language: str,
    slide_summary: str,
    concepts: list[str],
    resources: list[dict[str, str]],
    evidence: list[dict[str, str]],
) -> str:
    """Deterministic offline package used when the local server is unavailable."""
    objectives = _learning_objectives(concepts)
    warmup, intro, guided, exercise, recap = _time_blocks(duration_minutes)
    objective_lines = "\n".join(f"- {objective}" for objective in objectives)
    concept_map = _concept_map(concepts)
    summary_lines = "\n".join(f"- {_trim(item['text'], 180)} (slide/page {item['page']})" for item in evidence[:5])
    if _is_armenian(language):
        links = _armenian_links(resources)
        evidence_notes = "\n".join(
            f"- Սլայդ/էջ {item['page']}: {_trim(item['text'], 220)}" for item in evidence[:6]
        )
        summary_lines = "\n".join(
            f"- {_trim(item['text'], 180)} (սլայդ/էջ {item['page']})" for item in evidence[:5]
        )
        return _fallback_generate_armenian(
            title=title,
            audience=audience,
            duration_minutes=duration_minutes,
            language=language,
            summary_lines=summary_lines,
            concept_map=concept_map,
            objectives=objectives,
            time_blocks=(warmup, intro, guided, exercise, recap),
            links=links,
            evidence_notes=evidence_notes,
        )
    links = "\n".join(
        f"- [{item['title']}]({item['url']}) - {item['snippet']}" for item in resources
    ) or "- No external resources were available; rerun `/research` before teaching."
    evidence_notes = "\n".join(
        f"- Slide/page {item['page']}: {_trim(item['text'], 220)}" for item in evidence[:6]
    )
    return f"""# {title}

**Audience:** {audience}  
**Duration:** {duration_minutes} minutes  
**Output language:** {language}

## Slide Summary
{summary_lines or _trim(slide_summary, 700)}

## Concept Map / Prerequisites
{concept_map}

## Learning Objectives
{objective_lines}

## Timed Teaching Plan
| Time | Segment | Activity |
| --- | --- | --- |
| 0-{warmup} min | Warm-up and diagnostic | Ask one prerequisite question and collect two learner assumptions on the board. |
| {warmup}-{warmup + intro} min | Concept framing | Introduce the central terms from the slides and connect them to a concrete example. |
| {warmup + intro}-{warmup + intro + guided} min | Guided explanation | Work through the slide evidence, highlighting definitions, workflow steps, and tradeoffs. |
| {warmup + intro + guided}-{warmup + intro + guided + exercise} min | In-class practice | Students solve the exercise below individually, then compare in pairs. |
| {duration_minutes - recap}-{duration_minutes} min | Recap and checks | Revisit objectives, resolve misconceptions, and ask two exit-check questions. |

## In-Class Exercise
Give learners a short scenario based on the slide topic. Ask them to:

1. Identify the two most relevant concepts from the lecture.
2. Choose an appropriate method or workflow step and justify the choice.
3. Name one likely failure mode or limitation.
4. Share one answer with a partner, then revise it after feedback.

Expected discussion points: correct use of terminology, evidence from the slides, and awareness of tradeoffs rather than a single memorized answer.

## Useful Links
{links}

## Grounding Notes
Slide-based claims:
{evidence_notes}

Web-based support is limited to the listed URLs above. Treat unsupported claims as suggestions to verify before lecture delivery.

## Email Body
Subject: Teaching package for {title}

Hello,

I prepared a {duration_minutes}-minute teaching package for {audience}. It includes learning objectives, a timed plan, an exercise, grounding notes from the slides, and supporting resources.

Best,
{SIGNATURE}
"""


def _fallback_generate_armenian(
    *,
    title: str,
    audience: str,
    duration_minutes: int,
    language: str,
    summary_lines: str,
    concept_map: str,
    objectives: list[str],
    time_blocks: tuple[int, int, int, int, int],
    links: str,
    evidence_notes: str,
) -> str:
    warmup, intro, guided, exercise, recap = time_blocks
    objective_lines = "\n".join(f"- {objective}" for objective in _armenian_objectives(objectives))
    return f"""# {title}

**Լսարան:** {audience}  
**Տեւողություն:** {duration_minutes} րոպե  
**Ելքային լեզու:** {language}

## Սլայդների ամփոփում
{summary_lines}

## Հասկացությունների քարտեզ / Նախապայմաններ
{_armenian_concept_map(concept_map)}

## Ուսումնական նպատակներ
{objective_lines}

## Ժամանակացույցով դասի պլան
| Ժամանակ | Բաժին | Գործողություն |
| --- | --- | --- |
| 0-{warmup} րոպե | Մուտք եւ նախնական ստուգում | Տվեք մեկ նախապայմանային հարց եւ գրատախտակին հավաքեք ուսանողների երկու ենթադրություն։ |
| {warmup}-{warmup + intro} րոպե | Հասկացությունների ձեւակերպում | Ներկայացրեք սլայդների հիմնական տերմինները եւ կապեք դրանք իրական օրինակների հետ։ |
| {warmup + intro}-{warmup + intro + guided} րոպե | Ուղղորդված բացատրություն | Քննարկեք սլայդների ապացույցները, սահմանումները, աշխատանքային քայլերը եւ փոխզիջումները։ |
| {warmup + intro + guided}-{warmup + intro + guided + exercise} րոպե | Լսարանային աշխատանք | Ուսանողները կատարում են ստորեւ տրված վարժությունը անհատապես, ապա համեմատում են զույգերով։ |
| {duration_minutes - recap}-{duration_minutes} րոպե | Ամփոփում եւ ստուգում | Վերադարձեք նպատակներին, պարզաբանեք թյուրըմբռնումները եւ տվեք երկու ելքային հարց։ |

## Լսարանային վարժություն
Ուսանողներին տվեք կարճ սցենար սլայդների թեմայի շուրջ եւ խնդրեք.

1. Նշել դասի երկու ամենակարեւոր հասկացությունները։
2. Ընտրել համապատասխան մեթոդ կամ աշխատանքային քայլ եւ հիմնավորել ընտրությունը։
3. Նշել մեկ հնարավոր սահմանափակում կամ սխալի աղբյուր։
4. Զույգով քննարկելուց հետո վերանայել պատասխանը։

Սպասվող քննարկումը պետք է շեշտի ճիշտ տերմինաբանությունը, սլայդներից բերված ապացույցները եւ մեթոդի սահմանափակումների գիտակցումը։

## Օգտակար հղումներ
{links}

## Հիմնավորման նշումներ
Սլայդների վրա հիմնված պնդումներ.
{evidence_notes}

Վեբ աղբյուրներից ստացված աջակցությունը սահմանափակվում է վերեւում նշված URL-ներով։ Չհիմնավորված պնդումները պետք է ստուգել դասից առաջ։

## Էլ. նամակի տեքստ
Թեմա. Դասավանդման փաթեթ՝ {title}

Բարեւ,

Պատրաստել եմ {duration_minutes} րոպեանոց դասավանդման փաթեթ {audience} լսարանի համար։ Այն ներառում է ուսումնական նպատակներ, ժամանակացույցով պլան, վարժություն, սլայդների վրա հիմնված նշումներ եւ լրացուցիչ աղբյուրներ։

Հարգանքով,
{SIGNATURE}
"""


def _learning_objectives(concepts: list[str]) -> list[str]:
    focus = concepts[:4] or ["the core lecture topic"]
    objectives = [
        f"Explain {focus[0]} using precise lecture terminology.",
        "Connect the main slide concepts to a realistic classroom example.",
        "Use slide evidence to justify a method, workflow, or design choice.",
        "Identify one limitation, tradeoff, or source of error in the topic.",
    ]
    if len(focus) > 1:
        objectives.append(f"Compare how {focus[0]} relates to {focus[1]}.")
    return objectives


def _concept_map(concepts: list[str]) -> str:
    key_topics = concepts[:5] or ["Core lecture topic"]
    prerequisites = concepts[5:8] or ["Basic terminology", "Lecture context"]
    key_topic_lines = "\n".join(f"  - {topic}" for topic in key_topics)
    prerequisite_lines = "\n".join(f"  - {item}" for item in prerequisites)
    return (
        "- Key topics:\n"
        f"{key_topic_lines}\n"
        "- Likely prerequisites:\n"
        f"{prerequisite_lines}"
    )


def _armenian_concept_map(concept_map: str) -> str:
    lines = concept_map.splitlines()
    translated: list[str] = []
    for line in lines:
        if line == "- Key topics:":
            translated.append("- Հիմնական թեմաներ.")
        elif line == "- Likely prerequisites:":
            translated.append("- Հավանական նախապայմաններ.")
        else:
            translated.append(line)
    return "\n".join(translated)


def _armenian_objectives(objectives: list[str]) -> list[str]:
    return [
        "Բացատրել դասի հիմնական հասկացությունները ճշգրիտ տերմինաբանությամբ։",
        "Կապել սլայդների գաղափարները իրական լսարանային օրինակի հետ։",
        "Օգտագործել սլայդներից ստացված ապացույցներ մեթոդը կամ աշխատանքային քայլը հիմնավորելու համար։",
        "Նշել թեմայի մեկ սահմանափակում, փոխզիջում կամ սխալի աղբյուր։",
        "Համեմատել հիմնական հասկացությունների կապերը եւ կիրառման պայմանները։",
    ][: max(4, min(5, len(objectives)))]


def _armenian_links(resources: list[dict[str, str]]) -> str:
    if not resources:
        return "- Արտաքին աղբյուրներ չեն գտնվել. դասից առաջ նորից գործարկեք `/research`։"
    return "\n".join(
        f"- [{item['title']}]({item['url']}) - Օգտակար է թեմայի լրացուցիչ բացատրությունների եւ օրինակների համար։"
        for item in resources
    )


def _is_armenian(language: str) -> bool:
    normalized = language.lower()
    return "armenian" in normalized or "հայ" in normalized


def _time_blocks(duration_minutes: int) -> tuple[int, int, int, int, int]:
    duration_minutes = max(5, duration_minutes)
    blocks = [
        max(1, round(duration_minutes * 0.10)),
        max(1, round(duration_minutes * 0.20)),
        max(1, round(duration_minutes * 0.35)),
        max(1, round(duration_minutes * 0.25)),
        max(1, round(duration_minutes * 0.10)),
    ]
    blocks[2] += duration_minutes - sum(blocks)
    while blocks[2] < 1:
        donor = max(range(len(blocks)), key=lambda index: blocks[index] if index != 2 else 0)
        blocks[donor] -= 1
        blocks[2] += 1
    return tuple(blocks)  # type: ignore[return-value]


def _trim(text: str, max_chars: int) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."
