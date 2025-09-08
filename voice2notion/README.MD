# voice2notion

Voice2Notion lets you dictate ideas and convert them into structured documents.  
It supports formatting into ADRs, PRDs, RFCs, and PR summaries, with optional publishing to Notion.

## Features

- Record audio from your microphone  
- Transcribe speech using OpenAI  
- Format transcript into Markdown (ADR, PRD, RFC, PR)  
- Save locally or publish to Notion  

## Setup

Create a virtual environment for this subproject and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```