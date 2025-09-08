# main.py
import os
import importlib
from recorder import record_until_stop
from transcriber import transcribe_file
from publisher import publish_markdown_to_notion

AUDIO_FILE = "tmp/input.wav"
TRANSCRIPT_FILE = "tmp/transcript.txt"
OUTPUT_FILE = "tmp/output.md"

# Map user-friendly names to (module_name, function_name)
FORMATTERS = {
    "adr": ("formatter_adr", "format_markdown"),
    "pr":  ("formatter_pr",  "format_markdown"),
    "rfc": ("formatter_rfc", "format_markdown"),
    "prd": ("formatter_prd", "format_markdown"),
}

def wait_enter(prompt: str = "Press Enter to continue…"):
    try:
        input(prompt)
    except KeyboardInterrupt:
        print("\n⛔ Exiting.")
        raise SystemExit(0)

def choose_formatter() -> str:
    print("Choose document type to format:")
    for key in FORMATTERS.keys():
        print(f"  - {key}")
    while True:
        choice = input("Type one of [adr/pr/rfc/prd]: ").strip().lower()
        if choice in FORMATTERS:
            return choice
        print("Invalid choice. Please type one of [adr/pr/rfc/prd].")

def load_formatter(choice: str):
    module_name, func_name = FORMATTERS[choice]
    try:
        mod = importlib.import_module(module_name)
        fn = getattr(mod, func_name)
        return fn
    except Exception as e:
        raise RuntimeError(f"Failed to load formatter '{choice}' from {module_name}.{func_name}: {e}")

def main():
    print("=== Voice → Text → Formatter (control flow) ===\n")

    # Step 1: Recording
    wait_enter("Step 1/5: Ready to record. Press Enter to start (then type 'stop' to finish)… ")
    try:
        audio_path = record_until_stop(AUDIO_FILE)
    except Exception as e:
        print(f"❌ Recording failed: {e}")
        return

    # Step 2: Transcribe
    wait_enter("Step 2/5: Press Enter to transcribe with OpenAI… ")
    try:
        transcript = transcribe_file(audio_path)
    except Exception as e:
        print(f"❌ Transcription failed: {e}")
        return

    print("\n📝 Transcript (preview):\n")
    print(transcript[:1200] + ("\n…(truncated)…" if len(transcript) > 1200 else ""))
    print("\n— end of preview —\n")

    # Optional: save raw transcript
    choice = input(f"Save raw transcript to '{TRANSCRIPT_FILE}'? [Y/n]: ").strip().lower()
    if choice in ("", "y", "yes"):
        try:
            with open(TRANSCRIPT_FILE, "w", encoding="utf-8") as f:
                f.write(transcript)
            print(f"💾 Saved transcript to {TRANSCRIPT_FILE}")
        except Exception as e:
            print(f"❌ Could not save transcript: {e}")

    # Step 3: Select formatter
    wait_enter("Step 3/5: Press Enter to choose formatter… ")
    doc_type = choose_formatter()
    formatter = load_formatter(doc_type)

    # Optional context (e.g., project/repo name)
    project_hint = input("Enter project name/context (or leave blank): ").strip() or None

    # Step 4: Format with selected formatter
    try:
        output_md = formatter(transcript, project_name=project_hint)
    except Exception as e:
        print(f"❌ Formatting failed: {e}")
        return

    print(f"\n📄 {doc_type.upper()} Markdown (preview):\n")
    print(output_md[:2000] + ("\n…(truncated)…" if len(output_md) > 2000 else ""))
    print("\n— end of preview —\n")

    # Save formatted doc
    default_name = f"tmp/{doc_type}.md"
    filename = input(f"Step 4/5: Save formatted doc as [{default_name}]: ").strip() or default_name
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output_md)
        print(f"💾 Saved {doc_type.upper()} to {filename}")
    except Exception as e:
        print(f"❌ Could not save {doc_type.upper()}: {e}")


    # Step 5: Publish to notion
    parent = os.getenv("NOTION_PARENT_PAGE_ID")
    if not parent:
        print("❌ NOTION_PARENT_PAGE_ID missing in .env; skipping Notion publish.")
    else:
        push = input("Step 5/5: Publish to Notion? [Y/n]: ").strip().lower()
        if push in ("", "y", "yes"):
            page_id = publish_markdown_to_notion(output_md, parent_page_id=parent, title=filename.replace(".md",""), emoji_icon="💡")
            print(f"🔗 Notion page created: {page_id}")

    print("✅ Done.")

if __name__ == "__main__":
    main()
