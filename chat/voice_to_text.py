"""Turns a voice note into text, entirely on this laptop.

Uses Whisper, a speech-recognition model that runs offline. The first run
downloads the model (a few hundred megabytes); after that no internet is needed.

Run it:  uv run --with faster-whisper python chat/voice_to_text.py recording.webm
"""

import subprocess
import sys

import numpy
from faster_whisper import WhisperModel

MODEL_SIZE = "small"   # "base" is faster and less accurate, "medium" is slower and more accurate


def read_sound(file: str) -> numpy.ndarray:
    """Use ffmpeg to turn any recording into the plain sound format Whisper wants."""
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", file, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True,
    ).stdout
    return numpy.frombuffer(raw, dtype=numpy.float32)


def main() -> None:
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    pieces, _info = model.transcribe(read_sound(sys.argv[1]), vad_filter=True)
    print(" ".join(piece.text.strip() for piece in pieces))


if __name__ == "__main__":
    main()
