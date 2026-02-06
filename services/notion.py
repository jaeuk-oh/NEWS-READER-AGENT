import os
import re
import logging
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION  = "2022-06-28"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['NOTION_TOKEN']}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


# ---------------------------------------------------------------------------
# Rich-text inline parsing
# ---------------------------------------------------------------------------
# Splits a line into segments: bold (**...**), link ([text](url)), or plain text.
# Ordered: bold first, then link, then plain — so ** and [ are not consumed as plain.
_SEGMENT_RE = re.compile(
    r"\*\*(.+?)\*\*"              # group 1: bold inner text
    r"|\[([^\]]+)\]\(([^)]+)\)"   # group 2: link text, group 3: link url
    r"|([^*\[]+)"                 # group 4: plain text
)


def _rich_text_obj(content: str, bold: bool, url: str | None = None) -> dict:
    return {
        "type": "text",
        "text": {
            "content": content,
            "link": {"url": url} if url else None,
        },
        "annotations": {
            "bold": bold,
            "italic": False,
            "strikethrough": False,
            "underline": False,
            "code": False,
            "color": "default",
        },
    }


def _parse_rich_text(line: str) -> list[dict]:
    """Parse a markdown line into a Notion rich_text array."""
    segments: list[dict] = []
    for match in _SEGMENT_RE.finditer(line):
        bold_inner, link_text, link_url, plain = match.groups()

        if bold_inner is not None:
            segments.append(_rich_text_obj(content=bold_inner, bold=True))
        elif link_text is not None:
            segments.append(_rich_text_obj(content=link_text, bold=False, url=link_url))
        elif plain is not None:
            segments.append(_rich_text_obj(content=plain, bold=False))

    if not segments:
        segments.append(_rich_text_obj(content=line, bold=False))

    return segments


# ---------------------------------------------------------------------------
# Block builders
# ---------------------------------------------------------------------------

def _heading_block(level: int, text: str) -> dict:
    block_type = f"heading_{level}"
    return {
        "type": block_type,
        block_type: {
            "rich_text": _parse_rich_text(text),
            "color": "default",
            "is_toggleable": False,
        },
    }


def _paragraph_block(text: str) -> dict:
    return {
        "type": "paragraph",
        "paragraph": {
            "rich_text": _parse_rich_text(text),
            "color": "default",
        },
    }


def _bullet_block(text: str) -> dict:
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": _parse_rich_text(text),
            "color": "default",
        },
    }


def _divider_block() -> dict:
    return {"type": "divider", "divider": {}}


# ---------------------------------------------------------------------------
# Markdown → Notion blocks
# ---------------------------------------------------------------------------

def markdown_to_blocks(md: str) -> list[dict]:
    """Convert markdown to Notion block objects.

    Handles the patterns produced by the crew's final_report_assembly_task:
    H1, H2, H3 (with emoji), dividers, bullet lists, and paragraphs
    with inline bold and links.
    """
    blocks: list[dict] = []

    for line in md.split("\n"):
        stripped = line.rstrip()

        if not stripped.strip():
            continue

        if stripped.strip() == "---":
            blocks.append(_divider_block())
        elif stripped.startswith("### "):
            blocks.append(_heading_block(3, stripped[4:]))
        elif stripped.startswith("## "):
            blocks.append(_heading_block(2, stripped[3:]))
        elif stripped.startswith("# "):
            blocks.append(_heading_block(1, stripped[2:]))
        elif stripped.startswith("- "):
            blocks.append(_bullet_block(stripped[2:]))
        else:
            blocks.append(_paragraph_block(stripped))

    return blocks


# ---------------------------------------------------------------------------
# Notion API
# ---------------------------------------------------------------------------

def create_notion_page(topic: str, markdown_content: str) -> str:
    """Create a new Notion page under the configured parent page.

    Returns the URL of the newly created page.
    Raises requests.HTTPError on API failure.
    """
    parent_page_id = os.environ["NOTION_PARENT_PAGE_ID"]
    today = datetime.now().strftime("%Y-%m-%d")
    page_title = f"Daily News Briefing — {today} — {topic}"

    blocks = markdown_to_blocks(markdown_content)

    # Notion allows max 100 children in the create call.
    # Typical reports are ~50 blocks; overflow handled via append.
    payload = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": page_title}}]
            }
        },
        "children": blocks[:100],
    }

    resp = requests.post(f"{NOTION_API_BASE}/pages", json=payload, headers=_headers())
    resp.raise_for_status()
    page_id = resp.json()["id"]

    # Append any blocks beyond the 100 limit
    if len(blocks) > 100:
        _append_blocks(page_id, blocks[100:])

    page_id_no_dashes = page_id.replace("-", "")
    return f"https://www.notion.so/{page_id_no_dashes}"


def _append_blocks(page_id: str, blocks: list[dict]) -> None:
    for i in range(0, len(blocks), 100):
        resp = requests.patch(
            f"{NOTION_API_BASE}/blocks/{page_id}/children",
            json={"children": blocks[i:i + 100]},
            headers=_headers(),
        )
        resp.raise_for_status()
