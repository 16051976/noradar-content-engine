"""
HeyGen Avatar integration for noradar-content-engine.

Classes:
    HeyGenAvatar  - low-level async wrapper around HeyGen API v2
    AvatarPipeline - high-level sync helper with MD5-based caching

AUCUN import depuis src/ (sauf rich pour les logs).
Ne raise jamais : retourne None si erreur (fallback-friendly).
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

console = Console()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
HEYGEN_API_KEY: str = os.getenv("HEYGEN_API_KEY", "")
HEYGEN_AVATAR_ID: str = os.getenv("HEYGEN_AVATAR_ID", "")
API_BASE = "https://api.heygen.com"
UPLOAD_BASE = "https://upload.heygen.com"
POLL_INTERVAL = 5
POLL_TIMEOUT = 300
CACHE_DIR = Path("outputs/cache/avatar")


# ---------------------------------------------------------------------------
# HeyGenAvatar - async low-level client
# ---------------------------------------------------------------------------
class HeyGenAvatar:
    """Async wrapper for HeyGen API v2 avatar video generation."""

    def __init__(
        self,
        api_key: str = HEYGEN_API_KEY,
        avatar_id: str = HEYGEN_AVATAR_ID,
    ) -> None:
        self.api_key = api_key
        self.avatar_id = avatar_id

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self.api_key,
            "Accept": "application/json",
        }

    # ----- Upload -----
    async def upload_audio(
        self, client: httpx.AsyncClient, audio_path: Path
    ) -> Optional[str]:
        """Upload an audio file. Returns the audio asset id or None."""
        console.log(f"[cyan]Upload audio:[/] {audio_path.name}")
        try:
            audio_bytes = audio_path.read_bytes()
            resp = await client.post(
                f"{UPLOAD_BASE}/v1/asset",
                headers={
                    "X-Api-Key": self.api_key,
                    "Content-Type": "audio/mpeg",
                },
                content=audio_bytes,
                timeout=60,
            )
            if resp.status_code != 200:
                console.log(f"[red]Upload echoue ({resp.status_code}):[/] {resp.text}")
                return None
            data = resp.json()
            audio_id = data.get("data", {}).get("id") or data.get("data", {}).get("asset_id")
            console.log(f"[green]Audio uploade ->[/] {audio_id}")
            return audio_id
        except Exception as exc:
            console.log(f"[red]Upload exception:[/] {exc}")
            return None

    # ----- Generate -----
    async def generate_video(
        self,
        client: httpx.AsyncClient,
        audio_asset_id: str,
        bg_color: str = "#1a1a2e",
        width: int = 720,
        height: int = 1280,
    ) -> Optional[str]:
        """Request avatar video generation. Returns video_id or None."""
        console.log("[cyan]Lancement generation avatar video ...[/]")
        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": self.avatar_id,
                        "avatar_style": "normal",
                    },
                    "voice": {
                        "type": "audio",
                        "audio_asset_id": audio_asset_id,
                    },
                    "background": {
                        "type": "color",
                        "value": bg_color,
                    },
                }
            ],
            "dimension": {"width": width, "height": height},
        }
        try:
            resp = await client.post(
                f"{API_BASE}/v2/video/generate",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=payload,
                timeout=30,
            )
            if resp.status_code != 200:
                console.log(f"[red]Generation echouee ({resp.status_code}):[/] {resp.text}")
                return None
            data = resp.json()
            video_id = data.get("data", {}).get("video_id")
            console.log(f"[green]Video en generation ->[/] video_id={video_id}")
            return video_id
        except Exception as exc:
            console.log(f"[red]Generate exception:[/] {exc}")
            return None

    # ----- Poll -----
    async def poll_status(
        self, client: httpx.AsyncClient, video_id: str
    ) -> Optional[str]:
        """Poll until completed. Returns download URL or None."""
        console.log(f"[cyan]Poll statut toutes les {POLL_INTERVAL}s (timeout {POLL_TIMEOUT}s)[/]")
        start = time.monotonic()
        while time.monotonic() - start < POLL_TIMEOUT:
            try:
                resp = await client.get(
                    f"{API_BASE}/v1/video_status.get",
                    headers=self._headers(),
                    params={"video_id": video_id},
                    timeout=15,
                )
            except Exception as exc:
                console.log(f"[yellow]Poll exception:[/] {exc}")
                await asyncio.sleep(POLL_INTERVAL)
                continue

            if resp.status_code != 200:
                console.log(f"[yellow]Poll erreur ({resp.status_code})[/]")
                await asyncio.sleep(POLL_INTERVAL)
                continue

            data = resp.json().get("data", {})
            status = data.get("status", "unknown")
            elapsed = int(time.monotonic() - start)
            console.log(f"  [{elapsed}s] status = {status}")

            if status == "completed":
                url = data.get("video_url")
                console.log(f"[green]Video prete ->[/] {url}")
                return url
            if status == "failed":
                console.log(f"[red]HeyGen a echoue:[/] {data.get('error', '?')}")
                return None

            await asyncio.sleep(POLL_INTERVAL)

        console.log("[red]Timeout atteint, abandon.[/]")
        return None

    # ----- Download -----
    async def download_video(
        self, client: httpx.AsyncClient, url: str, dest: Path
    ) -> bool:
        """Download video to dest. Returns True on success."""
        console.log(f"[cyan]Telechargement ->[/] {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            resp = await client.get(url, timeout=120, follow_redirects=True)
            if resp.status_code != 200:
                console.log(f"[red]Download echoue ({resp.status_code})[/]")
                return False
            dest.write_bytes(resp.content)
            size_mb = len(resp.content) / (1024 * 1024)
            console.log(f"[green]Sauvegarde:[/] {dest} ({size_mb:.1f} MB)")
            return True
        except Exception as exc:
            console.log(f"[red]Download exception:[/] {exc}")
            return False

    # ----- Full pipeline (async) -----
    async def generate_clip(
        self, audio_path: Path, output_path: Path
    ) -> Optional[Path]:
        """Run the full upload -> generate -> poll -> download pipeline."""
        if not self.api_key or not self.avatar_id:
            console.log("[red]HEYGEN_API_KEY ou HEYGEN_AVATAR_ID manquant.[/]")
            return None

        async with httpx.AsyncClient() as client:
            audio_id = await self.upload_audio(client, audio_path)
            if not audio_id:
                return None

            video_id = await self.generate_video(client, audio_id)
            if not video_id:
                return None

            video_url = await self.poll_status(client, video_id)
            if not video_url:
                return None

            ok = await self.download_video(client, video_url, output_path)
            return output_path if ok else None


# ---------------------------------------------------------------------------
# AvatarPipeline - sync high-level helper with caching
# ---------------------------------------------------------------------------
class AvatarPipeline:
    """
    High-level synchronous wrapper.

    - MD5-based caching in outputs/cache/avatar/
    - Never raises; returns None on any error.
    """

    def __init__(
        self,
        api_key: str = HEYGEN_API_KEY,
        avatar_id: str = HEYGEN_AVATAR_ID,
        cache_dir: Path = CACHE_DIR,
    ) -> None:
        self.heygen = HeyGenAvatar(api_key=api_key, avatar_id=avatar_id)
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _text_hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _cache_path(self, text: str) -> Path:
        return self.cache_dir / f"{self._text_hash(text)}.mp4"

    def generate_full_avatar_clip_sync(
        self,
        text: str,
        audio_path: Path | str,
        output_path: Path | str,
    ) -> Optional[Path]:
        """
        Generate an avatar clip synchronously.

        Args:
            text: Script text (used for cache key).
            audio_path: Path to the .mp3 audio file.
            output_path: Where to save the final .mp4.

        Returns:
            Path to the .mp4 on success, None on failure.
        """
        audio_path = Path(audio_path)
        output_path = Path(output_path)

        # --- Cache lookup ---
        cached = self._cache_path(text)
        if cached.exists():
            console.log(f"[green]Cache hit:[/] {cached}")
            # Copy cached file to requested output path
            if cached != output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(cached.read_bytes())
            return output_path

        # --- Validate inputs ---
        if not audio_path.exists():
            console.log(f"[red]Audio introuvable:[/] {audio_path}")
            return None

        # --- Generate ---
        try:
            result = asyncio.run(self.heygen.generate_clip(audio_path, output_path))
        except Exception as exc:
            console.log(f"[red]AvatarPipeline exception:[/] {exc}")
            return None

        if result is None:
            return None

        # --- Cache the result ---
        try:
            cached.parent.mkdir(parents=True, exist_ok=True)
            if cached != output_path:
                cached.write_bytes(output_path.read_bytes())
            console.log(f"[green]Mis en cache:[/] {cached}")
        except Exception as exc:
            console.log(f"[yellow]Cache write warning:[/] {exc}")

        return output_path
