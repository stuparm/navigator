# Navigator

Navigator is a collection of small AI-driven agents ("navigators") for different workflows.
Each subproject is self-contained and manages its own virtual environment.

## Structure

- `voice2notion/` — Record voice input and turn it into structured docs (ADR, PRD, RFC, PR summaries).  
  Includes transcription, formatting, and optional publishing to Notion.  
- (future subprojects will live in their own folders)

## Setup

Each subproject has:
- its own `requirements.txt`  
- its own `.venv` virtual environment  
- its own `README.md` with usage details  

Example for `voice2notion`:

```bash
cd voice2notion
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
