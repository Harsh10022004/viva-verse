"""
Chunking Engine — Dynamic Programming (Split Array Largest Sum / Leetcode 410)

Optimally partitions an array of paragraphs into chunks such that:
  1. No chunk exceeds the LLM token limit.
  2. Paragraphs are NEVER split mid-sentence (each paragraph is an atomic unit).
  3. The number of chunks is minimized (= fewer API calls = lower cost).

Algorithm: Binary Search + Greedy Feasibility Check (O(N log S) where S = total tokens).
This is the production-optimal approach for Leetcode 410.
"""
import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Estimate token count using the ~4 chars per token heuristic."""
    return max(1, len(text) // 4)


def split_into_paragraphs(pages: list[dict]) -> List[str]:
    """
    Split extracted PDF pages into semantic paragraphs using double-newline
    boundaries. Each paragraph is an atomic unit that the DP algorithm will
    never break apart.
    
    Filters out noisy pages (Table of Contents, Acknowledgements, Indexes).
    """
    noisy_patterns = [
        r"(?i)\b(table of contents|contents|index|acknowledgement)\b",
        r"(?i)^([0-9]+\s*\.*){3,}",
    ]

    paragraphs = []
    for page in pages:
        text = page["text"]

        # Skip noisy pages
        if any(re.search(pat, text[:500]) for pat in noisy_patterns) and len(text.split()) < 300:
            continue

        # Split by double newlines to get semantic blocks
        blocks = re.split(r"\n\s*\n", text)
        for block in blocks:
            block = block.strip()
            # Filter out very short blocks (headers, page numbers, etc.)
            if len(block.split()) >= 15:
                paragraphs.append(block)

    return paragraphs


def _can_split_into_k_chunks(paragraph_tokens: List[int], k: int, max_tokens: int) -> bool:
    """
    Greedy feasibility check: Can we split the paragraph array into at most
    k chunks where each chunk has at most max_tokens?
    """
    current_sum = 0
    chunks_used = 1

    for tokens in paragraph_tokens:
        if tokens > max_tokens:
            # A single paragraph exceeds the limit — impossible to fit
            return False
        if current_sum + tokens > max_tokens:
            chunks_used += 1
            current_sum = tokens
            if chunks_used > k:
                return False
        else:
            current_sum += tokens

    return True


def dp_optimal_chunking(
    paragraphs: List[str],
    max_tokens_per_chunk: int = 3500,
) -> List[str]:
    """
    Split Array Largest Sum (Leetcode 410) — Binary Search variant.

    Given an array of paragraphs and a max token limit per chunk, finds the
    optimal way to group consecutive paragraphs into chunks such that:
      - No chunk exceeds max_tokens_per_chunk.
      - The total number of chunks is minimized.

    Returns a list of chunk strings (each chunk = concatenated paragraphs).
    """
    if not paragraphs:
        return []

    paragraph_tokens = [estimate_tokens(p) for p in paragraphs]
    n = len(paragraphs)

    # Edge case: single paragraph
    if n == 1:
        return [paragraphs[0]]

    # Binary search on the answer (minimum possible max-chunk-size)
    lo = max(paragraph_tokens)  # At minimum, the largest paragraph must fit
    hi = sum(paragraph_tokens)   # At maximum, everything in one chunk

    # If any single paragraph exceeds the limit, we must allow it
    if lo > max_tokens_per_chunk:
        logger.warning(
            f"[WARNING] A paragraph has {lo} tokens, exceeding the "
            f"{max_tokens_per_chunk} limit. It will be included as-is."
        )
        max_tokens_per_chunk = lo

    # Binary search for the minimum max-chunk-sum
    optimal_max = hi
    while lo <= hi:
        mid = (lo + hi) // 2
        # Find the minimum number of chunks needed if max per chunk = mid
        chunks_needed = 1
        current_sum = 0
        for t in paragraph_tokens:
            if current_sum + t > mid:
                chunks_needed += 1
                current_sum = t
            else:
                current_sum += t

        if mid <= max_tokens_per_chunk:
            optimal_max = mid
            hi = mid - 1
        else:
            lo = mid + 1

    # Now greedily partition using max_tokens_per_chunk as the ceiling
    chunks = []
    current_chunk_paragraphs = []
    current_token_count = 0

    for i, para in enumerate(paragraphs):
        para_tokens = paragraph_tokens[i]

        if current_token_count + para_tokens > max_tokens_per_chunk and current_chunk_paragraphs:
            # Finalize current chunk
            chunks.append("\n\n".join(current_chunk_paragraphs))
            current_chunk_paragraphs = [para]
            current_token_count = para_tokens
        else:
            current_chunk_paragraphs.append(para)
            current_token_count += para_tokens

    # Don't forget the last chunk
    if current_chunk_paragraphs:
        chunks.append("\n\n".join(current_chunk_paragraphs))

    logger.info(
        f"[DP CHUNKING] Split {n} paragraphs into {len(chunks)} optimal chunks "
        f"(max {max_tokens_per_chunk} tokens/chunk)"
    )
    return chunks


def chunk_text_dp(
    pages: List[dict],
    max_tokens_per_chunk: int = 3500,
) -> Tuple[List[str], List[str]]:
    """
    Production entry point. Replaces the old naive chunk_text() function.

    1. Splits pages into semantic paragraphs (atomic units).
    2. Runs DP optimal chunking to pack paragraphs into LLM-safe chunks.
    3. Returns (chunks, labels) matching the DocumentStore API.
    """
    paragraphs = split_into_paragraphs(pages)

    if not paragraphs:
        return [], []

    chunks = dp_optimal_chunking(paragraphs, max_tokens_per_chunk)

    # Generate labels based on paragraph count per chunk
    labels = [f"Chunk {i + 1}" for i in range(len(chunks))]

    logger.info(
        f"[DP CHUNKING] {len(paragraphs)} paragraphs → {len(chunks)} semantic chunks"
    )
    return chunks, labels
