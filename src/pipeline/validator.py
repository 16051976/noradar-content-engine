"""
Validation qualité des scripts via Gemini API.
Score 0-100 sur 5 critères, seuil d'approbation : 70.
"""

import json
import google.generativeai as genai
from pydantic import BaseModel
from rich.console import Console

from src.config import settings
from src.models import Script

console = Console()

VALIDATION_PROMPT = """Tu es un évaluateur qualité de scripts vidéo viraux pour NoRadar (IA juridique de contestation d'amendes radar).

Évalue ce script sur 5 critères, chacun noté de 0 à 20 :

1. MÉTHODE JURIDIQUE (0-20) : Le script ne mentionne AUCUNE méthode juridique précise
   (pas d'articles de loi, pas de L.121-3, pas de motifs de contestation).
   20 = aucune mention, 0 = méthode détaillée.

2. CONCLUSION POSITIVE (0-20) : La conclusion est positive et affirmative.
   Résultat concret (amende annulée, points gardés). Jamais de doute.
   Finit par "Conçu par des avocats. Exécuté par une IA."

3. CTA CLAIR (0-20) : Call-to-action clair avec "lien en bio" ou Telegram.
   Mentionne 34€, 60 secondes, remboursement.

4. ORIGINALITÉ DU HOOK (0-20) : Le hook est original, pas générique.
   Montant précis, situation concrète, accroche qui stoppe le scroll.

5. CONFORMITÉ TIKTOK (0-20) : Pas de termes à risque de shadowban.
   Pas de vocabulaire agressif, pas de promesses exagérées, pas de spam.

SCRIPT À ÉVALUER :
Format : {format}
Hook : {hook}
Body : {body}
CTA : {cta}
Full text : {full_text}

Réponds UNIQUEMENT en JSON strict :
{{
    "methode_juridique": <0-20>,
    "conclusion_positive": <0-20>,
    "cta_clair": <0-20>,
    "originalite_hook": <0-20>,
    "conformite_tiktok": <0-20>,
    "score": <0-100 somme des 5>,
    "issues": ["problème 1", "problème 2"],
    "approved": <true si score >= 70, false sinon>
}}
"""


class ValidationResult(BaseModel):
    methode_juridique: int
    conclusion_positive: int
    cta_clair: int
    originalite_hook: int
    conformite_tiktok: int
    score: int
    issues: list[str]
    approved: bool


class ScriptValidator:
    """Valide la qualité d'un script via Gemini. Seuil : 70/100."""

    SCORE_THRESHOLD = 70

    def __init__(self):
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY non configurée dans .env")
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    def validate(self, script: Script) -> ValidationResult:
        prompt = VALIDATION_PROMPT.format(
            format=script.format.value,
            hook=script.hook,
            body=script.body,
            cta=script.cta,
            full_text=script.full_text,
        )

        response = self.model.generate_content(prompt)
        text = response.text.strip()

        # Nettoyer si wrapped dans ```json
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)
        result = ValidationResult(**data)

        if result.approved:
            console.print(f"[green]Validation OK (score: {result.score}/100)[/green]")
        else:
            console.print(f"[yellow]Validation échouée (score: {result.score}/100)[/yellow]")
            for issue in result.issues:
                console.print(f"  [yellow]- {issue}[/yellow]")

        return result
