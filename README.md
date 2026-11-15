# RAPS RAC Demo

A working demo of an AI member assistant for a healthcare association, built on the public documents of the Regulatory Affairs Professionals Society (RAPS) and its RAC credential program.

This is a concept demo built from public sources. It is not affiliated with or endorsed by RAPS.

## What it shows

- **Member assistant.** Answers questions about the RAC credential only from the 2026 RAC Candidate Guides and RAPS published guides. Every answer shows the source document, section and link. Questions outside the documents get a refusal and a staff handoff summary instead of a guess.
- **Eligibility checker.** Applies the published RAC eligibility paths (Bachelor's + 3 years, Master's + 2 years, Doctorate + 1 year, no degree + 10 years) with the experience type rules, and shows the rule behind each verdict.
- **Staff view.** A live queue of questions from the session plus a labeled demo inbox, with draft replies, headline numbers and an unanswered questions report.
- **Test set.** Twelve fixed questions run against the same answering engine, scored live for correct cited answers and correct refusals.

## Facts used

All credential facts come from the official 2026 RAC Candidate Guides. The exam is 120 multiple choice questions in 2.5 hours. Recertification requires 36 credits every three years. The 2026 application fee is $605 for RAPS members and $760 for nonmembers. An older RAPS web guide lists 100 questions, and the demo flags that figure as outdated where it comes up.

## Run it

Open `index.html` in a browser, or serve the folder with any static host. It also works as is on GitHub Pages. In that static mode the assistant uses a built in deterministic matching engine over the guide content, with no model call.

## LLM mode

Run the small backend in `server/` and the same page switches to real LLM answers.

```bash
python3 server/server.py
```

Then open http://localhost:8787. The page posts each question to `/api/ask`. The server retrieves the most relevant chunks from `server/knowledge.json` (extracted from the same public guides), and the LLM answers using only those chunks, with the sources returned alongside. Questions with no matching source, and requests to write application material, return a staff handoff without calling the model. If the model is unreachable, the server falls back to the top source chunk so the demo still answers from source.

Providers are set with environment variables.

- `LLM_PROVIDER=ollama` (default) uses a local Ollama server, no API key. `LLM_MODEL` defaults to `llama3.2:3b`. This is the free, private way to run it.
- `LLM_PROVIDER=openai` uses any OpenAI compatible chat API. Set `LLM_API_KEY`, and optionally `LLM_BASE_URL` and `LLM_MODEL` (default `gpt-4o-mini`).

The API key, when used, lives only on the server. It is never sent to the browser.

## Why this exists

The demo is the first build of a focused product idea, an AI assistant for healthcare and life sciences associations in the Washington DC area that handles certification, continuing education and guideline questions from an association's own documents, with citations, measured accuracy and a clean handoff to staff. The same engine is designed to be re-pointed at another association's documents and test set.
