# Certification Support Center — RAPS RAC Workspace

A rough v1 of a member support product for healthcare and life sciences associations, running here as a workspace for the Regulatory Affairs Professionals Society (RAPS) and its RAC credential program. It is built from RAPS public documents and is not affiliated with or endorsed by RAPS.

## What the product does

- **Support Assistant.** Members ask questions and get answers drawn only from the connected sources, the 2026 RAC Candidate Guides, the RAPS published guides, and documents your team uploads. Every answer shows its source. Questions outside the sources are not guessed at. They become a support case for staff instead.
- **Knowledge Base with document upload.** Staff upload the documents members actually ask about. PDF and Word (.docx) files are read in the browser with text extracted and split into passages, and plain text files (.txt, .md, .csv, .json) are indexed the same way. Uploaded documents become answerable right away and are cited by name. Scanned PDFs with no selectable text and legacy .doc files are marked as not searchable.
- **Eligibility checker.** Applies the published RAC eligibility paths (Bachelor's + 3 years, Master's + 2 years, Doctorate + 1 year, no degree + 10 years) with the experience type rules, and shows the rule behind each verdict.
- **Support Cases.** A live queue of questions from the session plus an example inbox, with draft replies, headline numbers and an unanswered questions report for staff.
- **Coverage and Insights.** Twelve fixed questions run against the same answering engine, scored live for correct cited answers and correct refusals, so answer quality is measured rather than assumed.

Light mode is the default appearance, with a dark mode toggle in the header.

## Facts used

All credential facts come from the official 2026 RAC Candidate Guides. The exam is 120 multiple choice questions in 2.5 hours. Recertification requires 36 credits every three years. The 2026 application fee is $605 for RAPS members and $760 for nonmembers. An older RAPS web guide lists 100 questions, and the workspace flags that figure as outdated where it comes up.

## Run it

Open `index.html` in a browser, or serve the folder with any static host. It also works as is on GitHub Pages. In that static mode the assistant uses a built in deterministic matching engine over the guide content and the documents uploaded in the browser, with no model call.

## LLM mode

Run the small backend in `server/` and the same page switches to real LLM answers.

```bash
python3 server/server.py
```

Then open http://localhost:8787. The page posts each question to `/api/ask`. The server retrieves the most relevant chunks from `server/knowledge.json` (extracted from the same public guides) plus any documents the page has sent to `/api/upload`, and the LLM answers using only those chunks, with the sources returned alongside. Questions with no matching source, and requests to write application material, return a staff handoff without calling the model. If the model is unreachable, the server falls back to the top source chunk so the workspace still answers from source. Uploaded documents are held in server memory for the run and are not written to disk.

Providers are set with environment variables.

- `LLM_PROVIDER=ollama` (default) uses a local Ollama server, no API key. `LLM_MODEL` defaults to `llama3.2:3b`. This is the free, private way to run it.
- `LLM_PROVIDER=openai` uses any OpenAI compatible chat API. Set `LLM_API_KEY`, and optionally `LLM_BASE_URL` and `LLM_MODEL` (default `gpt-4o-mini`).

The API key, when used, lives only on the server. It is never sent to the browser.

## Why this exists

This is the first build of a focused product idea, an AI support workspace for healthcare and life sciences associations in the Washington DC area that handles certification, continuing education and guideline questions from an association's own documents, with citations, measured accuracy and a clean handoff to staff. The same workspace is designed to be re-pointed at another association's documents and test set.
