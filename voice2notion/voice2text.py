import os
import sounddevice as sd
from scipy.io.wavfile import write
from openai import OpenAI
from dotenv import load_dotenv
import numpy as np

FILENAME = "tmp/input.wav"
SAMPLERATE = 44100

def record_until_stop():
    print("🎙️ Recording... type 'stop' and press Enter to finish.")

    # Start a raw recording buffer
    buffer = []

    def callback(indata, frames, time, status):
        if status:
            print(status)
        buffer.append(indata.copy())

    # Open a stream, keep filling the buffer until user types stop
    stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=callback, dtype='int16')
    with stream:
        while True:
            command = input()
            if command.strip().lower() == "stop":
                break

    # Concatenate buffer to numpy array
    audio = np.concatenate(buffer, axis=0)
    write(FILENAME, SAMPLERATE, audio)
    print(f"✅ Saved recording to {FILENAME}")
    return FILENAME

def transcribe(filename):
    load_dotenv()  # load .env file
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("❌ OPENAI_API_KEY not found. Add it to your .env file.")

    client = OpenAI(api_key=api_key)

    with open(filename, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",  # or "whisper-1"
            file=f
        )
    print("📝 Transcript:", transcript.text)


if __name__ == "__main__":
    file = record_until_stop()
    transcribe(file)