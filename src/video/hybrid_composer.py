"""
POC Hybrid Composer - Test rendu avatar + B-roll
NE MODIFIE AUCUN AUTRE FICHIER DU PROJET
"""

import random
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()

# --- Constants ---
WIDTH = 1080
HEIGHT = 1920
FPS = 30
CROSSFADE = 0.3

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AVATAR_PATH = PROJECT_ROOT / "outputs" / "test_avatar_result.mp4"
BROLL_DIR = PROJECT_ROOT / "assets" / "backgrounds"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "videos"
AUDIO_DIR = PROJECT_ROOT / "outputs" / "audio"

# Timeline : (nom, type, durée_secondes)
TIMELINE = [
    ("hook",     "text",   2),   # [0-2s]   Hook plein écran
    ("avatar_1", "avatar", 5),   # [2-7s]   Clip avatar
    ("broll_1",  "broll",  7),   # [7-14s]  B-roll
    ("stat",     "text",   4),   # [14-18s] Stat choc plein écran
    ("broll_2",  "broll",  7),   # [18-25s] B-roll
    ("avatar_2", "avatar", 5),   # [25-30s] Clip avatar
    ("cta",      "text",   3),   # [30-33s] CTA
]

TEXTS = {
    "hook": {
        "content": "Tu savais que ton proprio\npeut te devoir 10 000 EUR ?",
        "fontsize": 80,
    },
    "stat": {
        "content": "73%% des locataires\nne connaissent PAS\nleurs droits",
        "fontsize": 72,
    },
    "cta": {
        "content": "Lien en bio",
        "fontsize": 96,
    },
}


# ── Helpers ──────────────────────────────────────────────────────────


def _find_font() -> str:
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]:
        if Path(p).exists():
            return p
    return ""


def _find_latest_audio() -> Path | None:
    files = sorted(AUDIO_DIR.glob("*.mp3"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def _pick_broll(count: int = 2) -> list[Path]:
    files = list(BROLL_DIR.glob("*.mp4"))
    if not files:
        return []
    return random.sample(files, min(count, len(files)))


def _probe_duration(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def _run_ffmpeg(cmd: list[str], label: str):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg [{label}] echoue:\n{r.stderr[-800:]}")


# ── Segment builders ─────────────────────────────────────────────────


def _make_text_clip(
    name: str, duration: float, output: Path, tmp_dir: Path, font: str
):
    info = TEXTS[name]
    text_file = tmp_dir / f"{name}.txt"
    text_file.write_text(info["content"], encoding="utf-8")

    fontfile_opt = f":fontfile='{font}'" if font else ""

    vf = (
        f"drawtext=textfile='{text_file}'"
        f"{fontfile_opt}"
        f":fontsize={info['fontsize']}"
        f":fontcolor=white"
        f":x=(w-text_w)/2"
        f":y=(h-text_h)/2"
        f":line_spacing=24"
    )

    _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"color=c=black:s={WIDTH}x{HEIGHT}:d={duration}:r={FPS}",
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(output),
    ], f"text:{name}")


def _make_video_clip(
    source: Path, duration: float, start: float, output: Path,
    loop: bool = False,
):
    input_args: list[str] = []
    if loop:
        input_args.extend(["-stream_loop", "-1"])
    input_args.extend(["-ss", str(start), "-i", str(source)])

    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1"
    )

    _run_ffmpeg([
        "ffmpeg", "-y",
        *input_args,
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(output),
    ], f"clip:{source.name}")


# ── Assembly ─────────────────────────────────────────────────────────


def _assemble(
    clips: list[Path],
    durations: list[float],
    audio: Path | None,
    output: Path,
):
    n = len(clips)

    # Inputs
    inputs: list[str] = []
    for c in clips:
        inputs.extend(["-i", str(c)])
    if audio:
        inputs.extend(["-i", str(audio)])

    # xfade filter chain
    # offset_i = sum(durations[0:i]) - i * CROSSFADE
    filters: list[str] = []
    for i in range(1, n):
        offset = sum(durations[:i]) - i * CROSSFADE
        src_a = f"[xf{i - 1}]" if i > 1 else "[0:v]"
        src_b = f"[{i}:v]"
        out = f"[xf{i}]" if i < n - 1 else "[vout]"
        filters.append(
            f"{src_a}{src_b}xfade=transition=fade:duration={CROSSFADE}:offset={offset:.3f}{out}"
        )

    filter_complex = ";".join(filters)

    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex]

    if audio:
        cmd.extend(["-map", "[vout]", "-map", f"{n}:a"])
        cmd.extend(["-c:a", "aac", "-b:a", "192k", "-shortest"])
    else:
        cmd.extend(["-map", "[vout]", "-an"])

    cmd.extend([
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        str(output),
    ])

    _run_ffmpeg(cmd, "assemble")


# ── Entry point ──────────────────────────────────────────────────────


def create_hybrid_test():
    """Genere la video hybride POC avatar + B-roll."""

    console.print("[bold blue]POC Hybrid Composer[/bold blue]\n")

    # --- Verifications ---
    if not AVATAR_PATH.exists():
        console.print(
            "[red]❌ Avatar manquant. Lance d'abord : python test_avatar_standalone.py[/red]"
        )
        return

    audio = _find_latest_audio()
    if audio:
        console.print(f"[green]✓ Audio : {audio.name}[/green]")
    else:
        console.print("[yellow]⚠ Aucun audio — video muette[/yellow]")

    broll_files = _pick_broll(2)
    if not broll_files:
        console.print("[red]❌ Aucun B-roll dans assets/backgrounds/[/red]")
        return

    font = _find_font()
    avatar_dur = _probe_duration(AVATAR_PATH)

    console.print(f"[blue]Avatar : {avatar_dur:.1f}s[/blue]")
    console.print(f"[blue]B-roll : {', '.join(f.name for f in broll_files)}[/blue]")
    console.print()

    # --- Generation des segments ---
    with tempfile.TemporaryDirectory(prefix="hybrid_") as tmp_str:
        tmp = Path(tmp_str)
        clips: list[Path] = []
        durations: list[float] = []
        broll_idx = 0
        avatar_offset = 0.0

        for name, seg_type, dur in TIMELINE:
            clip = tmp / f"{name}.mp4"

            if seg_type == "text":
                _make_text_clip(name, dur, clip, tmp, font)
                console.print(f"  [green]✓[/green] {name} — texte {dur}s")

            elif seg_type == "avatar":
                need_loop = avatar_dur < dur
                start = 0.0 if need_loop else min(avatar_offset, max(0, avatar_dur - dur))
                _make_video_clip(AVATAR_PATH, dur, start, clip, loop=need_loop)
                avatar_offset = start + dur + 2
                console.print(f"  [green]✓[/green] {name} — avatar @{start:.1f}s {dur}s")

            elif seg_type == "broll":
                src = broll_files[broll_idx % len(broll_files)]
                broll_idx += 1
                src_dur = _probe_duration(src)
                need_loop = src_dur < dur
                if need_loop:
                    start = 0.0
                else:
                    start = random.uniform(0, max(0, src_dur - dur - 0.5))
                _make_video_clip(src, dur, start, clip, loop=need_loop)
                console.print(f"  [green]✓[/green] {name} — {src.name} @{start:.1f}s {dur}s")

            clips.append(clip)
            durations.append(float(dur))

        # --- Assemblage ---
        console.print("\n[blue]Assemblage xfade crossfade...[/blue]")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUTPUT_DIR / "hybrid_test.mp4"

        _assemble(clips, durations, audio, out)

    total = sum(d for _, _, d in TIMELINE) - CROSSFADE * (len(TIMELINE) - 1)
    console.print(f"\n[bold green]✓ Video hybride : {out}[/bold green]")
    console.print(f"[dim]Duree estimee : ~{total:.1f}s[/dim]")
