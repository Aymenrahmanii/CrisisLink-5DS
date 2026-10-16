"""Two chunking strategies for the CrisisLink protocol corpus.

Strategy A (fixed_index): recursive splitter on a fixed token window with overlap.
Strategy B (structured_index): Markdown-structure-aware; one chunk per section,
tables never cut in half, each chunk prefixed with its heading path.

Token counts use the all-MiniLM-L6-v2 tokenizer so both strategies are measured
in the unit the embedding model actually sees (its window is 256 tokens).
"""

import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "emergency_protocols.md"
TOKENIZER = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")

# Strategy A. The playbook suggested 300 tokens / 50 overlap, but all-MiniLM-L6-v2
# truncates input after 256 tokens, so a 300-token chunk would be silently cut.
FIXED_CHUNK_TOKENS = 200
FIXED_OVERLAP_TOKENS = 40

# Strategy B: sections longer than this are split between blocks (never inside a table row)
STRUCTURED_MAX_TOKENS = 240


def n_tokens(text: str) -> int:
    return len(TOKENIZER.encode(text, add_special_tokens=False))


def load_corpus() -> str:
    return CORPUS.read_text(encoding="utf-8")


def chunk_fixed(text: str) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        TOKENIZER,
        chunk_size=FIXED_CHUNK_TOKENS,
        chunk_overlap=FIXED_OVERLAP_TOKENS,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return [
        {"text": c, "metadata": {"strategy": "fixed", "chunk_index": i}}
        for i, c in enumerate(splitter.split_text(text))
    ]


def _sections(text: str) -> list[dict]:
    """Split on #, ## and ### headings, remembering the heading path."""
    sections, path, buf = [], {}, []
    current = None

    def flush():
        if current is not None:
            sections.append({**current, "body": "\n".join(buf).strip()})

    for line in text.splitlines():
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if m:
            flush()
            level, title = len(m.group(1)), m.group(2).strip()
            path = {k: v for k, v in path.items() if k < level}
            path[level] = title
            current = {"title": title, "path": " > ".join(path[k] for k in sorted(path))}
            buf = []
        else:
            buf.append(line)
    flush()
    return [s for s in sections if s["body"]]


def _blocks(body: str) -> list[str]:
    """Paragraphs, lists and whole tables as indivisible blocks."""
    blocks, cur, in_table = [], [], False
    for line in body.splitlines():
        is_row = line.lstrip().startswith("|")
        if (not line.strip()) or (is_row != in_table and cur):
            if cur:
                blocks.append("\n".join(cur))
            cur = [] if not line.strip() else [line]
            in_table = is_row if line.strip() else False
            continue
        cur.append(line)
        in_table = is_row
    if cur:
        blocks.append("\n".join(cur))
    return blocks


def _split_lines(block: str, header_prefix: str, limit: int, head_rows: int = 0) -> list[str]:
    """A block too big for one chunk: split between lines (table rows or list items).
    For tables, head_rows=2 repeats the header and separator rows in every piece."""
    rows = block.splitlines()
    head, body = rows[:head_rows], rows[head_rows:]
    pieces, cur = [], []
    for row in body:
        if cur and n_tokens(header_prefix + "\n".join(head + cur + [row])) > limit:
            pieces.append("\n".join(head + cur))
            cur = []
        cur.append(row)
    if cur:
        pieces.append("\n".join(head + cur))
    return pieces


def chunk_structured(text: str) -> list[dict]:
    chunks, parent = [], {"category": "reference", "source": ""}
    for sec in _sections(text):
        category = re.search(r"Category:\s*([a-z_]+)", sec["body"])
        source = re.search(r"Source:\s*(.+?)\.\s*$", sec["body"], re.M)
        is_subsection = sec["path"].count(" > ") >= 2
        meta = {
            "strategy": "structured",
            "section": sec["title"],
            # ### subsections without their own Category line inherit the ## section's one
            "category": category.group(1) if category else (parent["category"] if is_subsection else "reference"),
            "source": source.group(1) if source else (parent["source"] if is_subsection else ""),
        }
        if not is_subsection:
            parent = {"category": meta["category"], "source": meta["source"]}
        prefix = sec["path"] + "\n\n"
        if n_tokens(prefix + sec["body"]) <= STRUCTURED_MAX_TOKENS:
            chunks.append({"text": prefix + sec["body"], "metadata": meta})
            continue
        cur = []
        for block in _blocks(sec["body"]):
            candidate = prefix + "\n\n".join(cur + [block])
            if n_tokens(candidate) <= STRUCTURED_MAX_TOKENS:
                cur.append(block)
                continue
            if cur:
                chunks.append({"text": prefix + "\n\n".join(cur), "metadata": meta})
                cur = []
            if n_tokens(prefix + block) > STRUCTURED_MAX_TOKENS:
                head_rows = 2 if block.lstrip().startswith("|") else 0
                for piece in _split_lines(block, prefix, STRUCTURED_MAX_TOKENS, head_rows):
                    chunks.append({"text": prefix + piece, "metadata": meta})
            else:
                cur = [block]
        if cur:
            chunks.append({"text": prefix + "\n\n".join(cur), "metadata": meta})
    for i, c in enumerate(chunks):
        c["metadata"]["chunk_index"] = i
    return chunks


if __name__ == "__main__":
    corpus = load_corpus()
    print(f"corpus: {len(corpus)} chars, {n_tokens(corpus)} tokens")
    for name, fn in (("fixed", chunk_fixed), ("structured", chunk_structured)):
        chunks = fn(corpus)
        sizes = [n_tokens(c["text"]) for c in chunks]
        print(f"{name:10s} {len(chunks):3d} chunks, tokens min {min(sizes)} / avg {sum(sizes) // len(sizes)} / max {max(sizes)}")
