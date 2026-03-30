#!/usr/bin/env python3
"""
02_ingestion_textes.py
======================
Ingestion des commentaires Airbnb pour analyse NLP.

Fonctionnalités :
- Filtrage par quartier (Élysée)
- Regroupement des commentaires par annonce
- Nettoyage HTML
- Un fichier .txt par annonce
- Idempotence
- Gestion des erreurs robuste
"""

import re
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

import pandas as pd
from tqdm import tqdm


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    BASE_DIR = Path(__file__).parent.parent
    LISTINGS_PATH = BASE_DIR / "data/raw/tabular/listings.csv"
    REVIEWS_PATH = BASE_DIR / "data/raw/tabular/reviews.csv"
    TEXTS_DIR = BASE_DIR / "data/raw/texts"
    LOG_FILE = BASE_DIR / "scripts/ingestion_textes.log"
    
    # Filtres
    TARGET_NEIGHBOURHOOD = "Élysée"
    NEIGHBOURHOOD_COLUMN = "neighbourhood_cleansed"
    
    # Colonnes reviews
    LISTING_ID_COL = "listing_id"
    COMMENTS_COL = "comments"
    DATE_COL = "date"
    REVIEWER_COL = "reviewer_name"


# =============================================================================
# LOGGING
# =============================================================================

def setup_logging():
    """Configure le système de logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# =============================================================================
# FONCTIONS DE NETTOYAGE
# =============================================================================

def clean_html(text):
    """
    Supprime les balises HTML simples du texte.
    
    Args:
        text: Texte brut potentiellement avec HTML
        
    Returns:
        Texte nettoyé
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    
    # Remplacer <br>, <br/>, <br /> par des sauts de ligne
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    
    # Supprimer toutes les autres balises HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Décoder les entités HTML courantes
    html_entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'",
    }
    for entity, char in html_entities.items():
        text = text.replace(entity, char)
    
    # Nettoyer les espaces multiples
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    
    return text.strip()


def clean_text(text):
    """
    Nettoyage complet du texte tout en préservant l'UTF-8.
    
    Args:
        text: Texte brut
        
    Returns:
        Texte nettoyé
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    
    # Nettoyer HTML
    text = clean_html(text)
    
    # Supprimer les caractères de contrôle (sauf newline et tab)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    return text.strip()


# =============================================================================
# FONCTIONS PRINCIPALES
# =============================================================================

def load_elysee_listings():
    """
    Charge les IDs des annonces du quartier Élysée.
    
    Returns:
        set: Ensemble des listing_id du quartier Élysée
    """
    logger.info(f"📂 Chargement : {Config.LISTINGS_PATH}")
    
    if not Config.LISTINGS_PATH.exists():
        logger.error(f"❌ Fichier non trouvé : {Config.LISTINGS_PATH}")
        sys.exit(1)
    
    df = pd.read_csv(Config.LISTINGS_PATH)
    logger.info(f"   → {len(df)} annonces totales")
    
    # Filtrer par quartier
    df_elysee = df[df[Config.NEIGHBOURHOOD_COLUMN] == Config.TARGET_NEIGHBOURHOOD]
    elysee_ids = set(df_elysee['id'].tolist())
    
    logger.info(f"🎯 Quartier '{Config.TARGET_NEIGHBOURHOOD}' : {len(elysee_ids)} annonces")
    
    return elysee_ids


def load_reviews(elysee_ids):
    """
    Charge et filtre les reviews pour le quartier Élysée.
    
    Args:
        elysee_ids: Set des IDs d'annonces à conserver
        
    Returns:
        pd.DataFrame: Reviews filtrées
    """
    logger.info(f"📂 Chargement : {Config.REVIEWS_PATH}")
    
    if not Config.REVIEWS_PATH.exists():
        logger.error(f"❌ Fichier non trouvé : {Config.REVIEWS_PATH}")
        sys.exit(1)
    
    df = pd.read_csv(Config.REVIEWS_PATH)
    logger.info(f"   → {len(df)} reviews totales")
    
    # Filtrer pour ne garder que les reviews des annonces Élysée
    df_filtered = df[df[Config.LISTING_ID_COL].isin(elysee_ids)]
    logger.info(f"🎯 Reviews pour Élysée : {len(df_filtered)}")
    
    return df_filtered


def group_reviews_by_listing(df_reviews):
    """
    Regroupe les reviews par annonce.
    
    Args:
        df_reviews: DataFrame des reviews
        
    Returns:
        dict: {listing_id: [liste des reviews]}
    """
    logger.info("📊 Regroupement des reviews par annonce...")
    
    grouped = {}
    
    for listing_id in df_reviews[Config.LISTING_ID_COL].unique():
        listing_reviews = df_reviews[df_reviews[Config.LISTING_ID_COL] == listing_id]
        
        reviews_list = []
        for _, row in listing_reviews.iterrows():
            try:
                review = {
                    'date': str(row.get(Config.DATE_COL, 'N/A')),
                    'reviewer': str(row.get(Config.REVIEWER_COL, 'Anonyme')),
                    'comment': clean_text(row.get(Config.COMMENTS_COL, ''))
                }
                if review['comment']:  # Ignorer les commentaires vides
                    reviews_list.append(review)
            except Exception as e:
                logger.warning(f"⚠️ Ligne corrompue ignorée (listing {listing_id}): {e}")
                continue
        
        if reviews_list:
            grouped[listing_id] = reviews_list
    
    logger.info(f"   → {len(grouped)} annonces avec reviews valides")
    
    return grouped


def write_text_file(listing_id, reviews, overwrite=False):
    """
    Écrit un fichier .txt pour une annonce.
    
    Args:
        listing_id: ID de l'annonce
        reviews: Liste des reviews
        overwrite: Si True, écrase le fichier existant
        
    Returns:
        tuple: (success: bool, message: str)
    """
    output_path = Config.TEXTS_DIR / f"{listing_id}.txt"
    
    # Idempotence
    if output_path.exists() and not overwrite:
        return False, "skip"
    
    try:
        # Construire le contenu du fichier
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"Commentaires pour l'annonce {listing_id}")
        lines.append(f"Nombre de reviews : {len(reviews)}")
        lines.append(f"Généré le : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"{'='*60}\n")
        
        for i, review in enumerate(reviews, 1):
            lines.append(f"--- Review #{i} ---")
            lines.append(f"Date : {review['date']}")
            lines.append(f"Auteur : {review['reviewer']}")
            lines.append(f"Commentaire :")
            lines.append(f"  • {review['comment']}")
            lines.append("")  # Ligne vide entre les reviews
        
        # Écrire le fichier (UTF-8 pour préserver toutes les langues)
        content = '\n'.join(lines)
        output_path.write_text(content, encoding='utf-8')
        
        return True, "ok"
        
    except Exception as e:
        return False, f"error: {e}"


def run_ingestion(overwrite=False):
    """
    Fonction principale d'ingestion des textes.
    
    Args:
        overwrite: Si True, régénère tous les fichiers
    """
    print("\n" + "=" * 60)
    print("📝 IMMOVISION360 - INGESTION DES TEXTES")
    print("=" * 60)
    
    if overwrite:
        print("⚠️  Mode OVERWRITE activé : les fichiers existants seront écrasés")
    
    # Créer le dossier de sortie
    Config.TEXTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Charger les IDs Élysée
    elysee_ids = load_elysee_listings()
    
    if len(elysee_ids) == 0:
        logger.error("❌ Aucune annonce trouvée pour le quartier Élysée")
        return
    
    # Charger les reviews filtrées
    df_reviews = load_reviews(elysee_ids)
    
    if len(df_reviews) == 0:
        logger.warning("⚠️ Aucune review trouvée pour le quartier Élysée")
        return
    
    # Regrouper par annonce
    grouped_reviews = group_reviews_by_listing(df_reviews)
    
    # Stats
    stats = {'ok': 0, 'skip': 0, 'err': 0}
    
    print("\n" + "-" * 60)
    print("📄 CRÉATION DES FICHIERS TEXTE")
    print("-" * 60 + "\n")
    
    # Écrire les fichiers
    for listing_id, reviews in tqdm(grouped_reviews.items(), desc="Génération"):
        success, status = write_text_file(listing_id, reviews, overwrite)
        
        if status == "ok":
            stats['ok'] += 1
        elif status == "skip":
            stats['skip'] += 1
        else:
            stats['err'] += 1
            logger.warning(f"❌ Erreur pour ID {listing_id}: {status}")
    
    # Rapport final
    print("\n" + "=" * 60)
    print("📊 RAPPORT FINAL")
    print("=" * 60)
    print(f"""
    📁 Dossier : {Config.TEXTS_DIR}
    
    📈 Statistiques :
    ────────────────────────────────────
    ✅ Fichiers créés   : {stats['ok']}
    ⏭️  Ignorés (exist)  : {stats['skip']}
    ❌ Erreurs          : {stats['err']}
    ────────────────────────────────────
    
    📝 Total annonces traitées : {len(grouped_reviews)}
    💬 Total reviews traitées  : {sum(len(r) for r in grouped_reviews.values())}
    """)
    print("=" * 60)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main():
    """Point d'entrée avec gestion des arguments."""
    
    parser = argparse.ArgumentParser(
        description="Ingestion des textes Airbnb pour le Data Lake"
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Écraser les fichiers existants'
    )
    
    args = parser.parse_args()
    
    try:
        run_ingestion(overwrite=args.overwrite)
    except KeyboardInterrupt:
        print("\n\n⚠️ Interruption par l'utilisateur (Ctrl+C)")
        print("   Le script est idempotent - relancez quand vous voulez.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"❌ Erreur fatale : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()