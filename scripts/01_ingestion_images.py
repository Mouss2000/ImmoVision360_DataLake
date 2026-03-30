#!/usr/bin/env python3
"""
01_ingestion_images.py
Ingestion des images Airbnb avec respect des règles éthiques
"""

import sys
import time
from pathlib import Path
from io import BytesIO

import pandas as pd
import requests
from PIL import Image
from tqdm import tqdm


# === CONFIGURATION ===
class Config:
    BASE_DIR = Path(__file__).parent.parent
    LISTINGS_PATH = BASE_DIR / "data/raw/tabular/listings.csv"
    IMAGES_DIR = BASE_DIR / "data/raw/images"
    
    # Filtres
    TARGET_NEIGHBOURHOOD = "Élysée"
    MAX_IMAGES = None
    
    # Image
    IMAGE_SIZE = (320, 320)
    
    # Courtoisie serveur
    DELAY = 0.5
    TIMEOUT = 10
    HEADERS = {"User-Agent": "ImmoVision360/1.0 (Educational)"}


def check_ethics():
    """Confirmation éthique."""
    print("\n" + "=" * 55)
    print("⚖️  VÉRIFICATION ÉTHIQUE")
    print("=" * 55)
    print("""
    Confirmez que :
    ✓ Vous respectez le robots.txt
    ✓ Usage éducatif uniquement
    ✓ Licence Inside Airbnb respectée
    
    📖 https://insideairbnb.com/data-policies/
    """)
    
    r = input("Confirmer ? (oui/non) : ").lower()
    if r not in ['oui', 'o', 'yes', 'y']:
        print("❌ Annulé.")
        sys.exit(0)
    print("✅ OK\n")


def load_data():
    """Charge et filtre les données."""
    print(f"📂 Chargement : {Config.LISTINGS_PATH}")
    
    if not Config.LISTINGS_PATH.exists():
        print(f"❌ Fichier non trouvé !")
        print(f"   Placez listings.csv dans data/raw/tabular/")
        sys.exit(1)
    
    df = pd.read_csv(Config.LISTINGS_PATH)
    print(f"   → {len(df)} annonces")
    
    # Filtrer quartier (COLONNE CORRIGÉE)
    if Config.TARGET_NEIGHBOURHOOD:
        df = df[df['neighbourhood_cleansed'] == Config.TARGET_NEIGHBOURHOOD]
        print(f"🎯 Quartier '{Config.TARGET_NEIGHBOURHOOD}' : {len(df)}")
    
    # Limiter
    if Config.MAX_IMAGES:
        df = df.head(Config.MAX_IMAGES)
        print(f"🔢 Limite : {len(df)} images")
    
    df = df.dropna(subset=['picture_url'])
    return df[['id', 'picture_url']]


def download_image(lid, url):
    """Télécharge une image."""
    try:
        r = requests.get(url, headers=Config.HEADERS, timeout=Config.TIMEOUT)
        r.raise_for_status()
        
        img = Image.open(BytesIO(r.content))
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        img = img.resize(Config.IMAGE_SIZE, Image.Resampling.LANCZOS)
        img.save(Config.IMAGES_DIR / f"{lid}.jpg", "JPEG", quality=85)
        
        return True, "✅"
        
    except requests.exceptions.HTTPError as e:
        return False, f"❌ HTTP {e.response.status_code}"
    except requests.exceptions.Timeout:
        return False, "⏱️ Timeout"
    except Exception as e:
        return False, f"❌ {e}"


def main():
    print("\n" + "=" * 55)
    print("🚀 IMMOVISION360 - INGESTION IMAGES")
    print("=" * 55)
    
    check_ethics()
    Config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    
    df = load_data()
    if len(df) == 0:
        print("⚠️ Aucune image.")
        return
    
    stats = {'ok': 0, 'skip': 0, 'err': 0}
    
    print("\n📥 Téléchargement...\n")
    
    for _, row in tqdm(df.iterrows(), total=len(df)):
        lid = row['id']
        
        # Idempotence
        if (Config.IMAGES_DIR / f"{lid}.jpg").exists():
            stats['skip'] += 1
            continue
        
        ok, msg = download_image(lid, row['picture_url'])
        
        if ok:
            stats['ok'] += 1
        else:
            stats['err'] += 1
            print(f"   {msg} - ID {lid}")
        
        time.sleep(Config.DELAY)
    
    print("\n" + "=" * 55)
    print("📊 RÉSULTAT")
    print("=" * 55)
    print(f"""
    ✅ Téléchargées : {stats['ok']}
    ⏭️  Ignorées     : {stats['skip']}
    ❌ Erreurs      : {stats['err']}
    """)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Interrompu (Ctrl+C)")