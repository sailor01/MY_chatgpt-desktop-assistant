import sounddevice as sd
from scipy.io.wavfile import write
import whisper
import json
import os
from datetime import datetime

HISTORY_FILE = "history.json"
AUDIO_FILE = "input.wav"

def transcribe_audio():
    fs = 16000
    duration = 5
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    write(AUDIO_FILE, fs, recording)

    model = whisper.load_model("tiny")
    result = model.transcribe(AUDIO_FILE, language="zh")
    return result["text"]

def save_to_history(question, answer):
    record = {
        "time": datetime.now().isoformat(timespec='seconds'),
        "question": question,
        "answer": answer
    }
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []
    history.append(record)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []