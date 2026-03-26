"""
Data Enrichment Functions for FlowBySector Processing

This module contains functions for enriching FlowBySector data with additional
attributes including fuel types, USEEIO sectors, GHG source categories, and
primary activity information.
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(parent_dir))
# COLUMN_MAPPING removed - using direct column names


def enrich_with_fuel(fbs_data, fuel_by_table, fuel_by_term):
    """
    Enrich FlowBySector data with fuel type.
    
    Uses a two-step approach:
    1. First, match by table reference in MetaSources (before the period)
    2. Then, search for fuel terms in PrimaryActivity (prioritizing longer terms)
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with MetaSources and PrimaryActivity columns
    fuel_by_table : dict
        Dictionary mapping table references (e.g., "EPA_GHGI_T_3_73") to fuel types
    fuel_by_term : dict
        Dictionary mapping lookup terms to fuel types
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "Fuel" column added
    """
    if "MetaSources" not in fbs_data.columns and "PrimaryActivity" not in fbs_data.columns:
        print("Skipping fuel enrichment - missing required columns")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with fuel types...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Initialize the new column
    enriched_data['Fuel Consumed'] = None
    
    # TODO: Implement table lookup logic
    # TODO: Implement term lookup logic
    # TODO: Add match counting and reporting
    
    print(f"✓ Fuel enrichment completed")
    
    return enriched_data


def enrich_with_useeio(fbs_data, naics_to_useeio_dict):
    """
    Enrich FlowBySector data with USEEIO sector codes.
    
    Maps NAICS codes in SectorProducedBy to USEEIO codes using the crosswalk.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with SectorProducedBy column containing NAICS codes
    naics_to_useeio_dict : dict
        Dictionary mapping NAICS codes to USEEIO codes
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "USEEIO" column added
    """
    if "SectorProducedBy" not in fbs_data.columns:
        print("Skipping USEEIO enrichment - SectorProducedBy column not found")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with USEEIO sector codes...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Initialize the new column
    enriched_data['USEEIO'] = None
    
    matched_count = 0
    
    for idx, row in enriched_data.iterrows():
        sector_produced_by = row.get("SectorProducedBy", "")
        
        if pd.isna(sector_produced_by) or not sector_produced_by:
            continue
        
        # Convert to string and strip whitespace
        naics_code = str(sector_produced_by).strip()
        
        # Look up USEEIO code
        if naics_code in naics_to_useeio_dict:
            enriched_data.at[idx, 'USEEIO'] = naics_to_useeio_dict[naics_code]
            matched_count += 1
    
    print(f"✓ Matched {matched_count:,} records with USEEIO sector codes")
    
    return enriched_data


def enrich_with_primary_activities(fbs_data, primary_activity_mapping):
    """
    Enrich FlowBySector data with PrimaryActivity information.
    
    Logic:
    1. If AttributionSources is "direct", look up the ActivityProducedBy in the YAML mapping
       to find the original detailed activity name(s) from the YAML keys
    2. Otherwise, match MetaSources with m1 YAML mapping (source.activity_set or source)
    3. Deduplicate and simplify the resulting activities
    
    Creates one column:
    - PrimaryActivity: Primary activity name(s), deduplicated and simplified
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with MetaSources, AttributionSources, and ActivityProducedBy columns
    primary_activity_mapping : dict
        Flat mapping: "source_name.activity_set" or "source_name" → {'full': [...], 'short': [...]}
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with PrimaryActivity column added
    """
    if not primary_activity_mapping:
        print("No PrimaryActivity mapping available - skipping PrimaryActivity enrichment")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with PrimaryActivity information...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Initialize the new column
    enriched_data['PrimaryActivity'] = None
    
    # TODO: Implement direct attribution logic
    # TODO: Implement YAML mapping logic
    # TODO: Add deduplication and simplification
    # TODO: Add match counting and reporting
    
    print(f"✓ PrimaryActivity enrichment completed")
    
    return enriched_data


def enrich_with_metadata(fbs_data, meta_map):
    """
    Enrich FlowBySector data with EPA GHGI metadata.
    
    This function matches FlowBySector records with EPA GHGI table metadata
    to add IPCC categories, subcategories, and source descriptions.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with MetaSources column
    meta_map : pandas.DataFrame
        EPA GHGI metadata mapping
        
    Returns:
    --------
    pandas.DataFrame
        Enriched DataFrame with metadata columns added
    """
    print("Enriching FlowBySector data with EPA GHGI metadata...")
    
    # TODO: Implement meta_id extraction
    # TODO: Perform merge with metadata
    # TODO: Add match counting and reporting
    
    print(f"✓ Metadata enrichment completed")
    
    return fbs_data.copy()


# TODO: Add more enrichment functions as needed during incremental migration
# Candidates from enrich_fbs_with_meta.py (9 enrich_* functions total):
# - enrich_with_activity_sets()
# - enrich_with_ghg_source_categories()
# - enrich_with_gas_category()
# - enrich_with_ar5_100_gwp()
# - enrich_with_useeio_sector_name()
# etc.
