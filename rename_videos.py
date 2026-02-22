#!/usr/bin/env python3
"""
Script pour renommer les vidéos Google Drive avec leurs titres punchy.
"""

import json
import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
SCRIPTS_DIR = Path("/workspaces/noradar-content-engine/outputs/scripts")
CREDENTIALS_PATH = Path("/workspaces/noradar-content-engine/credentials/gdrive_token.json")
FOLDER_ID = "14UcsGSOlCjAZXca5q18_G9vZxK-I7kCH"

def get_drive_service():
    """Initialise le service Google Drive."""
    creds = Credentials.from_authorized_user_file(str(CREDENTIALS_PATH))
    return build('drive', 'v3', credentials=creds)

def get_video_mapping():
    """
    Lit tous les scripts JSON et crée un mapping:
    {video_id: {title: "TitrePunchy", original_name: "noradar_format_id.mp4"}}
    """
    mapping = {}
    
    for script_file in SCRIPTS_DIR.glob("*.json"):
        with open(script_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extraire l'ID du nom de fichier (ex: "story_pov_7d9e4e9d.json" -> "7d9e4e9d")
        video_id = script_file.stem.split('_')[-1]
        format_type = script_file.stem.rsplit('_', 1)[0]  # ex: "story_pov"
        
        # Nom original de la vidéo
        original_name = f"noradar_{format_type}_{video_id}.mp4"
        
        # Titre punchy
        punchy_title = data.get('title', f'NoRadar_{video_id}')
        
        mapping[video_id] = {
            'title': punchy_title,
            'original_name': original_name,
            'format': format_type
        }
    
    return mapping

def rename_videos_in_drive(service, mapping):
    """Renomme les vidéos dans Google Drive."""
    
    # Lister tous les fichiers du dossier
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType='video/mp4'",
            fields="files(id, name)",
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        
        renamed_count = 0
        not_found = []
        
        for file in files:
            file_id = file['id']
            current_name = file['name']
            
            # Chercher dans le mapping
            found = False
            for video_id, info in mapping.items():
                if info['original_name'] == current_name:
                    # Renommer avec le titre punchy
                    new_name = f"{info['title']}.mp4"
                    
                    try:
                        service.files().update(
                            fileId=file_id,
                            body={'name': new_name}
                        ).execute()
                        
                        print(f"✅ Renommé: {current_name} → {new_name}")
                        renamed_count += 1
                        found = True
                        break
                    except HttpError as e:
                        print(f"❌ Erreur renommage {current_name}: {e}")
            
            if not found:
                not_found.append(current_name)
        
        print(f"\n{'═'*50}")
        print(f"✅ {renamed_count} vidéos renommées")
        if not_found:
            print(f"⚠️  {len(not_found)} vidéos non trouvées dans les scripts:")
            for name in not_found:
                print(f"   - {name}")
    
    except HttpError as e:
        print(f"❌ Erreur accès Google Drive: {e}")

def main():
    print("🔄 Démarrage du renommage des vidéos...")
    print(f"📁 Dossier scripts: {SCRIPTS_DIR}")
    print(f"🔑 Credentials: {CREDENTIALS_PATH}")
    print(f"📂 Dossier Drive: {FOLDER_ID}\n")
    
    # Récupérer le mapping
    mapping = get_video_mapping()
    print(f"📊 {len(mapping)} scripts trouvés\n")
    
    # Connexion à Google Drive
    service = get_drive_service()
    
    # Renommer les vidéos
    rename_videos_in_drive(service, mapping)

if __name__ == "__main__":
    main()
