# notion_push.py
import os
import re
import argparse
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from notion_client import Client as Notion

ICON_BY_TYPE = {
    "info": "ℹ️",
    "note": "🗒️",
    "warning": "⚠️",
    "tip": "💡",
    "success": "✅",
    "quote": "💬",
}

def _rich(text: str) -> List[Dict[str, Any]]:
    return [{"type": "text", "text": {"content": text}}]

def _extract_title(md: str, fallback: Optional[str] = None) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()[:200]
    # fallback to first non-empty line or provided fallback
    for line in md.splitlines():
        if line.strip():
            return line.strip()[:200]
    return (fallback or "Untitled")[:200]

def _split_callouts(md: str):
    """
    Yields ('callout', {'type':..., 'text':...}) or ('text', chunk)
    """
    parts = []
    pattern = re.compile(
        r"\[\[CALLOUT\s+type=(info|note|warning|tip|success|quote)\]\](.*?)\[\[\/CALLOUT\]\]",
        re.IGNORECASE | re.DOTALL
    )
    last = 0
    for m in pattern.finditer(md):
        if m.start() > last:
            parts.append(("text", md[last:m.start()]))
        ctype = m.group(1).lower()
        body = m.group(2).strip()
        parts.append(("callout", {"type": ctype, "text": body}))
        last = m.end()
    if last < len(md):
        parts.append(("text", md[last:]))
    return parts

def _md_lines_to_blocks(md_chunk: str) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []

    # Normalize Windows newlines
    lines = md_chunk.replace("\r\n", "\n").split("\n")

    for line in lines:
        if not line.strip():
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rich("")}
            })
            continue

        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": _rich(line[2:].strip())}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": _rich(line[3:].strip())}})
        elif line.startswith("### "):
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": _rich(line[4:].strip())}})
        elif re.match(r"^(\-|\*)\s+", line):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": _rich(re.sub(r'^(\-|\*)\s+', '', line))}})
        elif re.match(r"^\d+\.\s+", line):
            blocks.append({"object": "block", "type": "numbered_list_item",
                           "numbered_list_item": {"rich_text": _rich(re.sub(r'^\d+\.\s+', '', line))}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": _rich(line)}})
    return blocks

def md_to_notion_blocks(md: str) -> List[Dict[str, Any]]:
    """Convert Markdown (plus optional [[CALLOUT ...]] markers) to Notion blocks."""
    blocks: List[Dict[str, Any]] = []
    for kind, payload in _split_callouts(md):
        if kind == "text":
            blocks.extend(_md_lines_to_blocks(payload))
        else:
            ctype = payload["type"]
            icon = ICON_BY_TYPE.get(ctype, "💡")
            text = payload["text"]
            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": icon},
                    "rich_text": _rich(text)
                }
            })
    return blocks

def publish_markdown_to_notion(
    markdown: str,
    parent_page_id: str,
    title: Optional[str] = None,
    emoji_icon: Optional[str] = None
) -> str:
    """Create a Notion page under a parent page with the given markdown content."""
    load_dotenv()
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise RuntimeError("❌ NOTION_TOKEN not found in environment (.env).")
    notion = Notion(auth=token)

    page_title = title or _extract_title(markdown)
    children = md_to_notion_blocks(markdown)

    page_payload: Dict[str, Any] = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": page_title}}]}
        },
        "children": children
    }
    if emoji_icon:
        page_payload["icon"] = {"type": "emoji", "emoji": emoji_icon}

    page = notion.pages.create(**page_payload)
    return page["id"]

def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    parser = argparse.ArgumentParser(description="Publish a Markdown file to Notion under a parent page.")
    parser.add_argument("path", help="Path to Markdown file (e.g., adr.md)")
    parser.add_argument("--parent", help="Parent page ID (defaults to NOTION_PARENT_PAGE_ID env)")
    parser.add_argument("--title", help="Override page title")
    parser.add_argument("--emoji", help="Emoji icon for the page (e.g., 💡)")
    args = parser.parse_args()

    parent = args.parent or os.getenv("NOTION_PARENT_PAGE_ID")
    if not parent:
        raise RuntimeError("❌ Parent page ID not provided. Use --parent or set NOTION_PARENT_PAGE_ID in .env.")

    md = _read_file(args.path)
    page_id = publish_markdown_to_notion(md, parent_page_id=parent, title=args.title, emoji_icon=args.emoji)
    print(f"✅ Created Notion page: {page_id}")

if __name__ == "__main__":
    main()
