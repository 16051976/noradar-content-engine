# 🎬 NoRadar Content Engine v2.1

Moteur de production automatisé de vidéos courtes pour TikTok, Instagram Reels, YouTube Shorts.

## ✨ Fonctionnalités

- **Scripts IA** : Génération automatique via Gemini (5 formats : scandale, tuto, temoignage, mythe, chiffre_choc)
- **Voix naturelle** : Google Cloud Text-to-Speech (voix Wavenet française)
- **Vidéos de fond** : Téléchargement automatique depuis Pexels (gratuit, HD)
- **Sous-titres TikTok** : Style viral avec couleurs alternées, gros texte centré
- **Format vertical** : 1080x1920 optimisé pour mobile

## 🚀 Installation rapide

```bash
# Cloner et installer
cd noradar-content-engine
./setup.sh

# Ou manuellement
python -m venv venv
source venv/bin/activate
pip install -e .
```

## ⚙️ Configuration

1. **Copier le fichier .env** :
```bash
cp .env.example .env
```

2. **Configurer les clés API** :

| Variable | Description | Où l'obtenir |
|----------|-------------|--------------|
| `GEMINI_API_KEY` | Scripts IA | [Google AI Studio](https://aistudio.google.com/app/apikey) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Voix TTS | Google Cloud Console → Service Account |
| `PEXELS_API_KEY` | Vidéos de fond | [Pexels API](https://www.pexels.com/api/) (gratuit) |

### Obtenir une clé Pexels (gratuit)

1. Va sur https://www.pexels.com/api/
2. Clique "Get Started" et crée un compte
3. Copie ta clé API dans `.env`

## 📺 Utilisation

### Générer une vidéo complète

```bash
source venv/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account.json

# Une vidéo format "scandale"
content-engine produce --format scandale --no-upload

# Une vidéo format "tuto"
content-engine produce --format tuto --no-upload

# Seulement le script (sans vidéo)
content-engine produce --format temoignage --script-only
```

### Formats disponibles

| Format | Description | Ton |
|--------|-------------|-----|
| `scandale` | Indignation, injustice | Énervé, révoltant |
| `tuto` | Comment contester | Pédagogique, clair |
| `temoignage` | Success story client | Personnel, authentique |
| `mythe` | Casser les idées reçues | Surprenant |
| `chiffre_choc` | Stats choquantes | Impactant |

### Production en batch

```bash
# 5 vidéos (distribution automatique)
content-engine batch --count 5 --no-upload

# Production hebdomadaire (30 vidéos)
content-engine weekly --no-upload
```

## 📁 Structure des outputs

```
outputs/
├── scripts/     # Scripts JSON générés
├── audio/       # Fichiers MP3 (voix)
├── subtitles/   # Fichiers SRT + ASS
├── videos/      # Vidéos finales MP4
└── ready/       # Prêt pour upload
```

## 🎨 Qualité vidéo

- **Résolution** : 1080x1920 (vertical)
- **FPS** : 30
- **Codec** : H.264 (libx264)
- **Audio** : AAC 192kbps
- **Sous-titres** : Style TikTok (gros, centrés, couleurs)

## 🔧 Dépannage

### "PEXELS_API_KEY non configuré"
→ Ajoute ta clé Pexels dans `.env` (ou utilise le fond dégradé par défaut)

### "FFmpeg n'est pas installé"
```bash
sudo apt install ffmpeg
```

### "DefaultCredentialsError"
```bash
export GOOGLE_APPLICATION_CREDENTIALS=credentials/service-account.json
```

## 📊 Coûts estimés

| Service | Coût |
|---------|------|
| Gemini API | Gratuit (quota généreux) |
| Google TTS | ~0.016€/vidéo (Wavenet) |
| Pexels | Gratuit |
| **Total** | ~0.50€ pour 30 vidéos/semaine |

## 🔜 Roadmap

- [ ] Google Drive sync automatique
- [ ] Repurpose.io integration
- [ ] Thumbnails automatiques
- [ ] Analytics tracking

---

**NoRadar** - Contestez vos amendes en 2 minutes 🚗
