# formatter.py
import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import date

DEFAULT_MODEL = "gpt-4o-mini"  # fast & cheap; swap to gpt-4o if you want extra quality

ADR_SYSTEM_PROMPT = """You are an expert architecture writer.
Output STRICT Markdown that is Notion-friendly (no HTML, no code fences unless explicitly needed).
Keep section headers exactly as specified. Do not invent extra sections. 
Use concise, clear language tailored to senior engineers & stakeholders.
"""

def _adr_user_prompt(transcript: str, project_name: str | None = None) -> str:
    today = date.today().isoformat()
    project = project_name or "Project"
    # Opinionated ADR skeleton:
    return f"""
Convert the following raw dictation into a clean ADR (Architecture Decision Record) in Markdown.

Rules:
- Use this exact section order and titles:
  # ADR: <short, imperative title>
  **Date:** {today}
  **Status:** Proposed
  **Project:** {project}

  ## Context
  ## Problem
  ## Options Considered
  ## Decision
  ## Consequences
  ## Risks & Trade-offs
  ## Alternatives Rejected
  ## Links & References
  ## TL;DR

- Keep it Notion-friendly:
  - Use headings (#, ##), bold, bullets, numbered lists.
  - Use short paragraphs and bullets for readability.
  - If the transcript includes explicit “callouts” or emphasis, convert them to clear bullets or short emphasized notes (e.g., **Note:** …, **Warning:** …).

- If any section is missing in the transcript, infer lightly or add a placeholder line (e.g., “TBD after spike”).

RAW TRANSCRIPT:
---
{transcript}
---
"""

def format_markdown(transcript: str, project_name: str | None = None, model: str = DEFAULT_MODEL) -> str:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ OPENAI_API_KEY not found in environment (.env).")

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": ADR_SYSTEM_PROMPT},
        {"role": "user", "content": _adr_user_prompt(transcript, project_name)},
    ]
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()
