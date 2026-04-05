#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_load.py - Load Transformed Data into PostgreSQL Data Warehouse

This script completes the ETL pipeline by loading the transformed/enriched
data from the Silver zone (CSV) into a PostgreSQL database.

Features:
- Secure credential management via .env
- SQLAlchemy engine for database connection
- Idempotent loading (if_exists='replace')
- Data type validation and mapping
- Comprehensive logging and error handling

Author: ImmoVision 360 Team
Phase: 2 - ETL Pipeline (Load)
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

# SQLAlchemy imports
try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.exc import SQLAlchemyError
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    print("⚠️ SQLAlchemy not installed. Run: pip install sqlalchemy psycopg2-binary")

# =============================================================================
# CONFIGURATION
# =============================================================================

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# Load environment variables from .env
load_dotenv(PROJECT_ROOT / ".env")

# Input file (Silver zone)
INPUT_FILE = DATA_PROCESSED / "transformed_elysee.csv"

# Database configuration from environment variables
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "immovision_db")

# Target table name in PostgreSQL
TABLE_NAME = "elysee_listings_silver"

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
# DATABASE FUNCTIONS
# =============================================================================

def validate_environment():
    """Validate that all required environment variables are set."""
    logger.info("Validating environment configuration...")
    
    required_vars = {
        "DB_USER": DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_HOST": DB_HOST,
        "DB_PORT": DB_PORT,
        "DB_NAME": DB_NAME,
    }
    
    missing = []
    for var_name, var_value in required_vars.items():
        if not var_value:
            missing.append(var_name)
        else:
            # Mask password for security
            display_value = "****" if "PASSWORD" in var_name else var_value
            logger.info(f"  {var_name}: {display_value}")
    
    if missing:
        logger.error(f"❌ Missing environment variables: {missing}")
        logger.error("   Please check your .env file")
        return False
    
    logger.info("✓ Environment configuration valid")
    return True


def create_db_engine():
    """
    Create SQLAlchemy engine for PostgreSQL connection.
    Returns the engine object or None if connection fails.
    """
    logger.info("Creating database connection...")
    
    if not SQLALCHEMY_AVAILABLE:
        logger.error("❌ SQLAlchemy not available!")
        return None
    
    # Build connection string
    # Format: postgresql://user:password@host:port/database
    connection_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Mask password in log
    safe_connection = f"postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    logger.info(f"  Connection: {safe_connection}")
    
    try:
        engine = create_engine(connection_string)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        logger.info("✓ Database connection successful")
        return engine
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("\nTroubleshooting:")
        logger.error("  1. Is PostgreSQL running?")
        logger.error("  2. Does the database exist? Create with: CREATE DATABASE immovision_db;")
        logger.error("  3. Are credentials correct in .env?")
        logger.error("  4. Is the host/port accessible?")
        return None


def load_silver_data():
    """Load the transformed CSV file from the Silver zone."""
    logger.info(f"\nLoading data from {INPUT_FILE.name}...")
    
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run 05_transform.py first!"
        )
    
    df = pd.read_csv(INPUT_FILE)
    
    logger.info(f"✓ Loaded {len(df):,} rows × {len(df.columns)} columns")
    logger.info(f"  Columns: {list(df.columns)}")
    
    return df


def prepare_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure proper data types before loading to PostgreSQL.
    SQLAlchemy will infer types, but we can help with explicit conversions.
    """
    logger.info("\nPreparing data types...")
    
    df = df.copy()
    
    # Define expected types for key columns
    type_mappings = {
        # Integer columns
        'id': 'Int64',
        'host_id': 'Int64',
        'calculated_host_listings_count': 'Int64',
        'minimum_nights': 'Int64',
        'availability_365': 'Int64',
        'number_of_reviews': 'Int64',
        'Standardization_Score': 'Int64',
        'Neighborhood_Impact': 'Int64',
        
        # Float columns
        'latitude': 'float64',
        'longitude': 'float64',
        'reviews_per_month': 'float64',
        'host_response_rate': 'float64',
        'price': 'float64',
        
        # String columns (kept as object/string)
        'name': 'string',
        'host_name': 'string',
        'host_response_time': 'string',
        'neighbourhood_cleansed': 'string',
        'property_type': 'string',
        'room_type': 'string',
        'license': 'string',
        'last_review': 'string',
    }
    
    for col, dtype in type_mappings.items():
        if col in df.columns:
            try:
                if dtype == 'Int64':
                    # Handle NaN properly with nullable integer
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                elif dtype == 'float64':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif dtype == 'string':
                    df[col] = df[col].astype('string')
                
                logger.info(f"  ✓ {col}: {dtype}")
            except Exception as e:
                logger.warning(f"  ⚠️ {col}: could not convert to {dtype} - {e}")
    
    return df


def load_to_postgresql(df: pd.DataFrame, engine) -> bool:
    """
    Load DataFrame to PostgreSQL table.
    Uses if_exists='replace' for idempotent operation.
    """
    logger.info(f"\nLoading data to PostgreSQL table: {TABLE_NAME}")
    logger.info(f"  Strategy: REPLACE (idempotent)")
    
    try:
        # Load data to SQL
        df.to_sql(
            name=TABLE_NAME,
            con=engine,
            if_exists='replace',  # Idempotent: recreate table each time
            index=False,          # Don't write DataFrame index as column
            method='multi',       # Use multi-row inserts for performance
            chunksize=500,        # Insert in chunks for large datasets
        )
        
        logger.info(f"✓ Data loaded successfully!")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Failed to load data: {e}")
        return False


def verify_load(engine) -> dict:
    """Verify the data was loaded correctly by querying the table."""
    logger.info(f"\nVerifying data in table: {TABLE_NAME}")
    
    try:
        with engine.connect() as conn:
            # Count rows
            result = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}"))
            row_count = result.fetchone()[0]
            
            # Get column info
            inspector = inspect(engine)
            columns = inspector.get_columns(TABLE_NAME)
            col_names = [col['name'] for col in columns]
            
            # Sample query
            result = conn.execute(text(f"SELECT * FROM {TABLE_NAME} LIMIT 3"))
            sample_rows = result.fetchall()
        
        logger.info(f"  ✓ Row count: {row_count:,}")
        logger.info(f"  ✓ Columns: {len(col_names)}")
        logger.info(f"  ✓ Table exists and is queryable")
        
        return {
            'success': True,
            'row_count': row_count,
            'columns': col_names,
            'sample_rows': sample_rows
        }
        
    except SQLAlchemyError as e:
        logger.error(f"❌ Verification failed: {e}")
        return {'success': False, 'error': str(e)}


def display_sample_queries(engine):
    """Display sample SQL queries that can be run on the loaded data."""
    logger.info("\n" + "="*60)
    logger.info("SAMPLE SQL QUERIES")
    logger.info("="*60)
    
    queries = [
        ("Count by Standardization Score", 
         f"""SELECT "Standardization_Score", COUNT(*) as count 
             FROM {TABLE_NAME} 
             GROUP BY "Standardization_Score" 
             ORDER BY "Standardization_Score";"""),
        
        ("Count by Neighborhood Impact",
         f"""SELECT "Neighborhood_Impact", COUNT(*) as count 
             FROM {TABLE_NAME} 
             GROUP BY "Neighborhood_Impact" 
             ORDER BY "Neighborhood_Impact";"""),
        
        ("Multi-property hosts (5+ listings)",
         f"""SELECT host_name, calculated_host_listings_count 
             FROM {TABLE_NAME} 
             WHERE calculated_host_listings_count >= 5 
             ORDER BY calculated_host_listings_count DESC 
             LIMIT 10;"""),
    ]
    
    for query_name, query in queries:
        logger.info(f"\n📊 {query_name}:")
        try:
            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                for row in rows[:5]:
                    logger.info(f"   {row}")
        except Exception as e:
            logger.info(f"   Query: {query[:80]}...")


def display_final_summary(df: pd.DataFrame, verification: dict):
    """Display final loading summary."""
    logger.info("\n" + "="*60)
    logger.info("LOAD COMPLETE - SUMMARY")
    logger.info("="*60)
    
    logger.info(f"""
  📊 Data Warehouse: PostgreSQL
  🗄️  Database: {DB_NAME}
  📋 Table: {TABLE_NAME}
  
  📈 Statistics:
     - Rows loaded: {verification.get('row_count', 'N/A'):,}
     - Columns: {len(verification.get('columns', [])):}
  
  🔗 Connection: postgresql://{DB_USER}:****@{DB_HOST}:{DB_PORT}/{DB_NAME}
  
  ✅ ETL Pipeline Complete!
     Extract → Transform → Load ✓
""")
    
    logger.info("="*60)
    logger.info("🎉 Phase 2 COMPLETE - Data Warehouse Ready!")
    logger.info("="*60)
    logger.info("\nNext: Phase 3 - Visualization & Analysis")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main loading pipeline."""
    logger.info("="*60)
    logger.info("06_LOAD.PY - Load to PostgreSQL Data Warehouse")
    logger.info("ImmoVision 360 - Phase 2: ETL Pipeline (Final Step)")
    logger.info("="*60 + "\n")
    
    try:
        # Step 1: Validate environment
        if not validate_environment():
            sys.exit(1)
        
        # Step 2: Create database engine
        engine = create_db_engine()
        if engine is None:
            sys.exit(1)
        
        # Step 3: Load Silver zone data
        df = load_silver_data()
        
        # Step 4: Prepare data types
        df = prepare_data_types(df)
        
        # Step 5: Load to PostgreSQL
        success = load_to_postgresql(df, engine)
        if not success:
            sys.exit(1)
        
        # Step 6: Verify load
        verification = verify_load(engine)
        if not verification.get('success'):
            logger.warning("⚠️ Verification had issues, but data may still be loaded")
        
        # Step 7: Display sample queries
        display_sample_queries(engine)
        
        # Step 8: Final summary
        display_final_summary(df, verification)
        
        logger.info("\n✅ LOAD COMPLETE")
        return True
        
    except FileNotFoundError as e:
        logger.error(f"❌ File Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()