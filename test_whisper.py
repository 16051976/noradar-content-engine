import whisper
import glob

model = whisper.load_model("medium")
audios = sorted(glob.glob("outputs/audio/*.mp3"))
audio_path = audios[-1]
print(f"Audio: {audio_path}")

result = model.transcribe(audio_path, language="fr", word_timestamps=True)

for seg in result["segments"][:3]:
    print(f"Segment {seg['id']} ({seg['start']:.2f}s - {seg['end']:.2f}s)")
    print(f"  Texte: {seg['text']}")
    if "words" in seg:
        for w in seg["words"][:5]:
            print(f"    {w['start']:.2f}s: {w['word']}")
    print()
