import re


def chunk_text(text: str, max_chars: int = 500, overlap: int = 60) -> list[str]:
    """Split text into chunks on paragraph/sentence boundaries."""
    text = text.strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    sentences: list[str] = []
    for p in parts:
        sentences.extend(s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if s.strip())

    chunks: list[str] = []
    current = ""
    for s in sentences:
        while len(s) > max_chars:  # very long sentence: hard split
            if current:
                chunks.append(current)
                current = ""
            chunks.append(s[:max_chars])
            s = s[max_chars - overlap:]
        if len(current) + len(s) + 1 <= max_chars:
            current = f"{current} {s}".strip()
        else:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail} {s}".strip() if tail and len(tail) + len(s) < max_chars else s
    if current:
        chunks.append(current)
    return chunks
