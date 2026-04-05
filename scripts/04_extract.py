import os
import sys
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd

# =============================================================================
# CONFIGURATION
# =============================================================================

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw" / "tabular"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# Input/Output files
INPUT_FILE = DATA_RAW / "listings.csv"
OUTPUT_FILE = DATA_PROCESSED / "filtered_elysee.csv"

# CORRECTED: Use 'neighbourhood_cleansed' column (not 'neighbourhood')
NEIGHBOURHOOD_COLUMN = "neighbourhood_cleansed"

# Target neighbourhood - Verified from data: "Élysée" has 2,625 listings
TARGET_NEIGHBOURHOOD = "Élysée"

# =============================================================================
# FEATURE SELECTION - COLUMNS TO KEEP
# =============================================================================

COLS_TO_KEEP = [
    # === IDENTIFIERS (for joins with images/texts) ===
    "id",                              # Primary key - links to [ID].jpg and [ID].txt
    "name",                            # Listing title - context
    
    # === HOST INFORMATION ===
    "host_id",                         # Host identifier - for aggregation
    "host_name",                       # Host name - context
    "calculated_host_listings_count",  # [HYPOTHESIS A] Multi-property detector
    "host_response_time",              # [HYPOTHESIS B] Response delay category
    "host_response_rate",              # [HYPOTHESIS B] Response rate percentage
    
    # === GEOLOCATION ===
    "neighbourhood_cleansed",          # CORRECTED: Neighbourhood name - for filtering
    "latitude",                        # GPS coordinates - spatial analysis
    "longitude",                       # GPS coordinates - spatial analysis
    
    # === PROPERTY CHARACTERISTICS ===
    "property_type",                   # [HYPOTHESIS A] Type of property
    "room_type",                       # [HYPOTHESIS A] Entire home vs shared
    "price",                           # [HYPOTHESIS A] Nightly price
    "minimum_nights",                  # [HYPOTHESIS A] Min stay (high = pro?)
    "availability_365",                # [HYPOTHESIS A] Days available/year
    
    # === REVIEW METRICS (for activity analysis) ===
    "number_of_reviews",               # Activity volume
    "reviews_per_month",               # Activity trend
    "last_review",                     # Recency of activity
    
    # === REGULATORY ===
    "license",                         # Compliance with Paris regulations
]

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging for the extraction process."""
    log_format = "%(asctime)s | %(levelname)-8s | %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

def validate_paths():
    """Verify input file exists and create output directory if needed."""
    logger.info("Validating paths...")
    
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Please ensure Phase 1 (data ingestion) has been completed."
        )
    
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    logger.info(f"✓ Input file found: {INPUT_FILE}")
    logger.info(f"✓ Output directory ready: {DATA_PROCESSED}")


def load_raw_data():
    """Load the raw listings.csv file."""
    logger.info(f"Loading raw data from {INPUT_FILE.name}...")
    
    try:
        df = pd.read_csv(INPUT_FILE, low_memory=False)
        logger.info(f"✓ Loaded {len(df):,} listings with {len(df.columns)} columns")
        return df
    except Exception as e:
        logger.error(f"Failed to load CSV: {e}")
        raise


def validate_columns(df: pd.DataFrame) -> list:
    """Check which columns from COLS_TO_KEEP exist in the DataFrame."""
    logger.info("Validating column selection...")
    
    available_cols = set(df.columns)
    requested_cols = set(COLS_TO_KEEP)
    
    missing_cols = requested_cols - available_cols
    if missing_cols:
        logger.warning(f"⚠ Missing columns (will be skipped): {missing_cols}")
    
    valid_cols = [col for col in COLS_TO_KEEP if col in available_cols]
    logger.info(f"✓ {len(valid_cols)}/{len(COLS_TO_KEEP)} columns available for extraction")
    
    return valid_cols


def filter_neighbourhood(df: pd.DataFrame) -> pd.DataFrame:
    """Filter DataFrame to keep only the target neighbourhood (Élysée)."""
    logger.info(f"Filtering for neighbourhood: '{TARGET_NEIGHBOURHOOD}'...")
    
    if NEIGHBOURHOOD_COLUMN not in df.columns:
        raise KeyError(f"Column '{NEIGHBOURHOOD_COLUMN}' not found in dataset")
    
    # Show neighbourhood distribution
    unique_neighbourhoods = df[NEIGHBOURHOOD_COLUMN].nunique()
    logger.info(f"Found {unique_neighbourhoods} unique neighbourhoods in dataset")
    
    # Apply filter (exact match, case-sensitive since we know the exact name)
    mask = df[NEIGHBOURHOOD_COLUMN] == TARGET_NEIGHBOURHOOD
    df_filtered = df[mask].copy()
    
    if len(df_filtered) == 0:
        # Fallback: try case-insensitive
        mask = df[NEIGHBOURHOOD_COLUMN].str.lower() == TARGET_NEIGHBOURHOOD.lower()
        df_filtered = df[mask].copy()
    
    if len(df_filtered) == 0:
        available = df[NEIGHBOURHOOD_COLUMN].unique()
        logger.error(f"No listings found for '{TARGET_NEIGHBOURHOOD}'")
        logger.info(f"Available neighbourhoods: {sorted(available)}")
        raise ValueError(f"Target neighbourhood '{TARGET_NEIGHBOURHOOD}' not found")
    
    logger.info(f"✓ Filtered to {len(df_filtered):,} listings in {TARGET_NEIGHBOURHOOD}")
    return df_filtered


def select_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """Select only the specified columns from the DataFrame."""
    logger.info(f"Selecting {len(columns)} strategic columns...")
    
    df_selected = df[columns].copy()
    logger.info(f"✓ Column selection complete")
    
    return df_selected


def display_extraction_summary(df_original: pd.DataFrame, df_extracted: pd.DataFrame):
    """Display a summary of the extraction process."""
    logger.info("\n" + "="*60)
    logger.info("EXTRACTION SUMMARY")
    logger.info("="*60)
    logger.info(f"Original dataset:  {len(df_original):,} rows × {len(df_original.columns)} columns")
    logger.info(f"Extracted dataset: {len(df_extracted):,} rows × {len(df_extracted.columns)} columns")
    logger.info(f"Data reduction:    {(1 - len(df_extracted)/len(df_original))*100:.1f}% rows removed")
    logger.info(f"Column reduction:  {len(df_original.columns)} → {len(df_extracted.columns)} columns")
    logger.info("="*60)
    
    logger.info("\nColumns retained by Hypothesis:")
    logger.info("  [A] Economic: calculated_host_listings_count, price, property_type, room_type, availability_365, minimum_nights")
    logger.info("  [B] Social:   host_response_time, host_response_rate")
    logger.info("  [C] Visual:   (images analyzed in transform phase)")
    logger.info("  [ID/Geo]:     id, host_id, neighbourhood_cleansed, latitude, longitude")
    logger.info("  [Activity]:   number_of_reviews, reviews_per_month, last_review")
    logger.info("  [Regulatory]: license")


def save_filtered_data(df: pd.DataFrame):
    """Save the filtered DataFrame to the processed directory."""
    logger.info(f"\nSaving filtered data to {OUTPUT_FILE.name}...")
    
    try:
        df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
        file_size_kb = OUTPUT_FILE.stat().st_size / 1024
        logger.info(f"✓ Saved successfully: {OUTPUT_FILE}")
        logger.info(f"  File size: {file_size_kb:.2f} KB")
    except Exception as e:
        logger.error(f"Failed to save CSV: {e}")
        raise


def display_data_preview(df: pd.DataFrame):
    """Show a preview of the extracted data."""
    logger.info("\n" + "="*60)
    logger.info("DATA PREVIEW (First 5 rows)")
    logger.info("="*60)
    
    # Show key columns
    preview_cols = ["id", "name", "host_id", "price", "room_type", "calculated_host_listings_count"]
    preview_cols = [c for c in preview_cols if c in df.columns]
    
    print(df[preview_cols].head().to_string())
    
    logger.info("\n" + "="*60)
    logger.info("DATA TYPES")
    logger.info("="*60)
    for col in df.columns:
        null_count = df[col].isna().sum()
        null_pct = (null_count / len(df)) * 100
        logger.info(f"  {col:<35} {str(df[col].dtype):<15} (NaN: {null_count:,} = {null_pct:.1f}%)")


def generate_metadata(df_original: pd.DataFrame, df_extracted: pd.DataFrame) -> dict:
    """Generate extraction metadata for documentation."""
    metadata = {
        "extraction_date": datetime.now().isoformat(),
        "source_file": str(INPUT_FILE),
        "output_file": str(OUTPUT_FILE),
        "target_neighbourhood": TARGET_NEIGHBOURHOOD,
        "original_rows": len(df_original),
        "original_columns": len(df_original.columns),
        "extracted_rows": len(df_extracted),
        "extracted_columns": len(df_extracted.columns),
        "columns_kept": list(df_extracted.columns),
        "data_reduction_pct": round((1 - len(df_extracted)/len(df_original))*100, 2),
    }
    
    logger.info(f"\nExtraction completed at: {metadata['extraction_date']}")
    return metadata


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main extraction pipeline."""
    logger.info("="*60)
    logger.info("04_EXTRACT.PY - Strategic Data Extraction")
    logger.info("ImmoVision 360 - Phase 2: ETL Pipeline")
    logger.info("="*60 + "\n")
    
    try:
        # Step 1: Validate paths
        validate_paths()
        
        # Step 2: Load raw data
        df_raw = load_raw_data()
        
        # Step 3: Validate requested columns
        valid_columns = validate_columns(df_raw)
        
        # Step 4: Filter by neighbourhood (Élysée)
        df_filtered = filter_neighbourhood(df_raw)
        
        # Step 5: Select strategic columns
        df_extracted = select_columns(df_filtered, valid_columns)
        
        # Step 6: Display summary
        display_extraction_summary(df_raw, df_extracted)
        
        # Step 7: Preview data
        display_data_preview(df_extracted)
        
        # Step 8: Save to Silver zone
        save_filtered_data(df_extracted)
        
        # Step 9: Generate metadata
        metadata = generate_metadata(df_raw, df_extracted)
        
        logger.info("\n" + "="*60)
        logger.info("✅ EXTRACTION COMPLETE")
        logger.info("="*60)
        logger.info(f"Output: {OUTPUT_FILE}")
        logger.info(f"Rows: {metadata['extracted_rows']:,} | Columns: {metadata['extracted_columns']}")
        logger.info("Next step: Run 05_transform.py")
        logger.info("="*60)
        
        return df_extracted
        
    except FileNotFoundError as e:
        logger.error(f"❌ File Error: {e}")
        sys.exit(1)
    except KeyError as e:
        logger.error(f"❌ Column Error: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"❌ Value Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()