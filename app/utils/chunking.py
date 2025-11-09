from typing import List, Tuple
import re

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
except Exception:
    _ENC = None


def count_tokens(text: str) -> int:
    if _ENC:
        return len(_ENC.encode(text))
    # fallback approximate token count
    return max(1, len(text) // 4)


def _encode(text: str) -> List[int]:
    if _ENC:
        return _ENC.encode(text)
    # very rough char->token fallback
    return [ord(c) % 256 for c in text]


def _decode(tokens: List[int]) -> str:
    if _ENC:
        return _ENC.decode(tokens)

    return "".join(chr(t) for t in tokens)

#chunksize=500, 50 token overlap
def chunk_fixed_tokens(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Tuple[str, int]]:
    toks = _encode(text)
    n = len(toks)
    chunks: List[Tuple[str, int]] = []
    i = 0
    while i < n:
        j = min(i + chunk_size, n)
        sub = toks[i:j]
        chunks.append((_decode(sub), len(sub)))
        if j == n:
            break
        i = max(0, j - overlap)
    return chunks


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

#split by sentences, overlap sentences=2
def chunk_semantic(text: str, max_tokens: int = 500, overlap_sentences: int = 2) -> List[Tuple[str, int]]:
    sentences = _SENT_SPLIT.split(text)
    chunks: List[Tuple[str, int]] = []
    curr: List[str] = []
    curr_tok = 0

    for sent in sentences:
        stoks = count_tokens(sent)
        if curr and curr_tok + stoks > max_tokens:
            chunk_text = " ".join(curr).strip()
            chunks.append((chunk_text, count_tokens(chunk_text)))
            # overlap: keep last N sentences
            curr = curr[-overlap_sentences:] if overlap_sentences > 0 else []
            curr_tok = count_tokens(" ".join(curr)) if curr else 0
        curr.append(sent)
        curr_tok += stoks

    if curr:
        chunk_text = " ".join(curr).strip()
        chunks.append((chunk_text, count_tokens(chunk_text)))
    return chunks