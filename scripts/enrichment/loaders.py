"""
Data Loading Functions for FlowBySector Processing

This module contains functions for loading various data sources including
parquet files, CSV mappings, YAML configurations, and lookups.
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))
import config


def load_parquet_data(input_path, subfolder, file_name):
    """
    Load FlowBySector parquet data and prepare for processing.
    
    Parameters:
    -----------
    input_path : str
        Base path to FlowSA data directory
    subfolder : str
        Subfolder containing the parquet files (usually "FlowBySector")
    file_name : str
        Name of the parquet file to load
        
    Returns:
    --------
    pandas.DataFrame
        Loaded FlowBySector data with formatted Location column
    """
    print(f"Loading parquet data from: {os.path.join(input_path, subfolder, file_name)}")
    
    # Load the parquet file
    fbs_parquet = pd.read_parquet(os.path.join(input_path, subfolder, file_name))
    
    # Maintain leading zeros in Location column by formatting as Excel string
    # This prevents Excel from treating location codes like "01000" as numbers
    fbs_parquet.Location = fbs_parquet.Location.apply('="{}"'.format)
    
    print(f"✓ Loaded {len(fbs_parquet):,} records from parquet file")
    
    return fbs_parquet


def load_metadata_mapping(mapping_csv_path):
    """
    Load EPA GHGI metadata mapping from CSV file.
    
    Parameters:
    -----------
    mapping_csv_path : str
        Path to the EPA_GHGI_meta_sources.csv file
        
    Returns:
    --------
    pandas.DataFrame or None
        Metadata mapping DataFrame, or None if file doesn't exist
    """
    if os.path.exists(mapping_csv_path):
        print(f"Loading EPA GHGI metadata from: {mapping_csv_path}")
        meta_map = pd.read_csv(mapping_csv_path)
        print(f"✓ Loaded {len(meta_map):,} metadata records")
        return meta_map
    else:
        print(f"Warning: Metadata file not found at {mapping_csv_path}")
        print("Run the EPA GHGI metadata extraction script first:")
        print("python scripts/extract_meta_from_EPA_GHGI.py")
        return None


def load_fuel_lookup(lookup_csv_path):
    """
    Load fuel lookup table from CSV file.
    
    Parameters:
    -----------
    lookup_csv_path : str
        Path to the fuel lookup CSV file
        
    Returns:
    --------
    dict or None
        Dictionary mapping lookup terms to fuel types, or None if file doesn't exist
    """
    if os.path.exists(lookup_csv_path):
        print(f"Loading fuel lookup from: {lookup_csv_path}")
        lookup_df = pd.read_csv(lookup_csv_path)
        
        # Determine the column names based on file content
        if 'Table ref' in lookup_df.columns:
            # Table-based lookup
            lookup_dict = dict(zip(
                lookup_df['Table ref'].str.strip(),
                lookup_df['FuelConsumed'].str.strip()
            ))
        elif 'Fossil Fuel terms for lookup' in lookup_df.columns:
            # Term-based lookup
            lookup_dict = dict(zip(
                lookup_df['Fossil Fuel terms for lookup'].str.strip(),
                lookup_df['FuelConsumed'].str.strip()
            ))
        else:
            print(f"Warning: Unexpected column names in {lookup_csv_path}")
            return None
        
        print(f"✓ Loaded {len(lookup_dict):,} fuel lookup entries")
        return lookup_dict
    else:
        print(f"Warning: Fuel lookup file not found at {lookup_csv_path}")
        return None


# TODO: Add more loader functions as needed during incremental migration
# Candidates from enrich_fbs_with_meta.py (13 load_* functions total):
# - load_generated_fbs_data()
# - load_activity_sets_lookup()
# - load_naics_to_useeio_crosswalk()
# - load_metasource_to_ghgsource_mapping()
# - load_flowable_categorization()
# - load_sector_classification()
# - load_ipcc_ar5_100_gwp()
# - load_method_yaml()
# - load_industry_output()
# - load_market_share_matrix()
# etc.
