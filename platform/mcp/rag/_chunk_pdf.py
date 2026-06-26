"""
PDF chunking for the RAG ingestion pipeline.

Strategy:
  1. Extract all pages with pypdf.
  2. Detect section headings: lines that start with "##" (planted by _create_sample_pdfs.py)
     OR lines shorter than 80 chars written in ALLCAPS.
  3. Split the document on headings, yielding one chunk per section.
  4. If a section body exceeds MAX_WORDS, split further into paragraph-sized
     sub-chunks with OVERLAP_WORDS of carry-over so retrieval stays coherent.
  5. Return a list of {"text": str, "metadata": dict} dicts.

Metadata per chunk:
  source_type:    "manual"
  document_name:  stem of the filename (e.g. "hydraulic_maintenance")
  section:        heading text (or "page_N" when no headings are found)
  page_start:     first page number the section appears on (1-indexed)
  chunk_index:    sequential chunk index within the document
"""

import re
from pathlib import Path

import pypdf

MAX_WORDS    = 300   # split sections larger than this
OVERLAP_WORDS = 40   # words carried over between sub-chunks


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("##"):
        return True
    # heuristic: short, ALL-CAPS line (ignoring punctuation/numbers)
    letters = re.sub(r"[^A-Za-z ]", "", stripped)
    if letters and letters == letters.upper() and 3 < len(stripped) < 80:
        return True
    return False


def _split_into_words(text: str) -> list[str]:
    return text.split()


def _sub_chunk(text: str, heading: str, meta_base: dict, start_index: int) -> list[dict]:
    """Break an oversized section body into overlapping sub-chunks."""
    words = _split_into_words(text)
    chunks = []
    i = 0
    sub = 0
    while i < len(words):
        window = words[i : i + MAX_WORDS]
        chunk_text = f"{heading}\n\n" + " ".join(window)
        chunks.append({
            "text":     chunk_text,
            "metadata": {**meta_base, "chunk_index": start_index + sub},
        })
        sub += 1
        i += MAX_WORDS - OVERLAP_WORDS
    return chunks


def chunk_pdf(pdf_path: Path) -> list[dict]:
    """
    Parse a PDF and return a list of text chunks with metadata.
    """
    reader = pypdf.PdfReader(str(pdf_path))
    document_name = pdf_path.stem

    # --- collect (page_number, line) pairs ---
    page_lines: list[tuple[int, str]] = []
    for page_num, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        for line in raw.splitlines():
            page_lines.append((page_num, line))

    # --- group by section heading ---
    sections: list[dict] = []   # {heading, page_start, body_lines}
    current: dict | None = None

    for page_num, line in page_lines:
        if _is_heading(line):
            if current is not None:
                sections.append(current)
            current = {
                "heading":    line.strip().lstrip("#").strip(),
                "page_start": page_num,
                "body_lines": [],
            }
        else:
            if current is None:
                # text before the first heading — treat as an unnamed intro section
                current = {
                    "heading":    f"page_{page_num}",
                    "page_start": page_num,
                    "body_lines": [],
                }
            current["body_lines"].append(line)

    if current is not None:
        sections.append(current)

    # --- build chunks ---
    chunks: list[dict] = []
    chunk_index = 0

    for sec in sections:
        body = " ".join(ln for ln in sec["body_lines"] if ln.strip())
        meta_base = {
            "source_type":   "manual",
            "document_name": document_name,
            "section":       sec["heading"],
            "page_start":    sec["page_start"],
        }

        words = _split_into_words(body)
        if len(words) <= MAX_WORDS:
            text = f"{sec['heading']}\n\n{body}" if body else sec["heading"]
            chunks.append({"text": text, "metadata": {**meta_base, "chunk_index": chunk_index}})
            chunk_index += 1
        else:
            sub = _sub_chunk(body, sec["heading"], meta_base, chunk_index)
            chunks.extend(sub)
            chunk_index += len(sub)

    return chunks
