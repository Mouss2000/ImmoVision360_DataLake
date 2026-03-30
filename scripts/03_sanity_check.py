#!/usr/bin/env python3
"""
03_sanity_check.py
==================
Audit complet du Data Lake ImmoVision360.

Vérifie :
- Cohérence du périmètre Élysée
- Intégrité des images (comptage, jointure, orphelins)
- Intégrité des textes (comptage, jointure, orphelins)
- Cohérence croisée images/textes
- Validation des fichiers (corruption, taille)

Auteur: [Votre Nom]
Date: 2024
"""

import sys
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
from PIL import Image
from tqdm import tqdm


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    BASE_DIR = Path(__file__).parent.parent
    LISTINGS_PATH = BASE_DIR / "data/raw/tabular/listings.csv"
    REVIEWS_PATH = BASE_DIR / "data/raw/tabular/reviews.csv"
    IMAGES_DIR = BASE_DIR / "data/raw/images"
    TEXTS_DIR = BASE_DIR / "data/raw/texts"
    
    # Filtres (doivent correspondre aux scripts 1 et 2)
    TARGET_NEIGHBOURHOOD = "Élysée"
    NEIGHBOURHOOD_COLUMN = "neighbourhood_cleansed"
    
    # Paramètres de validation
    MIN_IMAGE_SIZE_BYTES = 1000  # Image < 1KB = probablement corrompue
    MIN_TEXT_SIZE_BYTES = 10     # Fichier texte < 10 bytes = probablement vide
    EXPECTED_IMAGE_SIZE = (320, 320)  # Taille attendue des images


# =============================================================================
# FONCTIONS DE CHARGEMENT
# =============================================================================

def load_elysee_reference():
    """
    Charge la liste de référence des IDs du périmètre Élysée.
    
    Returns:
        set: Ensemble des listing_id du quartier Élysée
    """
    if not Config.LISTINGS_PATH.exists():
        print(f"❌ Fichier non trouvé : {Config.LISTINGS_PATH}")
        sys.exit(1)
    
    df = pd.read_csv(Config.LISTINGS_PATH)
    df_elysee = df[df[Config.NEIGHBOURHOOD_COLUMN] == Config.TARGET_NEIGHBOURHOOD]
    
    return set(df_elysee['id'].tolist()), len(df)


def load_reviews_reference(elysee_ids):
    """
    Charge les IDs ayant au moins une review.
    
    Args:
        elysee_ids: Set des IDs Élysée
        
    Returns:
        set: IDs avec au moins une review
    """
    if not Config.REVIEWS_PATH.exists():
        return set()
    
    df = pd.read_csv(Config.REVIEWS_PATH)
    df_elysee = df[df['listing_id'].isin(elysee_ids)]
    
    return set(df_elysee['listing_id'].unique())


# =============================================================================
# FONCTIONS DE VÉRIFICATION
# =============================================================================

def check_structure():
    """Vérifie la structure des dossiers."""
    
    print("\n" + "=" * 70)
    print("📂 VÉRIFICATION DE LA STRUCTURE")
    print("=" * 70)
    
    required_dirs = [
        "data/raw/tabular",
        "data/raw/images",
        "data/raw/texts",
        "scripts"
    ]
    
    required_files = [
        "data/raw/tabular/listings.csv",
        "data/raw/tabular/reviews.csv"
    ]
    
    results = {'dirs': True, 'files': True}
    
    print("\n📁 Dossiers :")
    for d in required_dirs:
        path = Config.BASE_DIR / d
        if path.exists():
            print(f"   ✅ /{d}")
        else:
            print(f"   ❌ /{d} - MANQUANT")
            results['dirs'] = False
    
    print("\n📄 Fichiers requis :")
    for f in required_files:
        path = Config.BASE_DIR / f
        if path.exists():
            size = path.stat().st_size
            print(f"   ✅ {f} ({size:,} bytes)")
        else:
            print(f"   ❌ {f} - MANQUANT")
            results['files'] = False
    
    return results


def check_images(elysee_ids):
    """
    Vérifie l'intégrité des images.
    
    Args:
        elysee_ids: Set des IDs de référence
        
    Returns:
        dict: Résultats de l'audit images
    """
    print("\n" + "=" * 70)
    print("🖼️  AUDIT DES IMAGES")
    print("=" * 70)
    
    results = {
        'expected': len(elysee_ids),
        'found': 0,
        'valid': 0,
        'corrupted': [],
        'wrong_size': [],
        'missing': [],
        'orphans': []
    }
    
    # Comptage physique
    if not Config.IMAGES_DIR.exists():
        print(f"   ❌ Dossier images non trouvé : {Config.IMAGES_DIR}")
        results['missing'] = list(elysee_ids)
        return results
    
    image_files = list(Config.IMAGES_DIR.glob("*.jpg"))
    results['found'] = len(image_files)
    
    # Extraire les IDs des images présentes
    image_ids = set()
    for img_path in image_files:
        try:
            img_id = int(img_path.stem)
            image_ids.add(img_id)
        except ValueError:
            pass
    
    # Vérifier les images manquantes
    results['missing'] = list(elysee_ids - image_ids)
    
    # Vérifier les images orphelines (pas dans la référence)
    results['orphans'] = list(image_ids - elysee_ids)
    
    # Validation des images existantes
    print("\n   🔍 Validation des fichiers images...")
    for img_path in tqdm(image_files, desc="   Vérification", leave=False):
        try:
            # Vérifier la taille du fichier
            if img_path.stat().st_size < Config.MIN_IMAGE_SIZE_BYTES:
                results['corrupted'].append(img_path.stem)
                continue
            
            # Vérifier l'intégrité de l'image
            with Image.open(img_path) as img:
                img.verify()
            
            # Rouvrir pour vérifier les dimensions
            with Image.open(img_path) as img:
                if img.size != Config.EXPECTED_IMAGE_SIZE:
                    results['wrong_size'].append(img_path.stem)
                else:
                    results['valid'] += 1
                    
        except Exception as e:
            results['corrupted'].append(img_path.stem)
    
    # Affichage des résultats
    print(f"\n   📊 Comptages :")
    print(f"      • Attendues (périmètre Élysée) : {results['expected']}")
    print(f"      • Présentes sur disque         : {results['found']}")
    print(f"      • Valides (320x320)            : {results['valid']}")
    
    completion = (results['found'] / results['expected'] * 100) if results['expected'] > 0 else 0
    print(f"\n   📈 Taux de complétion : {completion:.1f}%")
    
    if results['corrupted']:
        print(f"\n   ⚠️ Images corrompues ({len(results['corrupted'])}) :")
        for img_id in results['corrupted'][:5]:
            print(f"      - {img_id}.jpg")
        if len(results['corrupted']) > 5:
            print(f"      ... et {len(results['corrupted']) - 5} autres")
    
    if results['wrong_size']:
        print(f"\n   ⚠️ Taille incorrecte ({len(results['wrong_size'])}) :")
        for img_id in results['wrong_size'][:5]:
            print(f"      - {img_id}.jpg")
        if len(results['wrong_size']) > 5:
            print(f"      ... et {len(results['wrong_size']) - 5} autres")
    
    if results['missing']:
        print(f"\n   ❌ Images manquantes ({len(results['missing'])}) :")
        for img_id in results['missing'][:5]:
            print(f"      - {img_id}.jpg")
        if len(results['missing']) > 5:
            print(f"      ... et {len(results['missing']) - 5} autres")
    
    if results['orphans']:
        print(f"\n   👻 Images orphelines ({len(results['orphans'])}) :")
        print(f"      (présentes mais hors périmètre Élysée)")
        for img_id in results['orphans'][:5]:
            print(f"      - {img_id}.jpg")
        if len(results['orphans']) > 5:
            print(f"      ... et {len(results['orphans']) - 5} autres")
    
    return results


def check_texts(elysee_ids, ids_with_reviews):
    """
    Vérifie l'intégrité des fichiers texte.
    
    Args:
        elysee_ids: Set des IDs de référence
        ids_with_reviews: Set des IDs ayant des reviews
        
    Returns:
        dict: Résultats de l'audit textes
    """
    print("\n" + "=" * 70)
    print("📝 AUDIT DES TEXTES")
    print("=" * 70)
    
    # Le nombre attendu = IDs Élysée avec au moins une review
    expected_ids = elysee_ids & ids_with_reviews
    
    results = {
        'expected': len(expected_ids),
        'found': 0,
        'valid': 0,
        'empty': [],
        'corrupted': [],
        'missing': [],
        'orphans': []
    }
    
    # Comptage physique
    if not Config.TEXTS_DIR.exists():
        print(f"   ❌ Dossier textes non trouvé : {Config.TEXTS_DIR}")
        results['missing'] = list(expected_ids)
        return results
    
    text_files = list(Config.TEXTS_DIR.glob("*.txt"))
    results['found'] = len(text_files)
    
    # Extraire les IDs des fichiers présents
    text_ids = set()
    for txt_path in text_files:
        try:
            txt_id = int(txt_path.stem)
            text_ids.add(txt_id)
        except ValueError:
            pass
    
    # Vérifier les fichiers manquants
    results['missing'] = list(expected_ids - text_ids)
    
    # Vérifier les fichiers orphelins
    results['orphans'] = list(text_ids - expected_ids)
    
    # Validation des fichiers existants
    print("\n   🔍 Validation des fichiers texte...")
    for txt_path in tqdm(text_files, desc="   Vérification", leave=False):
        try:
            size = txt_path.stat().st_size
            
            if size < Config.MIN_TEXT_SIZE_BYTES:
                results['empty'].append(txt_path.stem)
                continue
            
            # Vérifier que le fichier est lisible (UTF-8)
            content = txt_path.read_text(encoding='utf-8')
            
            # Vérifier le format attendu
            if "Commentaires pour l'annonce" in content:
                results['valid'] += 1
            else:
                results['corrupted'].append(txt_path.stem)
                
        except UnicodeDecodeError:
            results['corrupted'].append(txt_path.stem)
        except Exception as e:
            results['corrupted'].append(txt_path.stem)
    
    # Affichage des résultats
    print(f"\n   📊 Comptages :")
    print(f"      • Attendus (Élysée + reviews)  : {results['expected']}")
    print(f"      • Présents sur disque          : {results['found']}")
    print(f"      • Valides (format correct)     : {results['valid']}")
    
    completion = (results['found'] / results['expected'] * 100) if results['expected'] > 0 else 0
    print(f"\n   📈 Taux de complétion : {completion:.1f}%")
    
    if results['empty']:
        print(f"\n   ⚠️ Fichiers vides ({len(results['empty'])}) :")
        for txt_id in results['empty'][:5]:
            print(f"      - {txt_id}.txt")
        if len(results['empty']) > 5:
            print(f"      ... et {len(results['empty']) - 5} autres")
    
    if results['corrupted']:
        print(f"\n   ⚠️ Fichiers corrompus ({len(results['corrupted'])}) :")
        for txt_id in results['corrupted'][:5]:
            print(f"      - {txt_id}.txt")
        if len(results['corrupted']) > 5:
            print(f"      ... et {len(results['corrupted']) - 5} autres")
    
    if results['missing']:
        print(f"\n   ❌ Fichiers manquants ({len(results['missing'])}) :")
        for txt_id in results['missing'][:5]:
            print(f"      - {txt_id}.txt")
        if len(results['missing']) > 5:
            print(f"      ... et {len(results['missing']) - 5} autres")
    
    if results['orphans']:
        print(f"\n   👻 Fichiers orphelins ({len(results['orphans'])}) :")
        for txt_id in results['orphans'][:5]:
            print(f"      - {txt_id}.txt")
        if len(results['orphans']) > 5:
            print(f"      ... et {len(results['orphans']) - 5} autres")
    
    return results


def check_cross_consistency(image_results, text_results):
    """
    Vérifie la cohérence croisée entre images et textes.
    
    Args:
        image_results: Résultats de l'audit images
        text_results: Résultats de l'audit textes
        
    Returns:
        dict: Résultats de cohérence croisée
    """
    print("\n" + "=" * 70)
    print("🔗 COHÉRENCE CROISÉE IMAGES / TEXTES")
    print("=" * 70)
    
    # Récupérer les IDs présents
    image_ids = set()
    for img_path in Config.IMAGES_DIR.glob("*.jpg"):
        try:
            image_ids.add(int(img_path.stem))
        except ValueError:
            pass
    
    text_ids = set()
    for txt_path in Config.TEXTS_DIR.glob("*.txt"):
        try:
            text_ids.add(int(txt_path.stem))
        except ValueError:
            pass
    
    # Analyse croisée
    both = image_ids & text_ids
    image_only = image_ids - text_ids
    text_only = text_ids - image_ids
    
    results = {
        'both': len(both),
        'image_only': list(image_only),
        'text_only': list(text_only)
    }
    
    print(f"\n   📊 Statistiques :")
    print(f"      • IDs avec image ET texte : {len(both)}")
    print(f"      • IDs avec image SANS texte : {len(image_only)}")
    print(f"      • IDs avec texte SANS image : {len(text_only)}")
    
    if image_only:
        print(f"\n   🖼️ Images sans texte associé ({len(image_only)}) :")
        for img_id in sorted(image_only)[:5]:
            print(f"      - {img_id}")
        if len(image_only) > 5:
            print(f"      ... et {len(image_only) - 5} autres")
    
    if text_only:
        print(f"\n   📝 Textes sans image associée ({len(text_only)}) :")
        for txt_id in sorted(text_only)[:5]:
            print(f"      - {txt_id}")
        if len(text_only) > 5:
            print(f"      ... et {len(text_only) - 5} autres")
    
    if not image_only and not text_only:
        print(f"\n   ✅ Parfaite cohérence : tous les IDs ont image ET texte")
    
    return results


def print_final_report(structure_results, image_results, text_results, cross_results, total_listings, elysee_count):
    """Affiche le rapport final."""
    
    print("\n" + "=" * 70)
    print("📋 RAPPORT FINAL - SANITY CHECK")
    print("=" * 70)
    print(f"""
    🗓️  Date du rapport : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    ═══════════════════════════════════════════════════════════════════
    📍 PÉRIMÈTRE
    ═══════════════════════════════════════════════════════════════════
    • Quartier ciblé         : {Config.TARGET_NEIGHBOURHOOD}
    • Total annonces Paris   : {total_listings:,}
    • Annonces Élysée        : {elysee_count:,}
    
    ═══════════════════════════════════════════════════════════════════
    🖼️  IMAGES
    ═══════════════════════════════════════════════════════════════════
    • Attendues              : {image_results['expected']:,}
    • Présentes              : {image_results['found']:,}
    • Valides                : {image_results['valid']:,}
    • Taux de complétion     : {(image_results['found']/image_results['expected']*100) if image_results['expected'] > 0 else 0:.1f}%
    • Corrompues             : {len(image_results['corrupted'])}
    • Taille incorrecte      : {len(image_results['wrong_size'])}
    • Manquantes             : {len(image_results['missing'])}
    • Orphelines             : {len(image_results['orphans'])}
    
    ═══════════════════════════════════════════════════════════════════
    📝 TEXTES
    ═══════════════════════════════════════════════════════════════════
    • Attendus               : {text_results['expected']:,}
    • Présents               : {text_results['found']:,}
    • Valides                : {text_results['valid']:,}
    • Taux de complétion     : {(text_results['found']/text_results['expected']*100) if text_results['expected'] > 0 else 0:.1f}%
    • Vides                  : {len(text_results['empty'])}
    • Corrompus              : {len(text_results['corrupted'])}
    • Manquants              : {len(text_results['missing'])}
    • Orphelins              : {len(text_results['orphans'])}
    
    ═══════════════════════════════════════════════════════════════════
    🔗 COHÉRENCE CROISÉE
    ═══════════════════════════════════════════════════════════════════
    • IDs complets (img+txt) : {cross_results['both']:,}
    • Images sans texte      : {len(cross_results['image_only'])}
    • Textes sans image      : {len(cross_results['text_only'])}
    """)
    
    # Verdict final
    print("═══════════════════════════════════════════════════════════════════")
    print("🏁 VERDICT FINAL")
    print("═══════════════════════════════════════════════════════════════════")
    
    issues = []
    
    if not structure_results['dirs'] or not structure_results['files']:
        issues.append("Structure du projet incomplète")
    if len(image_results['corrupted']) > 0:
        issues.append(f"{len(image_results['corrupted'])} images corrompues")
    if len(image_results['missing']) > 0:
        issues.append(f"{len(image_results['missing'])} images manquantes")
    if len(text_results['corrupted']) > 0:
        issues.append(f"{len(text_results['corrupted'])} fichiers texte corrompus")
    if len(text_results['missing']) > 0:
        issues.append(f"{len(text_results['missing'])} fichiers texte manquants")
    if len(cross_results['image_only']) > 0:
        issues.append(f"{len(cross_results['image_only'])} images sans texte")
    if len(cross_results['text_only']) > 0:
        issues.append(f"{len(cross_results['text_only'])} textes sans image")
    
    if not issues:
        print("""
    ✅ SUCCÈS : Le Data Lake est complet et cohérent !
    
    Tous les fichiers sont présents, valides et alignés.
    Vous pouvez passer à la Phase 2 (IA Vision / NLP).
        """)
        return 0
    else:
        print(f"""
    ⚠️ ATTENTION : {len(issues)} problème(s) détecté(s)
        """)
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")
        print("""
    
    Recommandations :
    • Relancez les scripts d'ingestion si des fichiers manquent
    • Vérifiez les fichiers corrompus manuellement
    • Consultez les logs pour plus de détails
        """)
        return 1


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main():
    """Fonction principale du sanity check."""
    
    print("\n" + "=" * 70)
    print("🔍 IMMOVISION360 - SANITY CHECK")
    print("=" * 70)
    print("   Audit complet du Data Lake")
    print("=" * 70)
    
    # 1. Vérification structure
    structure_results = check_structure()
    
    # 2. Charger la référence
    print("\n" + "=" * 70)
    print("📊 CHARGEMENT DE LA RÉFÉRENCE")
    print("=" * 70)
    
    elysee_ids, total_listings = load_elysee_reference()
    ids_with_reviews = load_reviews_reference(elysee_ids)
    
    print(f"\n   📍 Périmètre : {Config.TARGET_NEIGHBOURHOOD}")
    print(f"   📊 Annonces totales Paris : {total_listings:,}")
    print(f"   🎯 Annonces Élysée : {len(elysee_ids):,}")
    print(f"   💬 Annonces avec reviews : {len(ids_with_reviews):,}")
    
    # 3. Audit images
    image_results = check_images(elysee_ids)
    
    # 4. Audit textes
    text_results = check_texts(elysee_ids, ids_with_reviews)
    
    # 5. Cohérence croisée
    cross_results = check_cross_consistency(image_results, text_results)
    
    # 6. Rapport final
    exit_code = print_final_report(
        structure_results,
        image_results,
        text_results,
        cross_results,
        total_listings,
        len(elysee_ids)
    )
    
    print("=" * 70 + "\n")
    
    return exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interruption par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale : {e}")
        sys.exit(1)