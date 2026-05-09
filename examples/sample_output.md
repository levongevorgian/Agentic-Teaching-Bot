# Agentic Telegram Teaching Assistant

**Լսարան:** AUA NLP students  
**Տեւողություն:** 80 րոպե  
**Ելքային լեզու:** Armenian/English

## Սլայդների ամփոփում

- Սլայդ/էջ 1-ը ներկայացնում է անհատական homework-ի նպատակը՝ կառուցել Telegram bot, որը ընդունում է lecture slides, օգտագործում է local LLM, կատարում է slide understanding, web research եւ email delivery։
- Սլայդ/էջ 2-ը սահմանում է agent workflow-ի հիմնական քայլերը՝ slide ingestion, concept map, teaching plan, web research, revision եւ email confirmation։
- Սլայդ/էջ 3-ը նկարագրում է evaluation-ը, grading rubric-ը եւ bonus ideas-ը՝ Armenian/bilingual support, PDF կամ Markdown attachment, trace/dashboard եւ backend comparison։

## Հասկացությունների քարտեզ / Նախապայմաններ

- Հիմնական թեմաներ.
  - Telegram bot workflow
  - Local LLM backend
  - Slide parsing/retrieval
  - Web research
  - Preview and approval before email
- Հավանական նախապայմաններ.
  - Basic Python and Telegram bot commands
  - Environment variables and secrets handling
  - Introductory NLP/LLM concepts

## Ուսումնական նպատակներ

- Բացատրել Telegram bot, session state, orchestrator, tools եւ local LLM backend բաղադրիչների դերը։
- Կապել slide parser/retriever, web search, email sender եւ logging/status գործիքները ամբողջական agent workflow-ի հետ։
- Նախագծել preview-before-send workflow, որտեղ email-ը ուղարկվում է միայն explicit approval-ից հետո։
- Օգտագործել slide/page references՝ package-ի պնդումները grounding անելու համար։
- Նշել failure cases՝ bad file, missing email, failed web search կամ unavailable LLM, եւ առաջարկել graceful fallback։

## Ժամանակացույցով դասի պլան

| Ժամանակ | Բաժին | Գործողություն |
| --- | --- | --- |
| 0-8 րոպե | Մուտք եւ նախնական ստուգում | Հարցնել՝ ինչ խնդիրներ կարող են առաջանալ, եթե LLM app-ը ավտոմատ email ուղարկի առանց confirmation-ի։ |
| 8-24 րոպե | Architecture walkthrough | Քարտեզագրել flow-ը՝ Telegram Bot API -> Session State -> Agent Orchestrator -> Tools -> Local LLM։ |
| 24-52 րոպե | Tool design եւ grounding | Քննարկել slide parsing/retrieval, web search, email sending եւ status logging գործիքները՝ slide/page references-ներով։ |
| 52-72 րոպե | Լսարանային աշխատանք | Ուսանողները նախագծում են state transitions upload -> /plan -> preview -> /approve -> /send flow-ի համար։ |
| 72-80 րոպե | Ամփոփում եւ ստուգում | Վերադառնալ learning objectives-ին եւ տալ երկու exit question՝ approval gate-ի եւ failure handling-ի մասին։ |

## Լսարանային վարժություն

Ուսանողներին տվեք նոր lecture slides-ի սցենար եւ խնդրեք.

1. Նշել ինչ state fields են պետք `/status`, `/trace`, `/plan`, `/research`, `/approve` եւ `/send` command-ների համար։
2. Որոշել որ transitions-ը պետք է blocked լինեն, եթե slides կամ recipient email չկա։
3. Նշել որ output sections-ը պետք է ունենան slide/page grounding։
4. Առաջարկել մեկ failure case եւ դրա user-facing error message-ը։

Սպասվող քննարկումը պետք է շեշտի reliability-ը, no-secrets policy-ն, explicit approval-ը եւ local LLM/tool integration-ը։

## Օգտակար հղումներ

- [Stanford CS224N Natural Language Processing](https://web.stanford.edu/class/cs224n/) - Օգտակար reference է NLP lecture topics-ի եւ assignments-ի համար։
- [Hugging Face NLP Course](https://huggingface.co/learn/nlp-course/) - Օգնում է transformers, tokenizers եւ practical NLP workflows բացատրելու համար։
- [Speech and Language Processing](https://web.stanford.edu/~jurafsky/slp3/) - Լավ textbook source է NLP foundations եւ advanced topics grounding-ի համար։

## Հիմնավորման նշումներ

Սլայդների վրա հիմնված պնդումներ.

- Սլայդ/էջ 1. Homework-ը պահանջում է Telegram bot, local LLM backend, slide understanding, web research եւ email delivery։
- Սլայդ/էջ 2. Required workflow-ը ներառում է slide ingestion, concept map, timed teaching plan, web research, revision եւ professional email։
- Սլայդ/էջ 3. Evaluation-ը պահանջում է functional test, grounding check, failure test եւ latency note։

Վեբ աղբյուրներից ստացված աջակցությունը սահմանափակվում է վերեւում նշված URL-ներով։ Չհիմնավորված պնդումները պետք է ստուգել դասից առաջ։

## Attachment Note

Current bot version prepares:

- `teaching_package.md` encoded as UTF-8 Markdown
- `teaching_package.pdf` generated with ReportLab and an explicitly registered Unicode font for Armenian/non-Latin text

If Unicode PDF generation fails, the bot keeps the Markdown attachment and reports a clear warning instead of sending a broken question-mark PDF։

## Էլ. նամակի տեքստ

Թեմա. Դասավանդման փաթեթ՝ Agentic Telegram Teaching Assistant

Բարեւ,

Կից ուղարկում եմ ստեղծված դասավանդման փաթեթը Markdown եւ PDF ձեւաչափերով։ Այն ներառում է ուսումնական նպատակներ, ժամանակացույցով դասի պլան, լսարանային վարժություն, օգտակար աղբյուրներ եւ հիմնավորման նշումներ՝ սլայդների/էջերի հղումներով։

Հարգանքով,
Levon's Teaching Assistant Bot

English signature used by the bot when the output language is English:

Best,
Levon's Teaching Assistant Bot
