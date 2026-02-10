"""
Générateur de voix avec Google Cloud Text-to-Speech.
"""

from pathlib import Path
from typing import Optional
from google.cloud import texttospeech
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded
from rich.console import Console

from src.utils.retry import with_retry

from src.config import settings
from src.models import Script, AudioFile

console = Console()


# Voix françaises recommandées (du plus naturel au plus basique)
FRENCH_VOICES = {
    # Voix Wavenet (très naturelles)
    "wavenet_male": "fr-FR-Wavenet-B",
    "wavenet_female": "fr-FR-Wavenet-A",
    "wavenet_male_2": "fr-FR-Neural2-D",
    "wavenet_female_2": "fr-FR-Wavenet-C",
    # Voix Neural2 (très naturelles, plus récentes)
    "neural2_male": "fr-FR-Neural2-B",
    "neural2_female": "fr-FR-Neural2-A",
    "neural2_male_2": "fr-FR-Neural2-D",
    "neural2_female_2": "fr-FR-Neural2-C",
    # Voix Standard (moins naturelles mais moins chères)
    "standard_male": "fr-FR-Standard-B",
    "standard_female": "fr-FR-Standard-A",
}


class VoiceGenerator:
    """Génère des fichiers audio via Google Cloud TTS."""

    def __init__(self):
        # Le client utilise GOOGLE_APPLICATION_CREDENTIALS automatiquement
        self.client = texttospeech.TextToSpeechClient()
        self.default_voice = settings.tts_voice_name

    @with_retry(exceptions=(ResourceExhausted, ServiceUnavailable, DeadlineExceeded))
    def _synthesize(self, **kwargs):
        """Appel TTS avec retry automatique."""
        return self.client.synthesize_speech(**kwargs)

    def list_voices(self, language_code: str = "fr-FR") -> list[str]:
        """Liste les voix disponibles pour une langue."""
        response = self.client.list_voices(language_code=language_code)
        voices = []
        for voice in response.voices:
            if language_code in voice.language_codes:
                voices.append(
                    {
                        "name": voice.name,
                        "gender": texttospeech.SsmlVoiceGender(voice.ssml_gender).name,
                        "sample_rate": voice.natural_sample_rate_hertz,
                    }
                )
        return voices

    def generate(
        self,
        text: str,
        output_path: Optional[Path] = None,
        voice_name: Optional[str] = None,
        speaking_rate: Optional[float] = None,
        pitch: Optional[float] = None,
    ) -> tuple[bytes, float]:
        """
        Génère l'audio pour un texte donné.

        Args:
            text: Texte à convertir en audio
            output_path: Chemin de sortie optionnel
            voice_name: Nom de la voix (défaut: config)
            speaking_rate: Vitesse de parole (défaut: config)
            pitch: Pitch de la voix (défaut: config)

        Returns:
            Tuple (audio_bytes, duration_seconds)
        """
        voice_name = voice_name or self.default_voice
        speaking_rate = speaking_rate or settings.tts_speaking_rate
        pitch = pitch or settings.tts_pitch

        console.print(f"[blue]Génération audio avec {voice_name}...[/blue]")

        # Configuration de la synthèse
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="fr-FR",
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
            # Amélioration de la qualité
            effects_profile_id=["small-bluetooth-speaker-class-device"],
        )

        # Génération
        response = self._synthesize(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        audio_content = response.audio_content

        # Estimation de la durée (approximative basée sur le texte)
        # En moyenne ~150 mots/minute, ajusté par speaking_rate
        word_count = len(text.split())
        duration = (word_count / 150) * 60 / speaking_rate

        # Sauvegarde si path spécifié
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_content)
            console.print(f"[green]✓ Audio sauvegardé : {output_path}[/green]")

        return audio_content, duration

    def generate_from_script(
        self,
        script: Script,
        voice_name: Optional[str] = None,
        engine: str = "google",
    ) -> AudioFile:
        """
        Génère l'audio pour un script complet.

        Args:
            script: Script source
            voice_name: Voix optionnelle
            engine: "google" ou "elevenlabs"

        Returns:
            AudioFile avec le chemin et métadonnées
        """
        settings.ensure_directories()

        output_path = settings.output_dir / "audio" / f"{script.format.value}_{script.id}.mp3"

        if engine == "elevenlabs":
            result = self._generate_elevenlabs(script.full_text, output_path)
            if result is not None:
                word_count = len(script.full_text.split())
                duration = (word_count / 150) * 60
                audio_file = AudioFile(
                    id=script.id,
                    script_id=script.id,
                    path=output_path,
                    duration=duration,
                    voice_name=f"elevenlabs:{settings.elevenlabs_voice_id}",
                )
                console.print(f"[dim]Durée estimée : {duration:.1f}s[/dim]")
                return audio_file
            else:
                console.print("[yellow]⚠ Fallback sur Google TTS...[/yellow]")

        # Google TTS (défaut ou fallback)
        _, duration = self.generate(
            text=script.full_text,
            output_path=output_path,
            voice_name=voice_name,
        )

        audio_file = AudioFile(
            id=script.id,
            script_id=script.id,
            path=output_path,
            duration=duration,
            voice_name=voice_name or self.default_voice,
        )

        console.print(f"[dim]Durée estimée : {duration:.1f}s[/dim]")
        return audio_file

    def _generate_elevenlabs(self, text: str, output_path: Path) -> Optional[Path]:
        """Tente de générer l'audio via ElevenLabs."""
        try:
            from src.voice.elevenlabs import ElevenLabsGenerator
            generator = ElevenLabsGenerator()
            return generator.generate(text, output_path)
        except Exception as e:
            console.print(f"[red]✗ ElevenLabs import/init échoué: {e}[/red]")
            return None

    def generate_with_ssml(
        self,
        ssml: str,
        output_path: Path,
        voice_name: Optional[str] = None,
    ) -> tuple[bytes, float]:
        """
        Génère l'audio avec SSML pour plus de contrôle.

        SSML permet de contrôler :
        - Les pauses : <break time="500ms"/>
        - L'emphase : <emphasis level="strong">mot</emphasis>
        - La vitesse locale : <prosody rate="slow">texte</prosody>
        """
        voice_name = voice_name or self.default_voice

        synthesis_input = texttospeech.SynthesisInput(ssml=ssml)

        voice = texttospeech.VoiceSelectionParams(
            language_code="fr-FR",
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=settings.tts_speaking_rate,
            pitch=settings.tts_pitch,
        )

        response = self._synthesize(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        with open(output_path, "wb") as f:
            f.write(response.audio_content)

        # Durée approximative
        import re

        clean_text = re.sub(r"<[^>]+>", "", ssml)
        word_count = len(clean_text.split())
        duration = (word_count / 150) * 60 / settings.tts_speaking_rate

        return response.audio_content, duration


def script_to_ssml(script: Script) -> str:
    """
    Convertit un script en SSML pour un meilleur rendu.

    Ajoute des pauses et emphases automatiques.
    """
    ssml_parts = ["<speak>"]

    # Hook avec emphase
    ssml_parts.append(f'<emphasis level="strong">{script.hook}</emphasis>')
    ssml_parts.append('<break time="800ms"/>')

    # Body avec pauses naturelles
    sentences = script.body.replace("...", "…").split(".")
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            ssml_parts.append(f"{sentence}.")
            ssml_parts.append('<break time="400ms"/>')

    # CTA avec légère pause avant
    ssml_parts.append('<break time="600ms"/>')
    ssml_parts.append(f'<emphasis level="moderate">{script.cta}</emphasis>')

    ssml_parts.append("</speak>")

    return "\n".join(ssml_parts)
