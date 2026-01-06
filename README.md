# 🎬 NoRadar Content Engine v2.0

Production automatisée de vidéos marketing pour NoRadar.

## 🎯 Objectif

Générer 30 vidéos courtes par semaine pour TikTok, Instagram Reels, YouTube Shorts, Facebook et X, avec un minimum d'effort manuel.

## 🏗️ Architecture

```
Script (Gemini) → Voix (Google TTS) → Vidéo (FFmpeg) → Google Drive → Repurpose.io
                                                                          ↓
                                                         TikTok, Reels, Shorts, FB, X
```

## 💰 Coût mensuel estimé

| Service | Coût |
|---------|------|
| Gemini Flash | Gratuit (1500 req/jour) |
| Google Cloud TTS | ~5€ |
| Repurpose.io | 25€ |
| **Total** | **~30€/mois** |

## 🚀 Installation

### 1. Cloner et installer

```bash
git clone https://github.com/your-user/noradar-content-engine.git
cd noradar-content-engine
pip install -e .
```

### 2. Configurer les credentials

```bash
cp .env.example .env
```

Éditez `.env` avec vos clés :

#### Gemini API (gratuit)
1. Allez sur https://aistudio.google.com/app/apikey
2. Créez une clé API
3. Ajoutez-la dans `GEMINI_API_KEY`

#### Google Cloud (TTS + Drive)
1. Créez un projet sur https://console.cloud.google.com
2. Activez les APIs :
   - Cloud Text-to-Speech API
   - Google Drive API
3. Créez un Service Account :
   - IAM & Admin → Service Accounts → Create
   - Téléchargez le JSON → `credentials/service-account.json`
4. Pour Google Drive OAuth :
   - APIs & Services → Credentials → Create OAuth Client ID
   - Type: Desktop App
   - Téléchargez le JSON → `credentials/gdrive_credentials.json`

### 3. Installer FFmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

### 4. Initialiser

```bash
content-engine init
```

## 📖 Usage

### Commandes principales

```bash
# Produire une vidéo
content-engine produce --format scandale
content-engine produce --format tuto --theme "contester amende stationnement"

# Générer uniquement le script (preview)
content-engine produce --format scandale --script-only

# Produire un batch
content-engine batch --count 10

# Produire une semaine complète (30 vidéos)
content-engine weekly

# Synchroniser vers Google Drive
content-engine sync

# Voir le statut
content-engine status

# Lister les voix disponibles
content-engine voices

# Nettoyer les fichiers
content-engine clean
```

### Raccourcis Makefile

```bash
make video FORMAT=scandale
make batch COUNT=10
make weekly
make sync
make status
make clean
```

## 📁 Formats de contenu

| Format | Objectif | Durée |
|--------|----------|-------|
| `scandale` | Viralité, polémique | 20-30s |
| `tuto` | Conversion, éducation | 30-45s |
| `temoignage` | Preuve sociale | 20-30s |
| `mythe` | Démystification | 25-35s |
| `chiffre_choc` | Hook rapide | 15-20s |

## 📂 Structure des outputs

```
outputs/
├── scripts/      # Scripts JSON générés
├── audio/        # Fichiers MP3 voix off
├── videos/       # Vidéos finales MP4
├── ready/        # Prêt pour Repurpose.io (synced avec GDrive)
└── uploaded/     # Déjà uploadé sur GDrive
```

## 🔄 Workflow Repurpose.io

1. Les vidéos finies sont copiées dans `outputs/ready/`
2. `content-engine sync` les upload vers Google Drive
3. Repurpose.io surveille le dossier Google Drive
4. Publication automatique vers les 5 plateformes

### Configuration Repurpose.io

1. Connectez votre Google Drive
2. Sélectionnez le dossier "NoRadar-Videos"
3. Configurez les destinations : TikTok, Instagram, YouTube, Facebook, X
4. Activez l'auto-publishing

## 🎨 Personnalisation

### Changer la voix

Dans `.env` :
```env
TTS_VOICE_NAME=fr-FR-Neural2-B  # Voix masculine Neural2
TTS_SPEAKING_RATE=1.2           # Plus rapide
```

Voix disponibles :
- `fr-FR-Wavenet-A/C` : Féminine
- `fr-FR-Wavenet-B/D` : Masculine
- `fr-FR-Neural2-A/C` : Féminine (plus naturel)
- `fr-FR-Neural2-B/D` : Masculine (plus naturel)

### Ajouter un fond personnalisé

```bash
content-engine produce --format scandale --background assets/backgrounds/dark.png
```

### Modifier les prompts

Éditez `src/scripts/generator.py` pour ajuster les prompts par format.

## 🐛 Dépannage

### "GEMINI_API_KEY non configurée"
→ Vérifiez que `.env` existe et contient votre clé

### "FFmpeg n'est pas installé"
→ `sudo apt install ffmpeg` (Linux) ou `brew install ffmpeg` (macOS)

### "Erreur Google Drive authentication"
→ Supprimez `credentials/token.pickle` et relancez pour re-authentifier

### "Quota Whisper dépassé"
→ Utilisez un modèle plus petit : éditez `SubtitleGenerator(model_size="tiny")`

## 📄 License

MIT - NoRadar 2024
