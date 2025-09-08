# transcriber.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# model="whisper-1"
def transcribe_file(filename: str, model: str = "gpt-4o-mini-transcribe") -> str:
    """
    Transcribes the given audio file using OpenAI. Returns the transcript text.
    """
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ OPENAI_API_KEY not found in environment (.env).")

    client = OpenAI(api_key=api_key)

    with open(filename, "rb") as f:
        resp = client.audio.transcriptions.create(model=model, file=f)

    # Some SDK versions return .text; others return the object directly as str.
    text = getattr(resp, "text", str(resp))
    return text

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py /path/to/audio.wav")
        raise SystemExit(1)
    print(transcribe_file(sys.argv[1]))
