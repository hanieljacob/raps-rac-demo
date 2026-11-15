#!/usr/bin/env python3
"""LLM backend for the RAPS RAC demo.

Serves the static demo from the repo root and answers POST /api/ask by
retrieving the most relevant knowledge chunks (extracted from the public
RAPS RAC guides), then asking an LLM to answer using only those chunks.

Providers (set LLM_PROVIDER):
  ollama   - local Ollama server, no API key needed (default)
             LLM_MODEL defaults to llama3.2:3b, OLLAMA_HOST to localhost:11434
  openai   - any OpenAI-compatible chat API (OpenAI, Azure, Together, ...)
             needs LLM_API_KEY, optional LLM_BASE_URL and LLM_MODEL

If retrieval finds nothing, or the request asks the assistant to write
application material, the server returns a handoff without calling the LLM.
If the LLM call itself fails, it falls back to the top retrieved chunk text
so the demo still answers from source.

Run:  python3 server/server.py   (port 8787, override with PORT)
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge.json")
PORT = int(os.environ.get("PORT", "8787"))
PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
MODEL = os.environ.get("LLM_MODEL", "llama3.2:3b" if PROVIDER == "ollama" else "gpt-4o-mini")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.environ.get("LLM_API_KEY", "")

with open(KB_PATH, encoding="utf-8") as f:
    KB = json.load(f)

# Documents added through POST /api/upload during this server run.
UPLOADED = []

STOPWORDS = set(
    "the a an and or of to in for on with is are be by at from as it its this that "
    "these those you your we our they their will would can could should may might "
    "have has had not no yes if then than so such per via".split()
)


def chunk_document(name, text):
    """Split an uploaded document into searchable chunks in the KB shape."""
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for p in paragraphs:
        if len(buf) + len(p) + 1 > 1100 and buf:
            chunks.append(buf)
            buf = p
        else:
            buf = (buf + "\n\n" + p) if buf else p
    if buf:
        chunks.append(buf)
    entries = []
    for i, chunk in enumerate(chunks):
        words = [w for w in normalize(chunk).split() if len(w) >= 4 and w not in STOPWORDS]
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        keywords = [w for w, _ in sorted(freq.items(), key=lambda t: -t[1])[:14]]
        entries.append(
            {
                "id": f"upload-{len(UPLOADED) + len(entries) + 1}",
                "topic": name,
                "keywords": keywords,
                "text": chunk,
                "source": {"doc": name, "section": "Uploaded document", "url": ""},
            }
        )
    return entries


def add_document(name, text):
    entries = chunk_document(name, text)
    UPLOADED.extend(entries)
    return {"ok": True, "chunks_added": len(entries), "uploaded_chunks_total": len(UPLOADED)}

WRITE_FOR_ME = re.compile(
    r"write my|draft my|compose my|fill out my|"
    r"(write|draft|compose)[^.]{0,60}(statement|essay|cover letter|application)",
    re.IGNORECASE,
)


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def retrieve(question, top_n=3):
    q = " " + normalize(question) + " "
    scored = []
    for entry in KB + UPLOADED:
        score = 0
        for kw in entry["keywords"]:
            k = normalize(kw)
            if (" " + k + " ") in q or k in q:
                score += 3 if len(k.split()) >= 2 else 2
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda t: -t[0])
    return scored[:top_n]


SYSTEM_PROMPT = (
    "You are a member assistant for a professional association. Answer the "
    "member's question using ONLY the source passages provided. Do not use "
    "outside knowledge and do not guess. Keep the answer short, plain and "
    "complete, and include the key reason or rule from the passages behind "
    "the answer. Use the exact figures from the passages (numbers, fees, "
    "deadlines). If the passages do not answer the question, reply with "
    "exactly: NOT_IN_SOURCES"
)


def call_llm(question, chunks):
    context = "\n\n".join(
        f"[Source: {c['source']['doc']}, {c['source']['section']}]\n{c['text']}"
        for _, c in chunks
    )
    user = f"Source passages:\n{context}\n\nMember question: {question}"
    if PROVIDER == "ollama":
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        req = urllib.request.Request(
            OLLAMA_HOST + "/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        return data["message"]["content"].strip()
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        BASE_URL.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY,
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"].strip()


def answer(question):
    if WRITE_FOR_ME.search(question or ""):
        return {"outcome": "handoff", "reason": "write_for_member", "engine": "guardrail"}
    chunks = retrieve(question)
    if not chunks:
        return {"outcome": "handoff", "reason": "no_match", "engine": "retrieval"}
    sources = [
        {"doc": c["source"]["doc"], "section": c["source"]["section"], "url": c["source"]["url"]}
        for _, c in chunks
    ]
    try:
        text = call_llm(question, chunks)
    except Exception as e:  # LLM unavailable: answer from the top chunk verbatim
        top = chunks[0][1]
        return {
            "outcome": "answered",
            "answer": top["text"],
            "sources": sources[:1],
            "engine": "fallback-no-llm",
            "detail": str(e)[:200],
        }
    if text.strip() == "NOT_IN_SOURCES" or "NOT_IN_SOURCES" in text[:40]:
        return {"outcome": "handoff", "reason": "llm_no_source", "engine": "llm:" + MODEL}
    return {
        "outcome": "answered",
        "answer": text,
        "sources": sources,
        "engine": "llm:" + MODEL,
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_POST(self):
        if self.path not in ("/api/ask", "/api/upload"):
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/upload":
                result = add_document(str(body.get("name", "Uploaded document"))[:120], str(body.get("text", "")))
            else:
                result = answer(str(body.get("question", "")))
            status = 200
        except Exception as e:
            result, status = {"outcome": "handoff", "reason": "server_error", "detail": str(e)[:200]}, 500
        data = json.dumps(result).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"Serving {ROOT} on http://localhost:{PORT}  provider={PROVIDER} model={MODEL}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
