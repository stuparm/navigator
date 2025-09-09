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

MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
MD_ITAL = re.compile(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)")
MD_CODE = re.compile(r"`([^`]+)`")
HEADING1 = re.compile(r"^\s{0,6}#\s+(.*)$")
HEADING2 = re.compile(r"^\s{0,6}##\s+(.*)$")
HEADING3 = re.compile(r"^\s{0,6}###\s+(.*)$")
BULLET    = re.compile(r"^\s{0,6}[-*]\s+(.*)$")
SUBBULLET = re.compile(r"^\s{2,}[-*]\s+(.*)$")  # indented bullets -> children
NUMBERED  = re.compile(r"^\s{0,6}(\d+)(?:[.)-])\s+(.*)$")  # 1. / 1) / 1 -

def _rich(text: str) -> List[Dict[str, Any]]:
    """
    Convert a small subset of Markdown (**bold**, *italic*, `code`) into
    Notion rich_text spans, ensuring NO overlapping tokens.
    Precedence: code > bold > italic.
    """
    if not text:
        return [{"type": "text", "text": {"content": ""}}]

    # 1) Collect matches with precedence and avoid overlaps
    n = len(text)
    covered = [False] * n
    tokens = []  # (start, end, type, inner)

    def add_matches(pattern, typ):
        for m in pattern.finditer(text):
            s, e = m.span()
            # require all chars in the match range to be uncovered
            if any(covered[i] for i in range(s, e)):
                continue
            # mark covered (the delimiters are inside s..e, we still mark them to avoid overlaps)
            for i in range(s, e):
                covered[i] = True
            tokens.append((s, e, typ, m.group(1)))

    # precedence order
    add_matches(MD_CODE, "code")
    add_matches(MD_BOLD, "bold")
    add_matches(MD_ITAL, "italic")

    tokens.sort(key=lambda t: t[0])

    # 2) Emit spans (plain text between tokens + annotated token text)
    spans: List[Dict[str, Any]] = []
    pos = 0
    for s, e, typ, inner in tokens:
        if s > pos:
            spans.append({"type": "text", "text": {"content": text[pos:s]}})
        annot = {"bold": False, "italic": False, "code": False}
        if typ == "bold":
            annot["bold"] = True
        elif typ == "italic":
            annot["italic"] = True
        elif typ == "code":
            annot["code"] = True
        spans.append({
            "type": "text",
            "text": {"content": inner},
            "annotations": annot
        })
        pos = e
    if pos < n:
        spans.append({"type": "text", "text": {"content": text[pos:]}})

    return spans or [{"type": "text", "text": {"content": text}}]

def _extract_title(md: str, fallback: Optional[str] = None) -> str:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()[:200]
    # fallback to first non-empty line or provided fallback
    for line in md.splitlines():
        if line.strip():
            return line.strip()[:200]
    return (fallback or "Untitled")[:200]

def _flush_list(acc, kind, out):
    if not acc:
        return
    if kind == "bullet":
        for item in acc:
            out.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": _rich(item["text"]),
                    "children": item.get("children", [])
                }
            })
    elif kind == "number":
        for item in acc:
            out.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": _rich(item["text"]),
                    "children": item.get("children", [])
                }
            })
    acc.clear()

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
    lines = md_chunk.replace("\r\n", "\n").split("\n")

    acc_items: List[Dict[str, Any]] = []   # each: {"text": str, "children": [blocks]}
    acc_kind: Optional[str] = None         # "bullet" | "number" | None

    def end_any_list():
        nonlocal acc_items, acc_kind
        _flush_list(acc_items, acc_kind, blocks)
        acc_kind = None

    for raw in lines:
        line = raw.rstrip()

        # BLANK LINES:
        # If we're inside a list, ignore blanks so numbering/bullets continue.
        if line.strip() == "":
            if acc_kind in ("number", "bullet"):
                continue
            else:
                # outside a list: skip (don't emit empty paragraphs)
                continue

        # HEADINGS end any active list
        m = HEADING1.match(line)
        if m:
            end_any_list()
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": _rich(m.group(1).strip())}})
            continue
        m = HEADING2.match(line)
        if m:
            end_any_list()
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": _rich(m.group(1).strip())}})
            continue
        m = HEADING3.match(line)
        if m:
            end_any_list()
            blocks.append({"object": "block", "type": "heading_3",
                           "heading_3": {"rich_text": _rich(m.group(1).strip())}})
            continue

        # SUB-BULLETS: if currently in a list, attach as children of last item
        m = SUBBULLET.match(line)
        if m and acc_kind in ("number", "bullet") and acc_items:
            acc_items[-1].setdefault("children", []).append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _rich(m.group(1).strip())}
            })
            continue

        # TOP-LEVEL BULLETS
        m = BULLET.match(line)
        if m:
            if acc_kind not in (None, "bullet"):
                end_any_list()
            acc_kind = "bullet"
            acc_items.append({"text": m.group(1).strip(), "children": []})
            continue

        # NUMBERED ITEMS
        m = NUMBERED.match(line)
        if m:
            if acc_kind not in (None, "number"):
                end_any_list()
            acc_kind = "number"
            acc_items.append({"text": m.group(2).strip(), "children": []})
            continue

        # ANY OTHER PARAGRAPH:
        # If we're in a numbered/bulleted list, treat as CHILD of the last item.
        if acc_kind in ("number", "bullet") and acc_items:
            acc_items[-1].setdefault("children", []).append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rich(line.strip())}
            })
            continue

        # Otherwise, plain paragraph
        end_any_list()
        blocks.append({"object": "block", "type": "paragraph",
                       "paragraph": {"rich_text": _rich(line.strip())}})

    # flush any trailing list
    end_any_list()
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
