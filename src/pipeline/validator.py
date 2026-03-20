"""
Validation qualité des scripts via Gemini API.
"""

import json
import google.generativeai as genai
from pydantic import BaseModel
from rich.console import Console

from src.config import settings
from src.models import Script

console = Console()

VALIDATION_PROMPT = """Tu es un évaluateur qualité de scripts vidéo viraux pour NoRadar (IA juridique de contestation d'amendes radar).

Évalue ce script sur 3 critères, chacun noté de 1 à 10 :

1. HOOK (accroche) : Est-ce que les 3 premières secondes stoppent le scroll ?
   - Montant précis mentionné ?
   - Situation concrète et relatable ?
   - Pas un hook interdit (trop générique, déjà vu) ?

2. COMPLIANCE : Le script respecte-t-il les règles métier ?
   - Ne mentionne PAS la méthode juridique, les articles de loi, les motifs
   - Ne mentionne PAS d'amendes non couvertes (stationnement, alcool, etc.)
   - Mentionne bien : 34€, 60 secondes, Telegram, remboursement
   - Finit sur un résultat POSITIF (amende annulée, points gardés)
   - Finit par "Conçu par des avocats. Exécuté par une IA."

3. ENGAGEMENT : Le script donne-t-il envie de regarder jusqu'au bout ?
   - Structure narrative claire ?
   - Ton authentique première personne ?
   - CTA clair ?

SCRIPT À ÉVALUER :
Format : {format}
Hook : {hook}
Body : {body}
CTA : {cta}

Réponds UNIQUEMENT en JSON strict :
{{
    "hook_score": <1-10>,
    "compliance_score": <1-10>,
    "engagement_score": <1-10>,
    "overall_score": <1-10>,
    "issues": ["problème 1", "problème 2"],
    "passed": <true si overall_score >= 6, false sinon>
}}
"""


class ValidationResult(BaseModel):
    hook_score: int
    compliance_score: int
    engagement_score: int
    overall_score: int
    issues: list[str]
    passed: bool


class ScriptValidator:
    """Valide la qualité d'un script via Gemini."""

    SCORE_THRESHOLD = 6

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

        if result.passed:
            console.print(f"[green]✓ Validation OK (score: {result.overall_score}/10)[/green]")
        else:
            console.print(f"[yellow]✗ Validation échouée (score: {result.overall_score}/10)[/yellow]")
            for issue in result.issues:
                console.print(f"  [yellow]- {issue}[/yellow]")

        return result
