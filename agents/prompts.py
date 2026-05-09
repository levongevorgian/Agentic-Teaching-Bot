SYSTEM_PROMPT = """You are an NLP teaching assistant that prepares practical lecture plans.
Ground the plan in the slide excerpts. Mark unsupported web/resource claims clearly.
Return concise, polished Markdown that a lecturer can directly use.
If the requested language is Armenian or Armenian/English, write the package in that language mode."""

LESSON_PACKAGE_PROMPT = """Create a teaching package from these inputs.

Audience: {audience}
Duration: {duration_minutes} minutes
Output language: {language}

Slide summary:
{slide_summary}

Main concepts and prerequisites:
{concepts}

Retrieved slide evidence:
{evidence}

Web resources:
{resources}

The package must include:
- a clear Markdown H1 title
- audience and duration
- a concise "Concept Map / Prerequisites" section with key topics and likely prerequisites
- 4-6 measurable learning objectives tailored to the audience
- a clean slide summary as bullets, not one large paragraph
- a timed plan with realistic minute allocations that add up to the requested duration
- at least one concrete in-class exercise with expected discussion points
- recap/check for understanding
- useful links with one-line justifications
- grounding notes that identify slide/page references separately from web-based claims
- a short professional email body signed as "Levon's Teaching Assistant Bot"

Do not invent URLs. Use only the provided web resources."""

CONCEPT_PROMPT = """From the slide excerpts below, list the main concepts and likely prerequisites.
Keep the output compact and useful for lesson planning.

{evidence}"""

REVISION_PROMPT = """Review this draft teaching package for realism, clarity, grounding, and timing.
Return an improved final version in Markdown. Ensure the title is clean, the summary is scannable,
the "Concept Map / Prerequisites" section is concise, timings are realistic, links are not fabricated,
slide/page grounding is explicit, and any email body is signed as "Levon's Teaching Assistant Bot".

{draft}"""
