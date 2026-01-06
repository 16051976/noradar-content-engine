"""
Générateur de scripts avec Google Gemini API.
"""

import json
from typing import Optional
import google.generativeai as genai
from rich.console import Console

from src.config import settings
from src.models import Script, VideoFormat

console = Console()


# === PROMPTS PAR FORMAT ===

SYSTEM_PROMPT = """Tu es un expert en copywriting viral pour les réseaux sociaux français.
Tu crées des scripts pour des vidéos courtes (15-45 secondes) sur le thème des amendes routières et leur contestation.

CONTEXTE NORADAR :
- Service qui aide les Français à contester leurs amendes
- 100% satisfait ou remboursé
- Via un bot Telegram simple et rapide
- Cible : conducteurs français qui ont reçu une amende

RÈGLES DE COPYWRITING :
1. HOOK (3 premières secondes) : Doit stopper le scroll immédiatement
2. Pattern interrupt : Commence par une question choc ou une stat surprenante
3. Ton : Direct, un peu provocateur, mais jamais vulgaire
4. Évite le jargon juridique complexe
5. Utilise "tu" pas "vous"
6. CTA clair vers le bot Telegram

FORMAT DE SORTIE (JSON strict) :
{
    "title": "Titre court pour le fichier",
    "hook": "Les 3 premières secondes - doit être CHOC",
    "body": "Le corps du message - 20-30 secondes",
    "cta": "Call-to-action final - 5 secondes",
    "full_text": "Le texte complet à lire (hook + body + cta)",
    "duration_estimate": 25,
    "hashtags": ["amende", "radar", "contestation"]
}
"""

FORMAT_PROMPTS = {
    VideoFormat.SCANDALE: """FORMAT : SCANDALE / POLÉMIQUE
Objectif : Viralité maximale, partage, commentaires

ANGLE : Dénoncer une injustice du système des amendes
- L'État qui "vole" les conducteurs
- Les radars comme "pompe à fric"
- Les amendes injustes ou abusives
- Le système opaque

EXEMPLES DE HOOKS :
- "L'État encaisse 2 MILLIARDS par an avec les amendes..."
- "Ce que l'État ne veut pas que tu saches sur les radars..."
- "Tu viens de payer une amende ? Tu aurais peut-être pas dû..."

TON : Indigné mais factuel. Pas complotiste, juste réaliste.""",
    VideoFormat.TUTO: """FORMAT : TUTORIEL / ÉDUCATIF
Objectif : Conversion directe, crédibilité

ANGLE : Expliquer comment contester simplement
- Les étapes de contestation
- Les motifs légaux valables
- Ce qu'il faut vérifier sur un PV
- Les délais à respecter

EXEMPLES DE HOOKS :
- "Comment j'ai fait annuler mon amende en 5 minutes..."
- "3 choses à vérifier AVANT de payer ton amende..."
- "La méthode légale pour contester n'importe quelle amende..."

TON : Expert accessible. Tu guides, tu rassures.""",
    VideoFormat.TEMOIGNAGE: """FORMAT : TÉMOIGNAGE / PREUVE SOCIALE
Objectif : Crédibilité, confiance

ANGLE : Success stories de contestation
- Amendes annulées
- Économies réalisées
- Processus simple
- Satisfaction client

EXEMPLES DE HOOKS :
- "J'ai fait annuler 450€ d'amendes le mois dernier..."
- "Ils m'ont dit que c'était impossible de contester..."
- "Ma première amende en 10 ans, et je refuse de payer..."

TON : Authentique, personnel. Comme un pote qui raconte.""",
    VideoFormat.MYTHE: """FORMAT : MYTHE VS RÉALITÉ
Objectif : Éducation, engagement (débat en commentaires)

ANGLE : Démystifier les croyances sur les amendes
- "On ne peut pas contester" → FAUX
- "Ça coûte plus cher de contester" → FAUX
- "Faut un avocat" → FAUX
- "Les radars sont toujours fiables" → FAUX

EXEMPLES DE HOOKS :
- "Non, tu n'es PAS obligé de payer ton amende..."
- "On t'a menti sur les contestations d'amendes..."
- "Cette croyance sur les radars est FAUSSE..."

TON : Pédagogue qui remet les pendules à l'heure.""",
    VideoFormat.CHIFFRE_CHOC: """FORMAT : CHIFFRE CHOC / STAT
Objectif : Hook ultra-rapide, partage

ANGLE : Une statistique surprenante qui fait réagir
- Taux de contestation réussie
- Montant encaissé par l'État
- Nombre d'amendes injustes
- Économies moyennes

EXEMPLES DE HOOKS :
- "2 milliards. C'est ce que l'État encaisse CHAQUE ANNÉE..."
- "67% des amendes contestées sont annulées..."
- "135€. C'est le prix moyen d'une erreur de radar..."

TON : Impactant, factuel, rapide. Moins de 20 secondes total.""",
}


class ScriptGenerator:
    """Génère des scripts vidéo via Gemini API."""

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY non configurée dans .env")

        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    def generate(
        self,
        format: VideoFormat,
        theme: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Script:
        """
        Génère un script pour le format spécifié.

        Args:
            format: Le format de vidéo (SCANDALE, TUTO, etc.)
            theme: Thème spécifique optionnel
            custom_instructions: Instructions additionnelles

        Returns:
            Script généré
        """
        # Construction du prompt
        format_prompt = FORMAT_PROMPTS[format]
        user_prompt = f"{format_prompt}\n\n"

        if theme:
            user_prompt += f"THÈME SPÉCIFIQUE : {theme}\n\n"

        if custom_instructions:
            user_prompt += f"INSTRUCTIONS ADDITIONNELLES : {custom_instructions}\n\n"

        user_prompt += "Génère UN script au format JSON demandé."

        console.print(f"[blue]Génération script {format.value}...[/blue]")

        try:
            response = self.model.generate_content(
                [SYSTEM_PROMPT, user_prompt],
                generation_config=genai.GenerationConfig(
                    max_output_tokens=settings.gemini_max_tokens,
                    temperature=0.8,  # Créativité
                ),
            )

            # Extraction du JSON
            response_text = response.text.strip()

            # Nettoyer si wrapped dans ```json
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            # Parser le JSON
            data = json.loads(response_text)

            script = Script(
                format=format,
                title=data["title"],
                hook=data["hook"],
                body=data["body"],
                cta=data["cta"],
                full_text=data["full_text"],
                duration_estimate=data.get("duration_estimate", 25),
                hashtags=data.get("hashtags", []),
            )

            console.print(f"[green]✓ Script généré : {script.title}[/green]")
            return script

        except json.JSONDecodeError as e:
            console.print(f"[red]Erreur parsing JSON : {e}[/red]")
            console.print(f"[dim]Réponse brute : {response_text[:500]}...[/dim]")
            raise
        except Exception as e:
            console.print(f"[red]Erreur génération : {e}[/red]")
            raise

    def generate_batch(
        self,
        formats: dict[VideoFormat, int],
        theme: Optional[str] = None,
    ) -> list[Script]:
        """
        Génère un batch de scripts selon la distribution demandée.

        Args:
            formats: Dict {format: nombre} ex: {SCANDALE: 5, TUTO: 3}
            theme: Thème optionnel pour tous les scripts

        Returns:
            Liste de scripts générés
        """
        scripts = []

        for format, count in formats.items():
            console.print(f"\n[bold]Génération {count}x {format.value}[/bold]")
            for i in range(count):
                try:
                    script = self.generate(format, theme)
                    scripts.append(script)
                    console.print(f"  [{i + 1}/{count}] {script.title}")
                except Exception as e:
                    console.print(f"  [red][{i + 1}/{count}] Échec : {e}[/red]")

        console.print(f"\n[green]Total : {len(scripts)} scripts générés[/green]")
        return scripts

    def save_script(self, script: Script) -> str:
        """Sauvegarde un script en JSON."""
        settings.ensure_directories()
        output_path = settings.output_dir / "scripts" / script.filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(script.model_dump_json(indent=2))

        console.print(f"[dim]Sauvegardé : {output_path}[/dim]")
        return str(output_path)

    @staticmethod
    def load_script(path: str) -> Script:
        """Charge un script depuis un fichier JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)
