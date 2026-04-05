#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_transform.py - Data Transformation & AI Feature Engineering

This script transforms filtered_elysee.csv into a clean, AI-enriched dataset:
1. Data cleaning (NaN handling for available columns)
2. AI Feature Engineering:
   - Standardization_Score (from images via Gemini Vision)
   - Neighborhood_Impact (from texts via Gemini NLP)

Note: Price column is 100% NaN in source data - documented in README_DATAPROFILING.md

Author: ImmoVision 360 Team
Phase: 2 - ETL Pipeline (Transform)
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

# Load environment variables
from dotenv import load_dotenv

# Get project root and load .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# For Gemini API
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. Run: pip install google-generativeai")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow not installed. Run: pip install Pillow")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
IMAGES_DIR = DATA_RAW / "images"
TEXTS_DIR = DATA_RAW / "texts"

# Files
INPUT_FILE = DATA_PROCESSED / "filtered_elysee.csv"
OUTPUT_FILE = DATA_PROCESSED / "transformed_elysee.csv"
CHECKPOINT_FILE = DATA_PROCESSED / "transform_checkpoint.csv"

# Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"

# Processing Configuration
CHECKPOINT_INTERVAL = 25
MAX_RETRIES = 3
INITIAL_BACKOFF = 60
RATE_LIMIT_DELAY = 5

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging with timestamps."""
    log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# DATA CLEANING FUNCTIONS
# =============================================================================

def apply_cleaning_rules(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply cleaning and transformation rules.
    Focuses on columns that have data (skips price since it's 100% NaN).
    """
    logger.info("\n" + "="*60)
    logger.info("PHASE 1: DATA CLEANING")
    logger.info("="*60)
    
    initial_rows = len(df)
    df = df.copy()
    
    logger.info(f"\n  Initial dataset: {initial_rows} rows × {len(df.columns)} columns")
    
    # -------------------------------------------------------------------------
    # 1. PRICE - 100% NaN in source, just document and skip
    # -------------------------------------------------------------------------
    if 'price' in df.columns:
        nan_count = df['price'].isna().sum()
        logger.info(f"\n  price: {nan_count}/{len(df)} NaN ({nan_count/len(df)*100:.1f}%)")
        if nan_count == len(df):
            logger.info("    → Column is 100% empty (source data issue)")
            logger.info("    → Decision: Keep column, document in README_DATAPROFILING.md")
    
    # -------------------------------------------------------------------------
    # 2. HOST_RESPONSE_RATE - Convert % string to float, impute with median
    # -------------------------------------------------------------------------
    if 'host_response_rate' in df.columns:
        # Convert string percentages to float
        df['host_response_rate'] = df['host_response_rate'].astype(str).str.replace('%', '')
        df['host_response_rate'] = pd.to_numeric(df['host_response_rate'], errors='coerce')
        
        nan_count = df['host_response_rate'].isna().sum()
        valid_count = df['host_response_rate'].notna().sum()
        
        if valid_count > 0:
            median_rate = df['host_response_rate'].median()
            df['host_response_rate'] = df['host_response_rate'].fillna(median_rate)
            logger.info(f"\n  host_response_rate: {nan_count} NaN → imputed with median ({median_rate:.1f})")
        else:
            df['host_response_rate'] = df['host_response_rate'].fillna(0)
            logger.info(f"\n  host_response_rate: all NaN → filled with 0")
    
    # -------------------------------------------------------------------------
    # 3. HOST_RESPONSE_TIME - Categorical, impute with 'unknown'
    # -------------------------------------------------------------------------
    if 'host_response_time' in df.columns:
        nan_count = df['host_response_time'].isna().sum()
        df['host_response_time'] = df['host_response_time'].fillna('unknown')
        logger.info(f"\n  host_response_time: {nan_count} NaN → 'unknown'")
    
    # -------------------------------------------------------------------------
    # 4. REVIEWS_PER_MONTH - Logical imputation: 0 means new/no reviews
    # -------------------------------------------------------------------------
    if 'reviews_per_month' in df.columns:
        nan_count = df['reviews_per_month'].isna().sum()
        df['reviews_per_month'] = pd.to_numeric(df['reviews_per_month'], errors='coerce').fillna(0)
        logger.info(f"\n  reviews_per_month: {nan_count} NaN → 0 (new listings)")
    
    # -------------------------------------------------------------------------
    # 5. NUMBER_OF_REVIEWS - Same logic
    # -------------------------------------------------------------------------
    if 'number_of_reviews' in df.columns:
        nan_count = df['number_of_reviews'].isna().sum()
        df['number_of_reviews'] = pd.to_numeric(df['number_of_reviews'], errors='coerce').fillna(0)
        logger.info(f"\n  number_of_reviews: {nan_count} NaN → 0")
    
    # -------------------------------------------------------------------------
    # 6. AVAILABILITY_365 - Impute with 0 (fully booked)
    # -------------------------------------------------------------------------
    if 'availability_365' in df.columns:
        nan_count = df['availability_365'].isna().sum()
        df['availability_365'] = pd.to_numeric(df['availability_365'], errors='coerce').fillna(0)
        logger.info(f"\n  availability_365: {nan_count} NaN → 0")
    
    # -------------------------------------------------------------------------
    # 7. MINIMUM_NIGHTS - Impute with 1 (default minimum)
    # -------------------------------------------------------------------------
    if 'minimum_nights' in df.columns:
        nan_count = df['minimum_nights'].isna().sum()
        df['minimum_nights'] = pd.to_numeric(df['minimum_nights'], errors='coerce').fillna(1)
        
        # Cap extreme values at 365
        extreme = df['minimum_nights'] > 365
        if extreme.sum() > 0:
            df.loc[extreme, 'minimum_nights'] = 365
            logger.info(f"\n  minimum_nights: {nan_count} NaN → 1, capped {extreme.sum()} values at 365")
        else:
            logger.info(f"\n  minimum_nights: {nan_count} NaN → 1")
    
    # -------------------------------------------------------------------------
    # 8. CALCULATED_HOST_LISTINGS_COUNT - Impute with median
    # -------------------------------------------------------------------------
    if 'calculated_host_listings_count' in df.columns:
        nan_count = df['calculated_host_listings_count'].isna().sum()
        df['calculated_host_listings_count'] = pd.to_numeric(
            df['calculated_host_listings_count'], errors='coerce'
        )
        median = df['calculated_host_listings_count'].median()
        if pd.isna(median):
            median = 1
        df['calculated_host_listings_count'] = df['calculated_host_listings_count'].fillna(median)
        logger.info(f"\n  calculated_host_listings_count: {nan_count} NaN → median ({median:.0f})")
    
    # -------------------------------------------------------------------------
    # 9. LICENSE - Impute with 'Not provided'
    # -------------------------------------------------------------------------
    if 'license' in df.columns:
        nan_count = df['license'].isna().sum()
        df['license'] = df['license'].fillna('Not provided')
        logger.info(f"\n  license: {nan_count} NaN → 'Not provided'")
    
    # -------------------------------------------------------------------------
    # 10. LAST_REVIEW - Keep as-is (date, NaN means never reviewed)
    # -------------------------------------------------------------------------
    if 'last_review' in df.columns:
        nan_count = df['last_review'].isna().sum()
        logger.info(f"\n  last_review: {nan_count} NaN → kept as NaN (no reviews yet)")
    
    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------
    final_rows = len(df)
    logger.info(f"\n  " + "="*50)
    logger.info(f"  📊 Cleaning Summary: {initial_rows} → {final_rows} rows (0 removed)")
    logger.info(f"  " + "="*50)
    
    return df


# =============================================================================
# GEMINI API FUNCTIONS
# =============================================================================

def initialize_gemini() -> Optional[object]:
    """Initialize Gemini model."""
    if not GEMINI_AVAILABLE:
        logger.error("❌ Gemini library not available!")
        return None
    
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not set in .env file!")
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        logger.info(f"  Testing connection to {GEMINI_MODEL}...")
        response = model.generate_content("Say 'OK'")
        
        if response.text:
            logger.info(f"✓ Gemini model initialized: {GEMINI_MODEL}")
            return model
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini: {e}")
        
        # Try fallback
        for fallback in ["gemini-2.0-flash-lite", "gemini-2.0-flash"]:
            try:
                logger.info(f"  Trying fallback: {fallback}...")
                model = genai.GenerativeModel(fallback)
                response = model.generate_content("Say 'OK'")
                if response.text:
                    logger.info(f"✓ Fallback: {fallback}")
                    return model
            except:
                continue
    
    return None


def classify_image(image_path: Path, model, max_retries: int = MAX_RETRIES) -> int:
    """
    Classify an image using Gemini Vision API.
    
    Returns:
        1 = Appartement industrialisé (standardized, Airbnb-style)
        0 = Appartement personnel (lived-in, personal)
       -1 = Autre / Error
    """
    prompt = """Analyse cette image et classifie-la strictement dans l'une de ces catégories :
- 'Appartement industrialisé' (Déco minimaliste, style catalogue, standardisé, froid)
- 'Appartement personnel' (Objets de vie, livres, décoration hétéroclite, chaleureux)
- 'Autre' (Si l'image ne montre pas l'intérieur d'un logement)

Réponds uniquement par le nom de la catégorie."""
    
    if not image_path.exists():
        return -1
    
    for attempt in range(max_retries):
        try:
            img = Image.open(image_path)
            
            # Resize if too large
            max_size = 512
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            response = model.generate_content([prompt, img])
            result = response.text.strip().lower()
            
            if 'industrialisé' in result or 'industrialise' in result:
                return 1
            elif 'personnel' in result:
                return 0
            else:
                return -1
                
        except google_exceptions.ResourceExhausted:
            wait_time = INITIAL_BACKOFF * (2 ** attempt)
            logger.warning(f"    ⏳ Quota exceeded. Waiting {wait_time}s...")
            time.sleep(wait_time)
            
        except google_exceptions.InvalidArgument:
            logger.warning(f"    ⚠️ Invalid image: {image_path.name}")
            return -1
            
        except Exception as e:
            logger.warning(f"    ⚠️ Attempt {attempt + 1} failed: {str(e)[:80]}")
            time.sleep(2 ** attempt)
    
    return -1


def classify_text(text_path: Path, model, max_retries: int = MAX_RETRIES) -> int:
    """
    Classify review text using Gemini NLP.
    
    Returns:
        1 = Hôtélisé (hotel-like, impersonal)
        0 = Voisinage naturel (authentic, personal)
       -1 = Autre / Error
    """
    prompt = """Analyse ces commentaires de voyageurs Airbnb et classe le type d'expérience :
- 'Hôtélisé' (boîte à clés, consignes professionnelles, peu de contact humain)
- 'Voisinage naturel' (rencontre avec l'hôte, conseils de quartier, vie locale)
- 'Autre' (commentaires insuffisants ou hors sujet)

Réponds uniquement par le nom de la catégorie.

COMMENTAIRES:
"""
    
    if not text_path.exists():
        return -1
    
    try:
        with open(text_path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        
        if len(text_content.strip()) < 50:
            return -1
        
        # Truncate if too long
        if len(text_content) > 8000:
            text_content = text_content[:8000] + "\n[...]"
            
    except Exception as e:
        logger.warning(f"    ⚠️ Error reading {text_path.name}: {e}")
        return -1
    
    for attempt in range(max_retries):
        try:
            full_prompt = prompt + text_content
            response = model.generate_content(full_prompt)
            result = response.text.strip().lower()
            
            if 'hôtélisé' in result or 'hotelise' in result:
                return 1
            elif 'voisinage' in result or 'naturel' in result:
                return 0
            else:
                return -1
                
        except google_exceptions.ResourceExhausted:
            wait_time = INITIAL_BACKOFF * (2 ** attempt)
            logger.warning(f"    ⏳ Quota exceeded. Waiting {wait_time}s...")
            time.sleep(wait_time)
            
        except Exception as e:
            logger.warning(f"    ⚠️ Attempt {attempt + 1} failed: {str(e)[:80]}")
            time.sleep(2 ** attempt)
    
    return -1


# =============================================================================
# CHECKPOINT MANAGEMENT
# =============================================================================

def load_checkpoint() -> dict:
    """Load checkpoint of already processed IDs."""
    if CHECKPOINT_FILE.exists():
        try:
            checkpoint_df = pd.read_csv(CHECKPOINT_FILE)
            processed = {}
            for _, row in checkpoint_df.iterrows():
                processed[row['id']] = {
                    'Standardization_Score': row.get('Standardization_Score', -1),
                    'Neighborhood_Impact': row.get('Neighborhood_Impact', -1)
                }
            logger.info(f"✓ Checkpoint loaded: {len(processed)} IDs already processed")
            return processed
        except Exception as e:
            logger.warning(f"  Could not load checkpoint: {e}")
    return {}


def save_checkpoint(processed: dict):
    """Save current progress."""
    if not processed:
        return
    rows = [{'id': lid, **scores} for lid, scores in processed.items()]
    pd.DataFrame(rows).to_csv(CHECKPOINT_FILE, index=False)


# =============================================================================
# MAIN AI ENRICHMENT
# =============================================================================

def enrich_with_ai(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add AI-generated features:
    - Standardization_Score (from images)
    - Neighborhood_Impact (from texts)
    """
    logger.info("\n" + "="*60)
    logger.info("PHASE 2: AI FEATURE ENGINEERING")
    logger.info("="*60)
    
    # Initialize Gemini
    model = initialize_gemini()
    if model is None:
        logger.warning("⚠️ Gemini not available - setting default values (-1)")
        df['Standardization_Score'] = -1
        df['Neighborhood_Impact'] = -1
        return df
    
    # Load checkpoint
    processed = load_checkpoint()
    
    # Initialize columns
    if 'Standardization_Score' not in df.columns:
        df['Standardization_Score'] = -1
    if 'Neighborhood_Impact' not in df.columns:
        df['Neighborhood_Impact'] = -1
    
    total = len(df)
    new_processed = 0
    skipped = 0
    
    # File coverage stats
    images_exist = sum(1 for lid in df['id'] if (IMAGES_DIR / f"{lid}.jpg").exists())
    texts_exist = sum(1 for lid in df['id'] if (TEXTS_DIR / f"{lid}.txt").exists())
    
    logger.info(f"\n  📊 Dataset: {total} listings")
    logger.info(f"  🖼️  Images available: {images_exist} ({images_exist/total*100:.1f}%)")
    logger.info(f"  📝 Texts available: {texts_exist} ({texts_exist/total*100:.1f}%)")
    logger.info(f"  📂 Already cached: {len(processed)}")
    
    remaining = total - len(processed)
    est_min = (remaining * 2 * RATE_LIMIT_DELAY) / 60
    logger.info(f"  ⏳ Estimated time for {remaining} new items: ~{est_min:.0f} min")
    logger.info(f"\n  Starting...\n")
    
    start_time = time.time()
    
    for idx, row in df.iterrows():
        listing_id = row['id']
        progress = ((idx + 1) / total) * 100
        
        # Skip if cached
        if listing_id in processed:
            df.at[idx, 'Standardization_Score'] = processed[listing_id]['Standardization_Score']
            df.at[idx, 'Neighborhood_Impact'] = processed[listing_id]['Neighborhood_Impact']
            skipped += 1
            continue
        
        new_processed += 1
        
        # ETA
        elapsed = time.time() - start_time
        rate = new_processed / elapsed if elapsed > 0 else 0
        remaining_items = total - (idx + 1)
        eta = remaining_items / rate / 60 if rate > 0 else 0
        
        logger.info(f"[{progress:5.1f}%] ID {listing_id} | New: {new_processed} | Cached: {skipped} | ETA: {eta:.1f}min")
        
        # Process Image → Standardization_Score
        img_path = IMAGES_DIR / f"{listing_id}.jpg"
        if img_path.exists():
            img_score = classify_image(img_path, model)
            df.at[idx, 'Standardization_Score'] = img_score
            time.sleep(RATE_LIMIT_DELAY)
        else:
            df.at[idx, 'Standardization_Score'] = -1
        
        # Process Text → Neighborhood_Impact
        txt_path = TEXTS_DIR / f"{listing_id}.txt"
        if txt_path.exists():
            txt_score = classify_text(txt_path, model)
            df.at[idx, 'Neighborhood_Impact'] = txt_score
            time.sleep(RATE_LIMIT_DELAY)
        else:
            df.at[idx, 'Neighborhood_Impact'] = -1
        
        # Update cache
        processed[listing_id] = {
            'Standardization_Score': df.at[idx, 'Standardization_Score'],
            'Neighborhood_Impact': df.at[idx, 'Neighborhood_Impact']
        }
        
        # Checkpoint
        if new_processed % CHECKPOINT_INTERVAL == 0:
            save_checkpoint(processed)
            logger.info(f"  💾 Checkpoint saved ({len(processed)} total)")
    
    # Final save
    save_checkpoint(processed)
    
    # Summary
    total_time = (time.time() - start_time) / 60
    
    logger.info(f"\n  " + "="*50)
    logger.info(f"  ✓ AI Enrichment Complete in {total_time:.1f} min")
    logger.info(f"  " + "="*50)
    logger.info(f"  New processed: {new_processed}")
    logger.info(f"  From cache: {skipped}")
    
    # Score distributions
    logger.info(f"\n  Standardization_Score:")
    logger.info(f"    1 (Industrialisé): {(df['Standardization_Score'] == 1).sum()}")
    logger.info(f"    0 (Personnel):     {(df['Standardization_Score'] == 0).sum()}")
    logger.info(f"   -1 (Autre/Error):   {(df['Standardization_Score'] == -1).sum()}")
    
    logger.info(f"\n  Neighborhood_Impact:")
    logger.info(f"    1 (Hôtélisé):         {(df['Neighborhood_Impact'] == 1).sum()}")
    logger.info(f"    0 (Voisinage naturel): {(df['Neighborhood_Impact'] == 0).sum()}")
    logger.info(f"   -1 (Autre/Error):       {(df['Neighborhood_Impact'] == -1).sum()}")
    
    return df


# =============================================================================
# OUTPUT
# =============================================================================

def save_transformed_data(df: pd.DataFrame):
    """Save the transformed DataFrame."""
    logger.info(f"\n💾 Saving to {OUTPUT_FILE.name}...")
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    
    size_kb = OUTPUT_FILE.stat().st_size / 1024
    logger.info(f"✓ Saved: {OUTPUT_FILE}")
    logger.info(f"  Size: {size_kb:.2f} KB | Rows: {len(df)} | Cols: {len(df.columns)}")


def display_final_summary(df: pd.DataFrame):
    """Display final summary."""
    logger.info("\n" + "="*60)
    logger.info("TRANSFORMATION COMPLETE")
    logger.info("="*60)
    
    logger.info(f"\nFinal DataFrame: {len(df)} rows × {len(df.columns)} columns")
    logger.info(f"\nColumns: {list(df.columns)}")
    
    # Show new AI columns
    logger.info(f"\n🤖 New AI Features Added:")
    logger.info(f"   - Standardization_Score (1=industrialisé, 0=personnel, -1=autre)")
    logger.info(f"   - Neighborhood_Impact (1=hôtélisé, 0=voisinage naturel, -1=autre)")
    
    logger.info("\n" + "="*60)
    logger.info("🚀 Next step: python scripts/06_load.py")
    logger.info("="*60)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main transformation pipeline."""
    logger.info("="*60)
    logger.info("05_TRANSFORM.PY - Data Transformation & AI Enrichment")
    logger.info("ImmoVision 360 - Phase 2: ETL Pipeline")
    logger.info("="*60 + "\n")
    
    try:
        # Validate input
        if not INPUT_FILE.exists():
            raise FileNotFoundError(f"Input not found: {INPUT_FILE}\nRun 04_extract.py first!")
        
        # Load data
        logger.info(f"📂 Loading {INPUT_FILE.name}...")
        df = pd.read_csv(INPUT_FILE)
        logger.info(f"✓ Loaded {len(df):,} rows × {len(df.columns)} columns")
        
        # Phase 1: Data Cleaning
        df = apply_cleaning_rules(df)
        
        # Phase 2: AI Feature Engineering
        df = enrich_with_ai(df)
        
        # Save output
        save_transformed_data(df)
        
        # Summary
        display_final_summary(df)
        
        logger.info("\n✅ TRANSFORMATION COMPLETE")
        return df
        
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Interrupted - checkpoint saved")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()