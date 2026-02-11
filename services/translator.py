"""
Google Translate integration without API keys.
Uses deep-translator library to translate final reports while preserving markdown structure.
"""

import re
import logging
from typing import Optional

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None
    logging.warning("deep-translator not installed. Translation features disabled.")


def translate_report(markdown_content: str, target_lang: str = 'ko', source_lang: str = 'en') -> str:
    """
    Translate markdown report while preserving structure.

    Args:
        markdown_content: The markdown text to translate
        target_lang: Target language code (default: 'ko' for Korean)
        source_lang: Source language code (default: 'en' for English)

    Returns:
        Translated markdown with preserved structure

    Raises:
        ImportError: If deep-translator is not installed
        Exception: If translation fails
    """
    if GoogleTranslator is None:
        raise ImportError(
            "deep-translator not installed. Run: uv add deep-translator"
        )

    translator = GoogleTranslator(source=source_lang, target=target_lang)

    lines = markdown_content.split('\n')
    translated_lines = []

    logging.info(f"Starting translation: {len(lines)} lines, {source_lang} → {target_lang}")

    for i, line in enumerate(lines):
        try:
            translated_line = _translate_line(line, translator)
            translated_lines.append(translated_line)

            # Progress logging every 50 lines
            if (i + 1) % 50 == 0:
                logging.info(f"Translated {i + 1}/{len(lines)} lines")

        except Exception as e:
            logging.warning(f"Failed to translate line {i + 1}: {e}")
            translated_lines.append(line)  # Fallback to original

    logging.info("Translation completed successfully")
    return '\n'.join(translated_lines)


def _translate_line(line: str, translator: GoogleTranslator) -> str:
    """
    Translate a single line while preserving markdown syntax.

    Handles:
    - Headings (# ## ###)
    - Bullet points (- )
    - Dividers (---)
    - Bold (**text**)
    - Links ([text](url))
    - Emojis (preserved as-is)
    """
    # Empty lines
    if not line.strip():
        return line

    # Dividers
    if line.strip() in ['---', '***', '___']:
        return line

    # Headings
    heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
    if heading_match:
        prefix = heading_match.group(1)
        text = heading_match.group(2)
        translated_text = _translate_text_with_inline_formatting(text, translator)
        return f"{prefix} {translated_text}"

    # Bullet points
    if line.startswith('- '):
        text = line[2:]
        translated_text = _translate_text_with_inline_formatting(text, translator)
        return f"- {translated_text}"

    # Regular paragraphs
    translated_text = _translate_text_with_inline_formatting(line, translator)
    return translated_text


def _translate_text_with_inline_formatting(text: str, translator: GoogleTranslator) -> str:
    """
    Translate text while preserving inline markdown (bold, links, emojis).

    Strategy:
    1. Extract links [text](url) → replace with placeholders
    2. Extract bold **text** → replace with placeholders
    3. Translate the placeholder-filled text
    4. Restore links and bold formatting
    """
    # Preserve emojis (already handled by deep-translator)

    # Extract and preserve links
    links = []
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    def link_replacer(match):
        link_text = match.group(1)
        link_url = match.group(2)
        placeholder_idx = len(links)
        links.append((link_text, link_url))
        return f"__LINK_{placeholder_idx}__"

    text_with_link_placeholders = link_pattern.sub(link_replacer, text)

    # Extract and preserve bold
    bold_texts = []
    bold_pattern = re.compile(r'\*\*([^*]+)\*\*')

    def bold_replacer(match):
        bold_text = match.group(1)
        placeholder_idx = len(bold_texts)
        bold_texts.append(bold_text)
        return f"__BOLD_{placeholder_idx}__"

    text_with_all_placeholders = bold_pattern.sub(bold_replacer, text_with_link_placeholders)

    # Translate text with placeholders
    # Handle Google Translate 5000 character limit
    if len(text_with_all_placeholders) > 4500:
        # For very long lines, split by sentences
        sentences = re.split(r'(?<=[.!?])\s+', text_with_all_placeholders)
        translated_sentences = []

        for sentence in sentences:
            if sentence.strip():
                try:
                    translated_sentences.append(translator.translate(sentence))
                except Exception as e:
                    logging.warning(f"Failed to translate sentence: {e}")
                    translated_sentences.append(sentence)

        translated_text = ' '.join(translated_sentences)
    else:
        try:
            translated_text = translator.translate(text_with_all_placeholders)
        except Exception as e:
            logging.warning(f"Translation failed, using original: {e}")
            translated_text = text_with_all_placeholders

    # Restore bold formatting
    for idx, bold_text in enumerate(bold_texts):
        placeholder = f"__BOLD_{idx}__"
        # Translate the bold text content
        try:
            translated_bold = translator.translate(bold_text)
        except:
            translated_bold = bold_text
        translated_text = translated_text.replace(placeholder, f"**{translated_bold}**")

    # Restore links (translate link text, preserve URL)
    for idx, (link_text, link_url) in enumerate(links):
        placeholder = f"__LINK_{idx}__"
        # Translate the link text
        try:
            translated_link_text = translator.translate(link_text)
        except:
            translated_link_text = link_text
        translated_text = translated_text.replace(placeholder, f"[{translated_link_text}]({link_url})")

    return translated_text


def translate_report_safe(markdown_content: str, target_lang: str = 'ko') -> Optional[str]:
    """
    Safe wrapper for translate_report that returns None on failure.

    Use this in production to gracefully handle translation failures.
    """
    try:
        return translate_report(markdown_content, target_lang=target_lang)
    except ImportError:
        logging.warning("Translation skipped: deep-translator not installed")
        return None
    except Exception as e:
        logging.error(f"Translation failed: {e}")
        return None
