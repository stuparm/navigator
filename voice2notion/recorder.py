# recorder.py
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

DEFAULT_FILENAME = "tmp/input.wav"
DEFAULT_SAMPLERATE = 44100

def record_until_stop(filename: str = DEFAULT_FILENAME, samplerate: int = DEFAULT_SAMPLERATE) -> str:
    """
    Records from the default microphone until the user types 'stop' + Enter.
    Saves a mono WAV file and returns its path.
    """
    print("🎙️ Recording… type 'stop' and press Enter to finish.")
    buffer = []

    def callback(indata, frames, time, status):
        if status:
            print(status)
        buffer.append(indata.copy())

    stream = sd.InputStream(samplerate=samplerate, channels=1, callback=callback, dtype='int16')

    try:
        with stream:
            while True:
                command = input()
                if command.strip().lower() == "stop":
                    break
    except KeyboardInterrupt:
        print("\n⛔ Interrupted, stopping recording.")
    finally:
        pass

    if not buffer:
        raise RuntimeError("No audio captured. Try again.")

    audio = np.concatenate(buffer, axis=0)
    write(filename, samplerate, audio)
    print(f"✅ Saved recording to {filename}")
    return filename

if __name__ == "__main__":
    record_until_stop()
