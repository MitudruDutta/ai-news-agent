# file: summarization_tool.py
"""Article text summarization utilities.

Primary approach: use gensim's TextRank summarizer if available.
Fallback: a lightweight frequency-based extractive summarizer requiring no external deps.

Public API:
- summarize_article_text(text: str, ratio: float = 0.2) -> str
"""
from __future__ import annotations

from typing import List
import re

# --- Attempt to import gensim summarizer (optional) -------------------------
try:  # gensim 4.x still exposes gensim.summarization but static analyzer may complain
    from gensim.summarization import summarize as gensim_summarize  # type: ignore
    _GENSIM_AVAILABLE = True
except Exception:  # pragma: no cover - environment variance
    gensim_summarize = None  # type: ignore
    _GENSIM_AVAILABLE = False

# --- Simple sentence splitter & fallback summarizer -------------------------
_SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[.!?])\s+')
_STOPWORDS = {
    'the','and','is','in','to','of','a','for','on','that','with','as','by','an','be','this','it','are','from',
    'at','or','we','was','will','its','their','has','have','can','our','not','more','they','which','about','into'
}

def _split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    sentences = _SENTENCE_SPLIT_REGEX.split(text)
    # Filter out extremely short fragments
    return [s.strip() for s in sentences if len(s.strip().split()) > 2]

def _frequency_based_summary(text: str, ratio: float) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return text
    # If desired sentences count is less than 2, just return first sentence
    target_sentences = max(1, int(len(sentences) * ratio))
    if target_sentences >= len(sentences):
        return text  # nothing to trim

    # Word frequency scoring (basic)
    word_freq: dict[str, int] = {}
    for s in sentences:
        for w in re.findall(r"[A-Za-z0-9']+", s.lower()):
            if w in _STOPWORDS or len(w) <= 2:
                continue
            word_freq[w] = word_freq.get(w, 0) + 1

    if not word_freq:  # fallback if all stopwords
        return " ".join(sentences[:target_sentences])

    # Normalize frequencies
    max_f = max(word_freq.values())
    for w in list(word_freq.keys()):
        word_freq[w] /= max_f

    sentence_scores: List[tuple[float, int, str]] = []
    for idx, s in enumerate(sentences):
        score = 0.0
        for w in re.findall(r"[A-Za-z0-9']+", s.lower()):
            score += word_freq.get(w, 0)
        sentence_scores.append((score, idx, s))

    # Sort by score desc, tie-break earlier sentences
    sentence_scores.sort(key=lambda x: (-x[0], x[1]))
    selected = sorted(sentence_scores[:target_sentences], key=lambda x: x[1])
    return " ".join(s for _, _, s in selected)

# --- Public API -------------------------------------------------------------

def summarize_article_text(text: str, ratio: float = 0.2) -> str:
    """Summarize article text.

    Args:
        text: Full article text (plain string).
        ratio: Approx fraction of sentences to retain (0 < ratio <= 1).

    Returns:
        Summarized text (string). Returns original text for very short inputs.
    """
    if not text or not isinstance(text, str):  # invalid input
        return ""

    words = text.split()
    if len(words) < 50:  # Too short to summarize meaningfully
        return text.strip()

    # Clamp ratio
    if ratio <= 0:
        ratio = 0.2
    if ratio > 1:
        ratio = 1.0

    # Try gensim first if available
    if callable(gensim_summarize):  # safer guard
        try:
            summary = gensim_summarize(text, ratio=ratio)
            if summary and summary.strip():
                return summary.strip()
        except Exception as e:  # pragma: no cover - external lib behavior variability
            print(f"Gensim summarization failed, falling back: {e}")

    # Fallback method
    try:
        return _frequency_based_summary(text, ratio).strip()
    except Exception as e:  # last resort: return original text
        print(f"Fallback summarization failed: {e}")
        return text.strip()

__all__ = ["summarize_article_text"]
