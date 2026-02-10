"""
Générateur de voix avec ElevenLabs API.
Alternative à Google Cloud TTS.
"""

from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console

from src.config import settings

console = Console()

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


class ElevenLabsGenerator:
    """Génère des fichiers audio via ElevenLabs API."""

    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.voice_id = settings.elevenlabs_voice_id

        if not self.api_key:
            console.print("[yellow]⚠ ELEVENLABS_API_KEY non configurée[/yellow]")
        if not self.voice_id:
            console.print("[yellow]⚠ ELEVENLABS_VOICE_ID non configuré[/yellow]")

    def generate(self, text: str, output_path: Path) -> Optional[Path]:
        """
        Génère un fichier MP3 via ElevenLabs.

        Args:
            text: Texte à convertir en audio
            output_path: Chemin de sortie du fichier MP3

        Returns:
            Path du fichier généré, ou None en cas d'erreur
        """
        if not self.api_key or not self.voice_id:
            console.print("[red]✗ ElevenLabs non configuré (clé API ou voice ID manquant)[/red]")
            return None

        url = f"{ELEVENLABS_API_URL}/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
        }

        console.print(f"[blue]Génération audio ElevenLabs (voice: {self.voice_id})...[/blue]")

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(url, headers=headers, json=body)
                response.raise_for_status()

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

            console.print(f"[green]✓ Audio ElevenLabs sauvegardé : {output_path}[/green]")
            return output_path

        except httpx.HTTPStatusError as e:
            console.print(f"[red]✗ ElevenLabs API erreur {e.response.status_code}: {e.response.text[:200]}[/red]")
            return None
        except httpx.RequestError as e:
            console.print(f"[red]✗ ElevenLabs connexion échouée: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]✗ ElevenLabs erreur inattendue: {e}[/red]")
            return None
