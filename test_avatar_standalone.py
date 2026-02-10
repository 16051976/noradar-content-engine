#!/usr/bin/env python3
"""
Test standalone HeyGen Avatar API v2 - 100% isole, zero import depuis src/.
Charge .env, trouve le .mp3 le plus recent, genere un avatar video via HeyGen.
"""

import asyncio
import hashlib
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")
HEYGEN_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID", "")
AUDIO_DIR = Path("outputs/audio")
OUTPUT_PATH = Path("outputs/test_avatar_result.mp4")
POLL_INTERVAL = 5
POLL_TIMEOUT = 300
API_BASE = "https://api.heygen.com"
UPLOAD_BASE = "https://upload.heygen.com"


def _headers() -> dict[str, str]:
    return {
        "X-Api-Key": HEYGEN_API_KEY,
        "Accept": "application/json",
    }


def find_latest_mp3() -> Path | None:
    """Return the most recently modified .mp3 in AUDIO_DIR, or None."""
    if not AUDIO_DIR.exists():
        return None
    mp3s = sorted(AUDIO_DIR.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
    return mp3s[0] if mp3s else None


# ---------------------------------------------------------------------------
# HeyGen API v2 workflow
# ---------------------------------------------------------------------------
async def upload_audio(client: httpx.AsyncClient, audio_path: Path) -> str | None:
    """Upload audio file to HeyGen via raw binary POST. Returns the audio asset id."""
    print(f"\U0001f4e4 Upload audio: {audio_path.name} ...")
    audio_bytes = audio_path.read_bytes()
    resp = await client.post(
        f"{UPLOAD_BASE}/v1/asset",
        headers={
            "X-Api-Key": HEYGEN_API_KEY,
            "Content-Type": "audio/mpeg",
        },
        content=audio_bytes,
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"\u274c Upload echoue ({resp.status_code}): {resp.text}")
        return None
    data = resp.json()
    audio_id = data.get("data", {}).get("id") or data.get("data", {}).get("asset_id")
    print(f"\u2705 Audio uploade -> {audio_id}")
    return audio_id


async def generate_video(client: httpx.AsyncClient, audio_asset_id: str) -> str | None:
    """Request avatar video generation. Returns the video_id for polling."""
    print("\U0001f3ac Lancement generation avatar video ...")
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": HEYGEN_AVATAR_ID,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "audio",
                    "audio_asset_id": audio_asset_id,
                },
                "background": {
                    "type": "color",
                    "value": "#1a1a2e",
                },
            }
        ],
        "dimension": {"width": 720, "height": 1280},
    }
    resp = await client.post(
        f"{API_BASE}/v2/video/generate",
        headers={**_headers(), "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"\u274c Generation echouee ({resp.status_code}): {resp.text}")
        return None
    data = resp.json()
    video_id = data.get("data", {}).get("video_id")
    print(f"\u2705 Video en cours de generation -> video_id={video_id}")
    return video_id


async def poll_status(client: httpx.AsyncClient, video_id: str) -> str | None:
    """Poll video status every POLL_INTERVAL seconds. Returns download URL or None."""
    print(f"\u23f3 Poll statut toutes les {POLL_INTERVAL}s (timeout {POLL_TIMEOUT}s) ...")
    start = time.monotonic()
    while time.monotonic() - start < POLL_TIMEOUT:
        resp = await client.get(
            f"{API_BASE}/v1/video_status.get",
            headers=_headers(),
            params={"video_id": video_id},
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"\u26a0\ufe0f  Poll erreur ({resp.status_code}): {resp.text}")
            await asyncio.sleep(POLL_INTERVAL)
            continue

        data = resp.json().get("data", {})
        status = data.get("status", "unknown")
        elapsed = int(time.monotonic() - start)
        print(f"   [{elapsed}s] status = {status}")

        if status == "completed":
            url = data.get("video_url")
            print(f"\u2705 Video prete -> {url}")
            return url
        if status == "failed":
            print(f"\u274c HeyGen a echoue: {data.get('error', 'raison inconnue')}")
            return None

        await asyncio.sleep(POLL_INTERVAL)

    print("\u274c Timeout atteint, abandon.")
    return None


async def download_video(client: httpx.AsyncClient, url: str, dest: Path) -> bool:
    """Download the generated video to dest."""
    print(f"\u2b07\ufe0f  Telechargement -> {dest} ...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = await client.get(url, timeout=120, follow_redirects=True)
    if resp.status_code != 200:
        print(f"\u274c Telechargement echoue ({resp.status_code})")
        return False
    dest.write_bytes(resp.content)
    size_mb = len(resp.content) / (1024 * 1024)
    print(f"\u2705 Sauvegarde: {dest} ({size_mb:.1f} MB)")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    # --- Pre-checks ---
    if not HEYGEN_API_KEY:
        print("\u274c HEYGEN_API_KEY manquant dans .env")
        print("   Ajoute: HEYGEN_API_KEY=ton_api_key")
        sys.exit(1)
    if not HEYGEN_AVATAR_ID:
        print("\u274c HEYGEN_AVATAR_ID manquant dans .env")
        print("   Ajoute: HEYGEN_AVATAR_ID=ton_avatar_id")
        sys.exit(1)

    audio_path = find_latest_mp3()
    if audio_path is None:
        print("\u274c Aucun fichier .mp3 trouve dans outputs/audio/")
        print("   Lance d'abord: content-engine produce --format tuto --no-upload")
        sys.exit(1)

    print(f"\U0001f3b5 Audio selectionne: {audio_path}")
    print(f"\U0001f916 Avatar ID: {HEYGEN_AVATAR_ID}")
    print("-" * 50)

    async with httpx.AsyncClient() as client:
        # Step 1: upload audio
        audio_asset_id = await upload_audio(client, audio_path)
        if not audio_asset_id:
            sys.exit(1)

        # Step 2: generate video
        video_id = await generate_video(client, audio_asset_id)
        if not video_id:
            sys.exit(1)

        # Step 3: poll until ready
        video_url = await poll_status(client, video_id)
        if not video_url:
            sys.exit(1)

        # Step 4: download
        ok = await download_video(client, video_url, OUTPUT_PATH)
        if not ok:
            sys.exit(1)

    print("-" * 50)
    print(f"\U0001f389 Termine ! Video avatar -> {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
