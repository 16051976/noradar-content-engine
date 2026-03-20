"""
Générateur de scripts avec Google Gemini API.
"""

import json
from typing import Optional
import anthropic
from rich.console import Console

from src.config import settings
from src.models import Script, VideoFormat

console = Console()


# === PROMPTS PAR FORMAT ===

SYSTEM_PROMPT = """Tu es un expert en copywriting viral pour les réseaux sociaux français.
Tu crées des scripts pour des vidéos courtes (15-20 secondes) sur le thème des amendes routières.

CONTEXTE NORADAR :
- IA juridique de contestation d'amendes, conçue par des avocats spécialisés
- Prix : 34€ (ce prix bas est possible parce que tout est automatisé)
- Garantie : 100% remboursé si la contestation échoue
- Process : envoie la photo de ton PV sur Telegram, l'IA fait le reste en 60 secondes
- Gimmick signature : "Conçu par des avocats. Exécuté par une IA."

═══════════════════════════════════════════════════════════════
TYPES D'AMENDES COUVERTES (radars automatiques uniquement) :
═══════════════════════════════════════════════════════════════
✅ Excès de vitesse (radar fixe, mobile, tronçon)
✅ Feu rouge grillé
✅ Ceinture non attachée
✅ Téléphone au volant
✅ Franchissement de ligne continue

═══════════════════════════════════════════════════════════════
AMENDES NON COUVERTES — NE JAMAIS MENTIONNER :
═══════════════════════════════════════════════════════════════
❌ Stationnement
❌ Alcoolémie / stupéfiants
❌ Contrôle technique
❌ Amendes dressées manuellement par un agent

═══════════════════════════════════════════════════════════════
RÈGLES ABSOLUES — NE JAMAIS MENTIONNER :
═══════════════════════════════════════════════════════════════
❌ La méthode juridique utilisée (aucun article de loi, pas de L.121-3)
❌ Comment fonctionne la contestation techniquement
❌ Les motifs de contestation (vice de procédure, anomalie, etc.)
❌ Toute information qui permettrait de contester sans NoRadar
❌ Les mots "équipe", "manuel", "on s'occupe", "nous analysons"
✅ La conclusion doit TOUJOURS être POSITIVE : amende annulée, points gardés, succès confirmé

═══════════════════════════════════════════════════════════════
RÈGLES DE COPYWRITING :
═══════════════════════════════════════════════════════════════
1. HOOK (3 sec) : Situation personnelle avec montant précis - stopper le scroll
2. TON : Complice, première personne (POV). Tu racontes TON histoire.
3. DURÉE : 15-20 secondes MAX (80-100 mots)
4. TUTOIEMENT : Utilise "j'" / "tu", jamais "vous" / "nous"
5. CTA : Toujours "lien en bio" + gimmick "Conçu par des avocats. Exécuté par une IA."
6. CONCLUSION POSITIVE OBLIGATOIRE : TOUJOURS finir sur un succès

═══════════════════════════════════════════════════════════════
ANGLES ÉMOTIONNELS — CHOISIS UN OBLIGATOIREMENT :
═══════════════════════════════════════════════════════════════
RAGE/INJUSTICE    → "135€ pour 7 km/h de trop. Absurde."
SOULAGEMENT       → "J'allais payer 135€. J'ai payé 34€. Amende annulée."
PROVOCATION       → "Tu paies tes amendes ? T'as tort."
CHOC/RÉVÉLATION   → "Personne m'avait dit qu'on pouvait faire ça."
COMPLICITÉ        → "Un pote m'a passé le bon plan. Je te le passe."

Indique l'angle choisi dans le champ "hook_emotion" du JSON.

═══════════════════════════════════════════════════════════════
HOOKS QUI CARTONNENT (patterns prouvés) :
═══════════════════════════════════════════════════════════════
CONFESSION+CHIFFRE  → "J'ai payé 270€ d'amendes cette année. La dernière, j'aurais dû contester."
RÉSULTAT IMPOSSIBLE → "135€ d'amende. 60 secondes. 0€ payé."
PROVOCATION DIRECTE → "Tu paies tes amendes sans réfléchir ? Stop."
INJUSTICE CONCRÈTE  → "Flashé à 83 au lieu de 80. 3 points en moins. Pour 3 km/h."
DÉCOUVERTE TARDIVE  → "J'ai su trop tard que cette amende était contestable."

HOOKS INTERDITS (trop vus, trop génériques) :
❌ "X% des conducteurs font cette erreur"
❌ "La vérité sur les amendes"
❌ "Ce que personne ne te dit"
❌ "Tu savais que..."
❌ Toute reformulation de ces patterns

═══════════════════════════════════════════════════════════════
DÉTAILS OBLIGATOIRES DANS CHAQUE SCRIPT :
═══════════════════════════════════════════════════════════════
✅ Montant précis de l'amende (90€, 135€, etc.)
✅ Type d'infraction radar automatique (excès de vitesse, feu rouge, etc.)
✅ "Photo du PV sur Telegram"
✅ "60 secondes"
✅ "34€, remboursé si ça marche pas"
✅ Terminer par "Conçu par des avocats. Exécuté par une IA."

═══════════════════════════════════════════════════════════════
FORMAT DE SORTIE (JSON strict) :
═══════════════════════════════════════════════════════════════
{
    "title": "Titre_Court_Sans_Espaces",
    "hook": "Les 3 premières secondes - accroche",
    "body": "Corps du message - 15-20 secondes",
    "cta": "Call-to-action final - 5 secondes",
    "full_text": "Le texte complet à lire (hook + body + cta)",
    "duration_estimate": 25,
    "hashtags": ["amende", "radar", "contestation", "noradar", "telegram"],
    "thumbnail_text": {
        "line1": "TEXTE LIGNE 1 (5-7 mots max, chiffré/situation)",
        "line2": "TEXTE LIGNE 2 (3-5 mots max, action/résultat)"
    },
    "facebook_caption": "Caption longue pour Facebook (3-5 phrases)"
}

═══════════════════════════════════════════════════════════════
RÈGLES POUR thumbnail_text (VIGNETTE) :
═══════════════════════════════════════════════════════════════
- line1 : Toujours un FAIT CHIFFRÉ ou SITUATION (ex: "135€ D'AMENDE", "FLASHÉ À 137")
- line2 : Toujours une ACTION ou RÉSULTAT (ex: "J'AI PAS PAYÉ.", "CONTESTÉE EN 60S.")
- Maximum 7 mots par ligne
- MAJUSCULES uniquement
- Pas de point à la fin de line1
- Point ou point d'exclamation à la fin de line2
- Doit créer de la CURIOSITÉ (donner envie de regarder la vidéo)

═══════════════════════════════════════════════════════════════
RÈGLES POUR facebook_caption :
═══════════════════════════════════════════════════════════════
- 3-5 phrases, ton explicatif mais accessible
- Commencer par une accroche (question ou constat)
- Expliquer brièvement le service NoRadar
- Bullet points avec émojis (→ ou ✓)
- Terminer par "Lien en commentaire 👇"
- PAS de hashtags dans la caption Facebook
- JAMAIS mentionner la méthode juridique
- PAS de sauts de ligne dans le texte, tout sur une seule ligne
- Utiliser des tirets ou → pour séparer les sections

EXEMPLE facebook_caption :
"Reçu une amende radar ? Avant de payer, regarde ça.

Une IA juridique conçue par des avocats analyse ton PV et génère ta contestation en 60 secondes.

→ 34€ tout compris
→ Remboursé si ça marche pas
→ 100% automatisé sur Telegram

Lien en commentaire 👇"
"""

FORMAT_PROMPTS = {
    # ═══════════════════════════════════════════════════════════════
    # NOUVEAUX FORMATS STORY-DRIVEN (PRIORITAIRES)
    # ═══════════════════════════════════════════════════════════════

    VideoFormat.STORY_POV: """FORMAT : STORY POV (Format star - 27% du contenu)
Objectif : Raconter une histoire personnelle de contestation en première personne

STRUCTURE OBLIGATOIRE :
[HOOK - 0-2s] "J'ai reçu une amende de [montant]€ pour [infraction radar]."
[TENSION - 2-8s] Contexte, pourquoi c'est frustrant, premier réflexe de payer
[PIVOT - 8-14s] "Puis j'ai testé NoRadar" — Photo PV sur Telegram, 60 secondes
[RÉSULTAT - 14-20s] "Résultat ? Amende annulée. 34€ pour garder mes points ? Meilleur investissement."
[CTA - 20-25s] "Lien en bio. Conçu par des avocats. Exécuté par une IA."

EXEMPLES DE HOOKS POV :
- "J'ai reçu une amende de 90€ pour excès de vitesse la semaine dernière."
- "135€ pour un feu rouge grillé sur l'A6. J'étais dégoûté."
- "Flashé à 137 au lieu de 130. Mon premier réflexe ? Payer."
- "Téléphone au volant. 135€ + 3 points. J'allais payer..."

TON : Authentique, première personne, comme si tu racontais à un pote.

ÉLÉMENTS OBLIGATOIRES :
- Montant précis (90€, 135€, etc.)
- Type d'infraction radar automatique
- "Photo du PV sur Telegram"
- "60 secondes"
- "34€, remboursé si ça marche pas"
- TOUJOURS finir sur un SUCCÈS → amende annulée, points gardés

EXEMPLES thumbnail_text :
- {"line1": "135€ D'AMENDE", "line2": "J'AI PAS PAYÉ."}
- {"line1": "FLASHÉ À 137", "line2": "SUR L'A6."}
- {"line1": "90€ POUR RIEN", "line2": "J'AI CONTESTÉ."}
- {"line1": "FEU ROUGE GRILLÉ", "line2": "ET ALORS ?"}

NE PAS MENTIONNER : méthode juridique, article de loi, motifs, équipe.""",

    VideoFormat.DEBUNK: """FORMAT : DEBUNK (20% du contenu)
Objectif : Casser une idée reçue sans révéler la méthode

STRUCTURE :
[HOOK - 2s] Affirmation contre-intuitive ("J'ai arrêté de payer mes amendes direct")
[CROYANCE - 5s] Ce que les gens pensent à tort
[RÉALITÉ - 8s] Pourquoi c'est faux (SANS révéler la méthode)
[SOLUTION - 8s] NoRadar, Telegram, 60 secondes, 34€
[CTA - 5s] "Lien en bio. Conçu par des avocats. Exécuté par une IA."

EXEMPLES DE HOOKS DEBUNK :
- "J'ai arrêté de payer mes amendes radar direct."
- "Non, t'es pas obligé de payer ton amende."
- "3 raisons de ne pas payer ton amende tout de suite."
- "Tout le monde me dit de payer. Je fais l'inverse."

CROYANCES À CASSER :
- "On peut pas contester" → Faux
- "C'est trop compliqué" → 60 secondes sur Telegram
- "Ça sert à rien" → Faux
- "Faut un avocat" → L'IA est conçue par des avocats

TON : Affirmatif, bienveillant. Tu remets les pendules à l'heure.

EXEMPLES thumbnail_text :
- {"line1": "90% DES GENS", "line2": "FONT CETTE ERREUR."}
- {"line1": "ARRÊTE DE PAYER", "line2": "DIRECT."}
- {"line1": "ON T'A MENTI", "line2": "SUR LES AMENDES."}
- {"line1": "TU CROIS QUE", "line2": "T'AS PAS LE CHOIX ?"}

NE PAS MENTIONNER : méthode, article de loi, motifs juridiques.""",

    VideoFormat.CAS_REEL: """FORMAT : CAS RÉEL (20% du contenu)
Objectif : Raconter un cas type (anonymisé) avec suspense

STRUCTURE :
[HOOK - 2s] "Un conducteur a reçu une amende de [montant]€ pour [infraction]"
[CONTEXTE - 6s] Circonstances (autoroute, ville, radar automatique)
[RÉACTION - 5s] "Il allait payer, puis il a découvert NoRadar"
[ACTION - 6s] "Photo du PV, Telegram, 60 secondes, dossier généré"
[RÉSULTAT - 4s] "2 semaines plus tard : amende annulée. Points intacts."
[CTA - 5s] "Même situation ? Lien en bio. Conçu par des avocats. Exécuté par une IA."

EXEMPLES DE HOOKS CAS RÉEL :
- "Un conducteur a reçu une amende de 135€ pour un feu rouge grillé."
- "Flashé à 92 au lieu de 80 sur une départementale."
- "Téléphone au volant. 135€ + 3 points."
- "Elle roulait à 54 en zone 50. Amende quand même."

TON : Narratif, factuel. Tu racontes l'histoire de quelqu'un d'autre.

INFRACTIONS RADAR AUTOMATIQUE UNIQUEMENT :
- Excès de vitesse (fixe, mobile, tronçon)
- Feu rouge
- Ceinture
- Téléphone au volant
- Ligne continue

EXEMPLES thumbnail_text :
- {"line1": "TÉLÉPHONE AU VOLANT", "line2": "135€ + 3 POINTS."}
- {"line1": "FEU ROUGE GRILLÉ", "line2": "DOSSIER ENVOYÉ."}
- {"line1": "FLASHÉ À 92", "line2": "AU LIEU DE 80."}
- {"line1": "54 EN ZONE 50", "line2": "AMENDE QUAND MÊME."}

NE PAS MENTIONNER : méthode, article de loi.""",

    # ═══════════════════════════════════════════════════════════════
    # FORMATS EXISTANTS (FEATURE-DRIVEN)
    # ═══════════════════════════════════════════════════════════════

    VideoFormat.SCANDALE: """FORMAT : SCANDALE / ACCROCHE FORTE (13% du contenu)
Objectif : Stopper le scroll, créer de l'engagement

ANGLE : Faire réaliser qu'on peut agir (sans expliquer comment)

EXEMPLES DE HOOKS :
- "T'as déjà payé une amende en te disant 'j'aurais peut-être pu contester' ?"
- "Le système compte sur le fait que tu contestes pas."
- "Ce que 90% des conducteurs ne font jamais avec leurs amendes..."
- "Ils encaissent 2 milliards par an. Et si tu arrêtais de payer ?"

TON : Complice, pas indigné. Tu donnes un bon plan, pas une leçon.

ÉLÉMENTS À INCLURE :
- IA juridique conçue par des avocats spécialisés
- 60 secondes sur Telegram, tout est automatisé
- 34€ seulement (automatisé, pas low-cost)
- Remboursé si ça marche pas
- Terminer par "Conçu par des avocats. Exécuté par une IA."

EXEMPLES thumbnail_text :
- {"line1": "ILS COMPTENT", "line2": "SUR TON SILENCE."}
- {"line1": "90% DES GENS", "line2": "PAIENT SANS RÉFLÉCHIR."}
- {"line1": "2 MILLIARDS PAR AN", "line2": "ET TOI ?"}

NE PAS MENTIONNER : méthode, article de loi, motifs juridiques, équipe.""",

    VideoFormat.TUTO: """FORMAT : TUTO / SIMPLICITÉ (10% du contenu)
Objectif : Montrer que c'est ultra simple (sans révéler la méthode)

EXEMPLES DE HOOKS :
- "Contester une amende en 60 secondes ? Je t'explique..."
- "Tu penses que contester c'est galère ? Regarde ça..."
- "La façon la plus simple de contester ton amende..."

STRUCTURE :
1. Hook : "C'est plus simple que tu crois"
2. Process simplifié : "Tu prends ton PV en photo sur Telegram"
3. Rassurance : "L'IA génère ta contestation automatiquement"
4. Garantie : "Et si ça marche pas, tu es remboursé"
5. CTA : Lien en bio + "Conçu par des avocats. Exécuté par une IA."

TON : Pédagogue accessible. Tu simplifies, tu rassures.

EXEMPLES thumbnail_text :
- {"line1": "60 SECONDES", "line2": "POUR CONTESTER."}
- {"line1": "PHOTO DU PV", "line2": "ET C'EST FAIT."}
- {"line1": "PLUS SIMPLE", "line2": "QUE TU CROIS."}

NE PAS MENTIONNER : ce qu'on fait concrètement, les motifs, la méthode.""",

    VideoFormat.TEMOIGNAGE: """FORMAT : TÉMOIGNAGE / PREUVE SOCIALE
Objectif : Crédibilité par l'exemple type de situation

EXEMPLES DE HOOKS :
- "J'y croyais pas du tout au début..."
- "Quand j'ai reçu mon amende, j'allais payer direct..."
- "Un pote m'a parlé de cette IA qui conteste les amendes..."

TON : Authentique, naturel. Comme un pote qui raconte.

ÉLÉMENTS À INCLURE :
- Montant de l'amende (90€, 135€, etc.)
- "J'ai juste envoyé la photo de mon PV sur Telegram"
- "L'IA a généré ma contestation en 60 secondes"
- "Et c'était que 34€, remboursé si ça marchait pas"
- RÉSULTAT POSITIF : "Amende annulée", "Points intacts", "Classement sans suite"

EXEMPLES thumbnail_text :
- {"line1": "J'Y CROYAIS PAS", "line2": "ET POURTANT."}
- {"line1": "135€ D'AMENDE", "line2": "J'AI TESTÉ."}
- {"line1": "UN POTE M'A DIT", "line2": "TESTE ÇA."}

NE PAS MENTIONNER : pourquoi ça a marché, la méthode, les motifs.""",

    VideoFormat.MYTHE: """FORMAT : MYTHE / CROYANCE À CASSER
Objectif : Éduquer sans révéler la méthode

EXEMPLES DE HOOKS :
- "Non, t'es pas obligé de payer ton amende..."
- "'Contester ça sert à rien' - C'est faux..."
- "On t'a fait croire que contester c'était compliqué..."

STRUCTURE :
1. Le mythe que les gens croient
2. Pourquoi c'est faux (sans détailler la méthode)
3. La solution simple : NoRadar
4. CTA + "Conçu par des avocats. Exécuté par une IA."

TON : Bienveillant mais affirmatif.

EXEMPLES thumbnail_text :
- {"line1": "TU CROIS QUE", "line2": "C'EST COMPLIQUÉ ?"}
- {"line1": "MYTHE", "line2": "DÉTRUIT."}
- {"line1": "ON T'A MENTI", "line2": "VOICI LA VÉRITÉ."}

NE PAS MENTIONNER : les vraies raisons juridiques, les articles de loi.""",

    VideoFormat.CHIFFRE_CHOC: """FORMAT : CHIFFRE CHOC (10% du contenu)
Objectif : Hook ultra-rapide par un chiffre

EXEMPLES DE HOOKS :
- "34€. C'est tout ce que ça coûte de contester ton amende avec une IA..."
- "60 secondes. C'est le temps qu'il faut à l'IA pour générer ta contestation..."
- "Remboursé. Si la contestation marche pas, tu paies rien..."

DURÉE : 15-20 secondes max. Court et percutant.

STRUCTURE :
1. Le chiffre (hook)
2. Ce que ça signifie (5 sec)
3. Comment en profiter : NoRadar (5 sec)
4. CTA rapide + "Conçu par des avocats. Exécuté par une IA."

EXEMPLES thumbnail_text :
- {"line1": "34€", "line2": "TOUT COMPRIS."}
- {"line1": "60 SECONDES", "line2": "CHRONO."}
- {"line1": "REMBOURSÉ", "line2": "SI ÇA MARCHE PAS."}

NE PAS MENTIONNER : statistiques de succès précises, méthode.""",

    VideoFormat.ULTRA_COURT: """FORMAT : ULTRA COURT (15 secondes max)
Objectif : Message percutant en 50-70 mots maximum

EXEMPLES DE HOOKS :
- "Amende ? L'IA conteste en 60 secondes."
- "34€. Automatisé. Remboursé si ça marche pas."
- "Photo du PV → l'IA génère ta contestation."

DURÉE : 15 secondes MAX (40-60 mots)

STRUCTURE :
1. Hook (2 sec)
2. Promesse (5 sec)
3. CTA (3 sec) + "Conçu par des avocats. Exécuté par une IA."

TON : Direct, efficace. Pas de blabla.

EXEMPLES thumbnail_text :
- {"line1": "AMENDE ?", "line2": "60 SECONDES."}
- {"line1": "34€", "line2": "REMBOURSÉ."}
- {"line1": "PHOTO DU PV", "line2": "C'EST TOUT."}

NE PAS MENTIONNER : détails, méthode, justification.""",

    VideoFormat.VRAI_FAUX: """FORMAT : VRAI OU FAUX (12-15 secondes)
Objectif : Engagement maximum via un format interactif qui pousse aux commentaires

STRUCTURE STRICTE :
1. HOOK (2 sec) : "VRAI ou FAUX :" + affirmation provocante sur les amendes/radars/permis
2. PAUSE (1 sec) : "La réponse va te surprendre..." ou "Réfléchis bien..." ou "Tu es sûr de toi ?"
3. RÉPONSE (3 sec) : "C'est FAUX !" ou "C'est VRAI !" + explication flash en 1 phrase
4. LIEN NORADAR (3 sec) : Relier naturellement à NoRadar comme solution
5. CTA (3 sec) : "Lien en bio. Conçu par des avocats. Exécuté par une IA."

EXEMPLES D'AFFIRMATIONS (varier à chaque génération, NE JAMAIS réutiliser) :
- "VRAI ou FAUX : Tu es obligé de payer une amende radar dans les 45 jours"
- "VRAI ou FAUX : Si tu contestes, tu risques de payer plus cher"
- "VRAI ou FAUX : Un excès de 1 km/h peut te coûter des points"
- "VRAI ou FAUX : Une amende payée ne peut plus être contestée"
- "VRAI ou FAUX : Les radars ont une marge d'erreur obligatoire"
- "VRAI ou FAUX : Contester une amende, c'est réservé aux riches"
- "VRAI ou FAUX : Tu peux recevoir une amende sans être flashé"
- "VRAI ou FAUX : Le propriétaire du véhicule paie toujours l'amende"

TON : Mystérieux au début, affirmatif à la réponse. Pousser les gens à commenter leur réponse.

DURÉE : 12-15 secondes MAX (40-60 mots)

RÈGLE CLÉ : L'affirmation doit être suffisamment ambiguë pour que 50% des gens se trompent.

NE PAS MENTIONNER : articles de loi, méthode juridique, motifs de contestation, équipe humaine.""",
}


class ScriptGenerator:
    """Génère des scripts vidéo via Gemini API."""

    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY non configurée dans .env")
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._generated_hooks: list[str] = []

    def _call_claude_api(self, system: str, user: str) -> str:
        message = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            temperature=1.0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text

    def generate(
        self,
        format: VideoFormat,
        theme: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> Script:
        """
        Génère un script pour le format spécifié.
        Injecte de la variabilité pour éviter les doublons en batch.
        """
        import random

        # === VARIABILITÉ : angles aléatoires pour casser le cache Gemini ===
        ANGLE_VARIATIONS = {
            VideoFormat.STORY_POV: [
                "Angle : excès de vitesse sur autoroute, frustration du conducteur régulier",
                "Angle : feu rouge grillé en ville, premier PV de sa vie",
                "Angle : flashé à 3 km/h au-dessus, sentiment d'injustice",
                "Angle : téléphone au volant, amende reçue 2 semaines après",
                "Angle : ceinture non attachée sur un parking, absurde",
                "Angle : conducteur qui cumule les amendes et découvre NoRadar",
                "Angle : jeune conducteur qui risque de perdre son permis probatoire",
                "Angle : parent pressé qui se fait flasher en emmenant les enfants à l'école",
            ],
            VideoFormat.DEBUNK: [
                "Mythe à casser : contester c'est réservé aux riches avec un avocat",
                "Mythe à casser : ça sert à rien, on perd toujours",
                "Mythe à casser : c'est trop compliqué, faut des connaissances juridiques",
                "Mythe à casser : contester ça prend des semaines",
                "Mythe à casser : si tu contestes tu risques de payer plus cher",
                "Mythe à casser : faut se déplacer au tribunal",
                "Mythe à casser : une amende payée c'est trop tard",
            ],
            VideoFormat.CAS_REEL: [
                "Cas : excès de vitesse 137 au lieu de 130 sur l'A6",
                "Cas : feu rouge grillé de nuit, personne sur la route",
                "Cas : flashé à 54 en zone 50, amende absurde",
                "Cas : téléphone au volant, 135€ + 3 points",
                "Cas : ceinture dans un embouteillage, dénoncé par radar",
                "Cas : ligne continue franchie pour éviter un obstacle",
                "Cas : radar tronçon sur autoroute, 90€ pour 5 km/h",
            ],
            VideoFormat.SCANDALE: [
                "Angle : un conducteur qui découvre qu'il pouvait contester",
                "Angle : la frustration de payer sans savoir qu'on a le droit de contester",
                "Angle : le moment où tu reçois l'amende dans ta boîte aux lettres",
                "Angle : un ami qui te dit 'attends, paie pas tout de suite'",
                "Angle : la différence entre ceux qui paient et ceux qui contestent",
                "Angle : le réflexe que 90% des gens n'ont pas",
                "Angle : ce que personne ne t'a jamais dit sur les amendes",
                "Angle : la réaction quand on découvre qu'on peut agir",
            ],
            VideoFormat.TUTO: [
                "Angle : montrer la simplicité en 3 étapes",
                "Angle : comparer avec la galère de contester tout seul",
                "Angle : rassurer quelqu'un qui n'y connaît rien",
                "Angle : le côté instantané, comme commander un Uber",
                "Angle : la surprise de la rapidité du process",
                "Angle : même ta grand-mère pourrait le faire",
                "Angle : la différence entre avant et après NoRadar",
            ],
            VideoFormat.TEMOIGNAGE: [
                "Angle : un sceptique convaincu par le résultat",
                "Angle : quelqu'un qui a failli payer 135€ pour rien",
                "Angle : un habitué des amendes qui a enfin trouvé la solution",
                "Angle : la surprise du remboursement après contestation réussie",
                "Angle : quelqu'un qui regrette de ne pas avoir connu ça avant",
                "Angle : un conducteur avec plusieurs amendes par an",
                "Angle : la recommandation enthousiaste à un ami",
            ],
            VideoFormat.MYTHE: [
                "Mythe : contester c'est réservé aux riches",
                "Mythe : ça sert à rien, on perd toujours",
                "Mythe : c'est trop compliqué",
                "Mythe : contester ça prend des semaines",
                "Mythe : c'est pas fiable, c'est juste de l'IA",
                "Mythe : ça coûte plus cher que l'amende",
                "Mythe : il faut se déplacer au tribunal",
            ],
            VideoFormat.CHIFFRE_CHOC: [
                "Chiffre : les millions d'euros payés chaque année en amendes contestables",
                "Chiffre : le prix (34€) comparé au coût d'une amende (90-135€)",
                "Chiffre : 60 secondes pour contester",
                "Chiffre : le pourcentage de gens qui ne contestent jamais",
                "Chiffre : le nombre de points perdus chaque année en France",
                "Chiffre : le rapport coût/bénéfice de la contestation",
            ],
            VideoFormat.ULTRA_COURT: [
                "Hook percutant : commence par le prix",
                "Hook percutant : commence par la rapidité",
                "Hook percutant : commence par la garantie remboursement",
                "Hook percutant : commence par une question directe",
                "Hook percutant : commence par un constat choc",
            ],
            VideoFormat.VRAI_FAUX: [
                "Question : obligation de payer dans les 45 jours",
                "Question : risque de payer plus cher si on conteste",
                "Question : un excès de 1 km/h peut coûter des points",
                "Question : une amende payée ne peut plus être contestée",
                "Question : les radars ont une marge d'erreur obligatoire",
                "Question : le propriétaire du véhicule paie toujours",
                "Question : contester c'est réservé aux riches",
                "Question : on peut recevoir une amende sans être flashé",
            ],
        }

        max_attempts = 3
        for attempt in range(max_attempts):
            # Construction du prompt avec variation
            format_prompt = FORMAT_PROMPTS[format]
            user_prompt = f"{format_prompt}\n\n"

            # Injecter un angle aléatoire pour forcer la variabilité
            angles = ANGLE_VARIATIONS.get(format, [])
            chosen_angle = "default"
            if angles:
                chosen_angle = random.choice(angles)
                user_prompt += f"DIRECTION CRÉATIVE : {chosen_angle}\n\n"

            # Injecter un nonce unique pour buster le cache Gemini
            nonce = random.randint(10000, 99999)
            user_prompt += f"[Variation #{nonce}] "

            if theme:
                user_prompt += f"THÈME SPÉCIFIQUE : {theme}\n\n"

            if custom_instructions:
                user_prompt += f"INSTRUCTIONS ADDITIONNELLES : {custom_instructions}\n\n"

            # Injection feedback analytics (si performance.json disponible)
            from src.analytics.performance import load_performance
            perf = load_performance()
            if perf and perf.winning_themes:
                user_prompt += f"THÈMES QUI PERFORMENT CETTE SEMAINE : {', '.join(perf.winning_themes)}\n"
                if perf.losing_themes:
                    user_prompt += f"THÈMES À ÉVITER : {', '.join(perf.losing_themes)}\n"
                user_prompt += "\n"

            # Anti-doublon : lister les hooks déjà utilisés
            if self._generated_hooks:
                hooks_list = " | ".join(self._generated_hooks[-10:])
                user_prompt += f"\nATTENTION - Ces accroches ont DÉJÀ été utilisées, tu DOIS en créer une COMPLÈTEMENT DIFFÉRENTE : [{hooks_list}]\n\n"

            user_prompt += "Génère UN script au format JSON demandé. Rappel : ne JAMAIS mentionner la méthode juridique."

            console.print(f"[blue]Génération script {format.value} (angle: {chosen_angle})...[/blue]")

            try:
                response_text = self._call_claude_api(SYSTEM_PROMPT, user_prompt).strip()

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
                    thumbnail_text=data.get("thumbnail_text", {"line1": "", "line2": ""}),
                    facebook_caption=data.get("facebook_caption", ""),
                )

                # Compter TOUT le texte qui sera lu (hook + body + cta)
                full_text = f"{script.hook} {script.body} {script.cta}"
                word_count = len(full_text.split())

                MAX_WORDS = {
                    "scandale": 55,
                    "tuto": 55,
                    "temoignage": 55,
                    "mythe": 50,
                    "chiffre_choc": 45,
                    "vrai_faux": 48
                }

                max_allowed = MAX_WORDS.get(format.value, 55)

                if word_count > max_allowed:
                    # Couper le body pour respecter la limite
                    words = script.body.split()
                    target_body_words = max_allowed - len(script.hook.split()) - len(script.cta.split())
                    script.body = " ".join(words[:target_body_words])
                    console.print(f"[yellow]⚠ Script tronqué à {max_allowed} mots[/yellow]")

                # Anti-doublon : vérifier que le hook est différent
                hook_normalized = script.hook.strip().lower()
                if hook_normalized in [h.strip().lower() for h in self._generated_hooks]:
                    if attempt < max_attempts - 1:
                        console.print(f"[yellow]⚠ Hook doublon détecté, nouvelle tentative ({attempt + 2}/{max_attempts})...[/yellow]")
                        continue
                    else:
                        console.print(f"[yellow]⚠ Hook similaire après {max_attempts} tentatives, on garde quand même[/yellow]")

                # Enregistrer le hook pour anti-doublon
                self._generated_hooks.append(script.hook)

                console.print(f"[green]✓ Script généré : {script.title}[/green]")
                return script

            except json.JSONDecodeError as e:
                console.print(f"[red]Erreur parsing JSON : {e}[/red]")
                console.print(f"[dim]Réponse brute : {response_text[:500]}...[/dim]")
                raise
            except Exception as e:
                console.print(f"[red]Erreur génération : {e}[/red]")
                raise

        raise RuntimeError(f"Échec de génération après {max_attempts} tentatives")

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
