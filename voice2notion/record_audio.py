import sounddevice as sd
from scipy.io.wavfile import write

def record_audio(duration=10, samplerate=44100):
    """
    Record audio from the default microphone.
    :param filename: Output file name
    :param duration: Recording length in seconds
    :param samplerate: Samples per second (Hz)
    """
    print(f"🎙️ Recording {duration} seconds of audio...")

    recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished

    write(filename, samplerate, recording)
    print(f"✅ Saved recording to {filename}")

if __name__ == "__main__":
    record_audio()
