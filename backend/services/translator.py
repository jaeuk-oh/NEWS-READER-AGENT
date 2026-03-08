"""Translate markdown reports from English to Korean.

Uses deep-translator (GoogleTranslator) — free, no API key, no cost.
Preserves markdown structure (headings, dividers, bullets, bold, links).
"""

import re
import logging

from deep_translator import GoogleTranslator

logger = logging.getLogger(__name__)

_CHUNK_LIMIT = 4500  # Stay safely under Google Translate's 5000-char limit

# Matches markdown links: [text](url)
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def _protect_urls(text: str) -> tuple[str, dict[str, str]]:
    """Replace URLs in markdown links with placeholders to prevent corruption."""
    urls: dict[str, str] = {}
    counter = 0

    def _replacer(match: re.Match) -> str:
        nonlocal counter
        placeholder = f"URLPLACEHOLDER{counter}"
        urls[placeholder] = match.group(2)
        counter += 1
        return f"[{match.group(1)}]({placeholder})"

    protected = _LINK_RE.sub(_replacer, text)
    return protected, urls


def _restore_urls(text: str, urls: dict[str, str]) -> str:
    """Restore original URLs from placeholders."""
    for placeholder, url in urls.items():
        text = text.replace(placeholder, url)
    return text


def _split_into_chunks(lines: list[str], limit: int) -> list[str]:
    """Group lines into chunks that stay under the character limit."""
    chunks: list[str] = []
    current_lines: list[str] = []
    current_size = 0

    for line in lines:
        line_size = len(line) + 1  # +1 for the newline separator
        if current_size + line_size > limit and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_size = 0
        current_lines.append(line)
        current_size += line_size

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


def translate_to_TargetLang(markdown: str, target_lang: str = "ko") -> str:
    """Translate a markdown report to the specified target language.

    Preserves markdown formatting by:
    1. Protecting URLs with placeholders before translation
    2. Splitting into chunks to respect character limits
    3. Restoring URLs after translation

    Falls back to the original text if translation fails entirely.
    """
    # Step 1: protect URLs from corruption
    protected, urls = _protect_urls(markdown)

    # Step 2: split into translatable chunks (line-boundary aware)
    lines = protected.split("\n")
    chunks = _split_into_chunks(lines, _CHUNK_LIMIT)

    # Step 3: translate each chunk
    translator = GoogleTranslator(source="auto", target=target_lang)
    translated_chunks: list[str] = []

    for i, chunk in enumerate(chunks):
        # Skip empty or whitespace-only chunks
        if not chunk.strip():
            translated_chunks.append(chunk)
            continue

        try:
            translated = translator.translate(chunk)
            if translated:
                translated_chunks.append(translated)
            else:
                logger.warning(f"Empty translation for chunk {i}, keeping original")
                translated_chunks.append(chunk)
        except Exception as e:
            logger.warning(f"Translation failed for chunk {i}: {e}. Keeping original.")
            translated_chunks.append(chunk)

    result = "\n".join(translated_chunks)

    # Step 4: restore original URLs
    result = _restore_urls(result, urls)

    logger.info(f"Report translated to '{target_lang}' successfully")
    return result
