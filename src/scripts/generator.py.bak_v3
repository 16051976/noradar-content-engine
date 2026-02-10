"""
Générateur de scripts avec Google Gemini API.
"""

import json
from typing import Optional
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, DeadlineExceeded
from rich.console import Console

from src.utils.retry import with_retry

from src.config import settings
from src.models import Script, VideoFormat

console = Console()


# === PROMPTS PAR FORMAT ===

SYSTEM_PROMPT = """Tu es un expert en copywriting viral pour les réseaux sociaux français.
Tu crées des scripts pour des vidéos courtes (20-30 secondes) sur le thème des amendes routières.

CONTEXTE NORADAR :
- IA juridique de contestation d'amendes, conçue par des avocats spécialisés
- Prix : 34€ (ce prix bas est possible parce que tout est automatisé)
- Garantie : 100% remboursé si la contestation échoue
- Process : envoie la photo de ton PV sur Telegram, l'IA fait le reste en 60 secondes
- Gimmick signature : "Conçu par des avocats. Exécuté par une IA."

RÈGLES ABSOLUES - NE JAMAIS MENTIONNER :
- La méthode juridique utilisée (aucun article de loi)
- Comment fonctionne la contestation techniquement
- Les motifs de contestation (vice de procédure, etc.)
- Toute information qui permettrait de contester sans NoRadar
- Les mots "équipe", "manuel", "on s'occupe", "nous analysons"

MESSAGE CLÉ : "Une IA juridique créée par des avocats. 60 secondes. 34€. Remboursé si ça marche pas."

RÈGLES DE COPYWRITING :
1. HOOK (3 sec) : Question personnelle ou stat relatable - stopper le scroll
2. Ton : Complice, comme un pote qui file un bon plan. Pas vendeur, pas victime.
3. Durée totale : 20-30 secondes MAX (150-200 mots)
4. Utilise "tu" pas "vous"
5. CTA : Toujours mentionner "lien en bio" et terminer avec le gimmick "Conçu par des avocats. Exécuté par une IA."

STRUCTURE OPTIMALE :
- HOOK (3 sec) : Question ou accroche personnelle
- PROBLÈME (5 sec) : La galère de recevoir une amende
- SOLUTION (10 sec) : NoRadar = IA juridique, rapide, garanti
- CTA (5 sec) : Lien en bio + gimmick signature

FORMAT DE SORTIE (JSON strict) :
{
    "title": "Titre_Court_Sans_Espaces",
    "hook": "Les 3 premières secondes - accroche",
    "body": "Corps du message - 15-20 secondes",
    "cta": "Call-to-action final - 5 secondes",
    "full_text": "Le texte complet à lire (hook + body + cta)",
    "duration_estimate": 25,
    "hashtags": ["amende", "radar", "contestation", "noradar", "telegram"]
}
"""

FORMAT_PROMPTS = {
    VideoFormat.SCANDALE: """FORMAT : ACCROCHE FORTE
Objectif : Stopper le scroll, créer de l'engagement

ANGLE : Faire réaliser qu'on peut agir (sans expliquer comment)
- "Tu sais que t'es pas obligé de payer ?"
- "La plupart des gens paient sans réfléchir"
- "Le système compte sur le fait que tu contestes pas"

EXEMPLES DE HOOKS :
- "T'as déjà payé une amende en te disant 'j'aurais peut-être pu contester' ?"
- "Reçu une amende ? Attends avant de payer..."
- "Ce que 90% des conducteurs ne font jamais avec leurs amendes..."

TON : Complice, pas indigné. Tu donnes un bon plan, pas une leçon.

POINTS CLÉS À INTÉGRER :
- IA juridique conçue par des avocats spécialisés
- 60 secondes sur Telegram, tout est automatisé
- 34€ seulement (automatisé, pas low-cost)
- Remboursé si ça marche pas
- Terminer par le gimmick : "Conçu par des avocats. Exécuté par une IA."

NE PAS MENTIONNER : méthode, article de loi, motifs juridiques, équipe, traitement manuel.""",

    VideoFormat.TUTO: """FORMAT : SIMPLICITÉ DU PROCESS
Objectif : Montrer que c'est ultra simple (sans révéler la méthode)

ANGLE : Rassurer sur la facilité
- C'est pas compliqué
- Pas besoin de s'y connaître
- 60 secondes et c'est fait

EXEMPLES DE HOOKS :
- "Contester une amende en 60 secondes ? Je t'explique..."
- "Tu penses que contester c'est galère ? Regarde ça..."
- "La façon la plus simple de contester ton amende..."

TON : Pédagogue accessible. Tu simplifies, tu rassures.

STRUCTURE :
1. Hook : "C'est plus simple que tu crois"
2. Process simplifié : "Tu prends ton PV en photo sur Telegram"
3. Rassurance : "L'IA juridique, conçue par des avocats, génère ta contestation automatiquement"
4. Garantie : "Et si ça marche pas, tu es remboursé"
5. CTA : Lien en bio + "Conçu par des avocats. Exécuté par une IA."

NE PAS MENTIONNER : ce qu'on fait concrètement, les motifs, la méthode, équipe humaine.""",

    VideoFormat.TEMOIGNAGE: """FORMAT : PREUVE SOCIALE
Objectif : Crédibilité par l'exemple type de situation

ANGLE : Quelqu'un raconte son expérience
- Sceptique au début ("une IA pour contester ?")
- A testé
- Ça a marché
- Recommande

EXEMPLES DE HOOKS :
- "J'y croyais pas du tout au début..."
- "Quand j'ai reçu mon amende, j'allais payer direct..."
- "Un pote m'a parlé de cette IA qui conteste les amendes..."

TON : Authentique, naturel. Comme un pote qui raconte.

ÉLÉMENTS À INCLURE :
- Montant de l'amende (90€, 135€, etc.)
- "J'ai juste envoyé la photo de mon PV sur Telegram"
- "L'algorithme a généré ma contestation en 60 secondes"
- "X semaines plus tard, amende annulée"
- "Et c'était que 34€, remboursé si ça marchait pas"
- Finir par : "Conçu par des avocats. Exécuté par une IA."

NE PAS MENTIONNER : pourquoi ça a marché, la méthode, les motifs, équipe humaine.""",

    VideoFormat.MYTHE: """FORMAT : CROYANCE À CASSER
Objectif : Éduquer sans révéler la méthode

ANGLE : Casser les idées reçues
- "On peut pas contester" → Faux
- "C'est trop compliqué" → Faux, une IA le fait en 60 secondes
- "Ça sert à rien" → Faux
- "Faut un avocat" → Faux, l'IA a été conçue par des avocats

EXEMPLES DE HOOKS :
- "Non, t'es pas obligé de payer ton amende..."
- "'Contester ça sert à rien' - C'est faux, et je t'explique pourquoi..."
- "On t'a fait croire que contester c'était compliqué..."

TON : Bienveillant mais affirmatif. Tu remets les pendules à l'heure.

STRUCTURE :
1. Le mythe que les gens croient
2. Pourquoi c'est faux (sans détailler la méthode)
3. La solution simple : NoRadar, moteur de contestation automatisé conçu par des avocats
4. CTA + gimmick : "Conçu par des avocats. Exécuté par une IA."

NE PAS MENTIONNER : les vraies raisons juridiques, les articles de loi, équipe humaine.""",

    VideoFormat.CHIFFRE_CHOC: """FORMAT : STATISTIQUE ACCROCHEUSE
Objectif : Hook ultra-rapide par un chiffre

ANGLE : Un chiffre qui fait réagir
- Montant payé par les Français
- Nombre d'amendes contestables
- 34€ parce que c'est automatisé, pas parce que c'est low-cost

EXEMPLES DE HOOKS :
- "34€. C'est tout ce que ça coûte de contester ton amende avec une IA..."
- "60 secondes. C'est le temps qu'il faut à l'algorithme pour générer ta contestation..."
- "Remboursé. Si la contestation marche pas, tu paies rien..."

TON : Impactant, direct. Chiffre → Explication → CTA.

DURÉE : 15-20 secondes max. Court et percutant.

STRUCTURE :
1. Le chiffre (hook)
2. Ce que ça signifie (5 sec)
3. Comment en profiter : NoRadar, IA juridique conçue par des avocats (5 sec)
4. CTA rapide + "Conçu par des avocats. Exécuté par une IA."

NE PAS MENTIONNER : statistiques de succès précises, méthode, équipe humaine.""",

    VideoFormat.ULTRA_COURT: """FORMAT : ULTRA COURT (15 secondes)
Objectif : Message percutant en 50-70 mots maximum

ANGLE : Aller droit au but
- Une accroche
- Un bénéfice clé
- CTA immédiat

EXEMPLES DE HOOKS :
- "Amende ? L'IA conteste en 60 secondes."
- "34€. Automatisé. Remboursé si ça marche pas."
- "Photo du PV → l'algorithme génère ta contestation."

TON : Direct, efficace. Pas de blabla.

DURÉE : 15 secondes MAX (50-70 mots)

STRUCTURE :
1. Hook (2 sec)
2. Promesse (5 sec)
3. CTA (3 sec) + "Conçu par des avocats. Exécuté par une IA."

NE PAS MENTIONNER : détails, méthode, justification, équipe humaine.""",
}


class ScriptGenerator:
    """Génère des scripts vidéo via Gemini API."""

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY non configurée dans .env")

        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    @with_retry(exceptions=(ResourceExhausted, ServiceUnavailable, DeadlineExceeded))
    def _call_gemini_api(self, prompts, generation_config):
        """Appel API Gemini avec retry automatique."""
        return self.model.generate_content(prompts, generation_config=generation_config)

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

        user_prompt += "Génère UN script au format JSON demandé. Rappel : ne JAMAIS mentionner la méthode juridique."

        console.print(f"[blue]Génération script {format.value}...[/blue]")

        try:
            response = self._call_gemini_api(
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
        if settings.tracking_enabled:
            console.print(f"[cyan]🔗 Lien trackable : {script.telegram_link}[/cyan]")
        return str(output_path)

    @staticmethod
    def load_script(path: str) -> Script:
        """Charge un script depuis un fichier JSON."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Script(**data)
