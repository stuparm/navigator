# formatter_flow.py
import os
from datetime import date
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_MODEL = "gpt-4o-mini"   # use "gpt-4o" for higher quality
DEFAULT_TEMPERATURE = 0.2

SYSTEM_PROMPT = """You are a precise technical writer specializing in explaining information-flow diagrams.
Output STRICT Markdown suitable for Notion:
- Use # / ## / ### headings, bold, bullets, and numbered lists.
- No HTML. No tables unless clearly needed. Avoid code fences unless essential.
- Keep the requested section order exactly. If info is missing, write 'TBD' concisely.
- Extract clear *actors*, *systems*, *events*, and *data artifacts* from the transcript.
- Normalize spoken enumerations like "step one", "number one", "number 1", "1)" "one)", "(1)", "Step 1" into numbered lists (1., 2., 3., ...).
- Normalize spoken arrows like "A to B", "A arrow to B", "A -> B", "A leads to B" into concise flow lines.- If uncertain, write 'TBD'.
- Rephrase sentences to be professional. Every step has explanation and retrned text should look like a story.
"""

def _flow_user_prompt(
    transcript: str,
    diagram_title: Optional[str] = None,
    diagram_ref: Optional[str] = None,
) -> str:
    """Builds the user prompt. The diagram_ref is shown as a human reference only (local path)."""
    today = date.today().isoformat()
    title = diagram_title or "Information Flow"

    # Only show a clean reference line if the local file exists; otherwise mark TBD
    if diagram_ref and os.path.exists(diagram_ref):
        ref_line = f"**Diagram Reference (local):** {os.path.abspath(diagram_ref)}"
    elif diagram_ref:
        ref_line = f"**Diagram Reference (local):** {diagram_ref}  *(not found; verify path)*"
    else:
        ref_line = "**Diagram Reference:** TBD"

    return f"""
Convert the following raw dictation into a structured explanation of the information flow.

# Flow: {title}
**Date:** {today}  
{ref_line}  
**Status:** Draft

Sections to output in this exact order:
## 1. Overview
- One to three paragraphs describing the purpose of the flow and what is the transcript about.
## 2. Step-by-Step Flow
- Produce a numbered list (1., 2., 3., …) that captures the end-to-end sequence.
- Normalize spoken steps like "step one", "(1)", "1)" into "1." entries.
- For arrows described verbally (e.g., "Service A to Service B", "A arrow to B", "A -> B"), write each step as: **A → B:** action / data / condition.


Guidance:
- Produce a numbered sequence in **Step-by-Step Flow** (1., 2., 3., …).
- For directional statements ("A to B", "A -> B"), prefer: **A → B:** action/data/condition.
- Keep bullets short and specific. If info is missing, write 'TBD'.

RAW TRANSCRIPT:
---
{transcript}
---
"""

def format_markdown(
    transcript: str,
    diagram_title: Optional[str] = None,
    diagram_ref: Optional[str] = None,
    diagram_file: Optional[str] = None,  # kept for API compatibility; not used for upload
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
) -> str:
    """
    Convert transcript (+ optional local diagram reference) into structured Markdown.
    - IF included, diagram contains "Red Circles with Numbers" and these numbers match the values from input text.
    - This version does NOT attempt to upload or attach the image to OpenAI.
    - The diagram path is included in the document as a human reference only.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ OPENAI_API_KEY not found in environment (.env).")

    client = OpenAI(api_key=api_key)

    # Build messages (text-only). No image upload attempted.
    system_msg = {"role": "system", "content": SYSTEM_PROMPT}
    user_msg = {"role": "user", "content": _flow_user_prompt(transcript, diagram_title, diagram_ref or diagram_file)}

    resp = client.chat.completions.create(
        model=model,
        messages=[system_msg, user_msg],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()
