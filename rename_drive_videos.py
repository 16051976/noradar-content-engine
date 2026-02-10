#!/usr/bin/env python3
"""
Script pour renommer les vidéos NoRadar sur Google Drive avec des titres punchy
"""

import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Mapping ID → Titre punchy
TITRES = {
    "a58df527": "Contester_cest_pour_les_riches_FAUX.mp4",
    "a8de7d6d": "Jetais_hyper_sceptique.mp4",
    "dbbc1abd": "135_euros_feu_rouge_jamais_paye.mp4",
    "e47c13d4": "90_euros_conteste_par_IA.mp4",
    "46b3d1ea": "Proprietaire_paie_toujours_FAUX.mp4",
    "8dbf96ee": "Sensation_arnaque_en_payant.mp4",
    "90c157eb": "Contester_sans_prise_de_tete.mp4",
    "bbbe87ed": "Amendes_impot_cache.mp4",
    "c6f77b57": "Roi_des_amendes_jusqua_ce_que.mp4",
    "f98f6769": "99_pourcent_contestent_jamais.mp4",
    "5ef7a967": "Mission_impossible_Detrompe_toi.mp4",
    "03b6bc27": "Radars_marge_erreur_obligatoire.mp4",
    "8b4b0111": "Paye_sans_comprendre_pourquoi.mp4",
    "c744111d": "Amende_sans_etre_flashe_VRAI.mp4",
    "2114f36f": "Marre_filer_argent_Etat.mp4",
    "dfce85af": "Aurais_pu_faire_quelque_chose.mp4",
    "8302358e": "IA_pas_fiable_FAUX.mp4",
    "d678b41b": "Contester_sans_prise_tete.mp4",
    "f73bf29b": "135_balles_feu_orange.mp4",
    "4b4957e6": "Flashe_feu_rouge_conteste_60s.mp4",
    "a77126c8": "Enfer_administratif_FAUX.mp4",
    "b3b35635": "Flashe_feu_rouge_degoute.mp4",
    "2bb32cdb": "Pas_un_truc_de_juriste.mp4",
    "edac3764": "Etat_encaisse_millions_STOP.mp4",
    "a31a9836": "Deux_doigts_payer_direct.mp4",
}

def rename_videos():
    """Renomme les vidéos sur Google Drive"""

    # Charger les credentials OAuth
    token_path = Path("/workspaces/noradar-content-engine/credentials/gdrive_token.json")

    if not token_path.exists():
        print("❌ Token Google Drive introuvable")
        print(f"   Cherché dans : {token_path}")
        return

    with open(token_path) as f:
        token_data = json.load(f)

    creds = Credentials.from_authorized_user_info(token_data)
    service = build('drive', 'v3', credentials=creds)

    # Lister tous les fichiers .mp4 dans le dossier
    print("🔍 Recherche des vidéos sur Google Drive...")

    results = service.files().list(
        q="mimeType='video/mp4' and name contains 'noradar_'",
        fields="files(id, name)"
    ).execute()

    files = results.get('files', [])

    if not files:
        print("❌ Aucune vidéo trouvée sur Drive")
        return

    print(f"✅ {len(files)} vidéos trouvées\n")

    renamed = 0
    skipped = 0

    for file in files:
        file_id = file['id']
        old_name = file['name']

        # Extraire l'ID unique de la vidéo
        try:
            video_id = old_name.split('_')[-1].replace('.mp4', '')
        except:
            print(f"⚠️  Format de nom invalide : {old_name}")
            skipped += 1
            continue

        # Trouver le nouveau titre
        new_name = TITRES.get(video_id)

        if not new_name:
            print(f"⚠️  ID {video_id} non trouvé dans la table de renommage")
            skipped += 1
            continue

        # Renommer sur Drive
        try:
            service.files().update(
                fileId=file_id,
                body={'name': new_name}
            ).execute()

            print(f"✅ {old_name}")
            print(f"   → {new_name}\n")
            renamed += 1

        except Exception as e:
            print(f"❌ Erreur renommage {old_name}: {e}")
            skipped += 1

    print(f"\n{'='*60}")
    print(f"✅ {renamed} vidéos renommées")
    print(f"⚠️  {skipped} vidéos ignorées")
    print(f"{'='*60}")

if __name__ == "__main__":
    rename_videos()
