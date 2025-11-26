"""
FlowBySector Data Enrichment with EPA GHGI Metadata

This script processes FlowBySector data from FlowSA and enriches it with 
EPA GHGI metadata to create detailed supply chain emission factors.

The enriched data breaks down GHG emissions by:
- Economic sectors (using NAICS-like codes)
- Greenhouse gas species (CO2, CH4, N2O, etc.)
- EPA GHGI source categories (IPCC categories and subcategories)
- Attribution sources (how emissions were allocated to sectors)
- PrimaryActivity information from method YAML (for non-direct attribution)

This output can then be used with USEEIO models for supply chain analysis.
"""

import os
import sys
import re
import subprocess
import pandas as pd
import numpy as np
import flowsa
from pathlib import Path
from ruamel.yaml import YAML

# Add parent directory to path to import config and terminology
parent_dir = Path(__file__).parent.parent
sys.path.append(str(parent_dir))

# Import configuration settings and terminology
import config
from terminology import TERMINOLOGY, get_jsonld_property

# Import modularized enrichment functions
from enrichment.utils import (
    get_emissions_intensity_col,
    check_flowsa_version,
    validate_flowsa_version,
    filter_columns
)
from enrichment.validators import (
    aggregate_to_reference_format,
    compare_with_reference,
    validate_data
)
from enrichment.loaders import (
    load_parquet_data,
    load_metadata_mapping,
    load_fuel_lookup
)
from enrichment.enrichers import (
    enrich_with_fuel,
    enrich_with_useeio,
    enrich_with_primary_activities,
    enrich_with_metadata
)
from enrichment.exporters import (
    build_emission_events_jsonld,
    build_d3_sunburst_hierarchy,
    save_outputs
)


# TODO: The functions below are now imported from enrichment modules
# They can be gradually removed as the migration continues
# For now, keeping them here to ensure backward compatibility

# DEPRECATED: Moved to enrichment.utils
def get_emissions_intensity_col():
    """Get the emissions intensity column name with the model year."""
    return f"Emissions Intensity (kg/USD_{config.MODEL_YEAR})"


def check_flowsa_version():
    """
    Check if the installed FlowSA version matches requirements.
    
    Returns:
    --------
    tuple : (bool, str, str)
        (version_matches, installed_version, installed_git_hash)
    """
    try:
        # Get FlowSA package location
        import flowsa
        flowsa_path = Path(flowsa.__file__).parent
        
        # Try to get version from git
        try:
            git_hash = subprocess.check_output(
                ['git', 'rev-parse', '--short=7', 'HEAD'],
                cwd=flowsa_path,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except:
            git_hash = None
        
        # Try to get version from package metadata
        try:
            import importlib.metadata
            version = importlib.metadata.version('flowsa')
        except:
            try:
                version = flowsa.__version__
            except:
                version = None
        
        return version, git_hash
    except Exception as e:
        print(f"Warning: Could not determine FlowSA version: {e}")
        return None, None


def validate_flowsa_version():
    """
    Validate that FlowSA version matches requirements in config.
    
    Raises:
    -------
    RuntimeError
        If version doesn't match and STRICT_VERSION_CHECK is True
    """
    if not config.STRICT_VERSION_CHECK:
        return
    
    installed_version, installed_git_hash = check_flowsa_version()
    
    # Handle both single version string and list of acceptable versions
    required_versions = config.REQUIRED_FLOWSA_VERSION
    if isinstance(required_versions, str):
        required_versions = [required_versions]
    
    print(f"\nFlowSA Version Check:")
    print(f"  Required version: {' or '.join(required_versions)} (tag: {config.REQUIRED_FLOWSA_GIT_TAG})")
    print(f"  Installed version: {installed_version or 'unknown'} (git: {installed_git_hash or 'unknown'})")
    
    # Check version - this is the critical check
    version_match = installed_version in required_versions
    
    # Git hash check is optional/advisory only (may not work in all environments)
    # Only warn if both are available and don't match
    if installed_git_hash and config.REQUIRED_FLOWSA_GIT_HASH:
        if installed_git_hash != config.REQUIRED_FLOWSA_GIT_HASH:
            print(f"  Note: Git hash differs (expected: {config.REQUIRED_FLOWSA_GIT_HASH})")
            print(f"        This is usually fine if version numbers match")
    
    if not version_match:
        error_msg = [
            "\n" + "="*80,
            "ERROR: FlowSA Version Mismatch",
            "="*80,
            f"Your reference parquet file was generated with FlowSA v{' or '.join(required_versions)}",
            f"You currently have FlowSA v{installed_version or 'unknown'} (git: {installed_git_hash or 'unknown'})",
            "",
            "To fix this, reinstall the correct version:",
            f"  pip uninstall flowsa",
            f"  pip install git+https://github.com/USEPA/flowsa.git@{config.REQUIRED_FLOWSA_GIT_TAG}",
            "",
            "Or run the installation script:",
            f"  python install_flowsa_2.0.3.py",
            "",
            "Or to skip version checking, set STRICT_VERSION_CHECK = False in config.py",
            "="*80
        ]
        raise RuntimeError("\n".join(error_msg))
    
    print("  Status: OK - Version matches requirements")


def _extract_meta_id(val):
    """
    Extract the EPA GHGI table identifier from MetaSources field.
    
    The MetaSources field often contains strings like "EPA_GHGI_T_3_7.1" or
    multiple sources separated by "|". This function extracts the base table ID
    (e.g., "EPA_GHGI_T_3_7") for matching with metadata.
    
    Parameters:
    -----------
    val : str or None
        The MetaSources value from FlowBySector data
        
    Returns:
    --------
    str or None
        The extracted meta_id for matching with EPA GHGI metadata
    """
    if pd.isna(val):
        return None
    
    s = str(val)
    
    # If multiple sources are present, take the first token by common separators
    s = s.split("|")[0].split(";")[0].split(",")[0].strip()
    
    # Extract portion before the first '.' (removes version numbers like .1, .2)
    return s.split(".")[0].strip()


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


def load_generated_fbs_data(modelname, output_dir):
    """
    Load previously generated FlowBySector data from FlowSA cache.
    
    FlowSA automatically caches generated FBS data in:
    C:\\Users\\{username}\\AppData\\Local\\flowsa\\FlowBySector\\
    
    This function loads from that cache, or falls back to a local generated file.
    If neither exists, provides instructions to generate the data.
    
    Parameters:
    -----------
    modelname : str
        Name of the FlowSA model (e.g., "GHG_national_2022_m2")
    output_dir : str
        Directory containing locally generated FBS files (fallback)
        
    Returns:
    --------
    pandas.DataFrame
        Generated FlowBySector data
    """
    print(f"Loading pre-generated FlowBySector data for model: {modelname}")
    
    # First, try FlowSA cache directory
    flowsa_cache = os.path.join(os.path.expanduser("~"), "AppData", "Local", "flowsa", "FlowBySector")
    
    # Look for parquet files with EXACT model name match (not just prefix)
    if os.path.exists(flowsa_cache):
        print(f"Checking FlowSA cache: {flowsa_cache}")
        # Match pattern: {modelname}_*.parquet or {modelname}.parquet
        # but NOT {modelname}AnythingElse_*.parquet
        all_files = os.listdir(flowsa_cache)
        cache_files = []
        for f in all_files:
            if f.endswith('.parquet'):
                # Extract the model name part (before version info)
                if f.startswith(modelname):
                    # Check if it's an exact match: modelname followed by _ or . or end of name
                    after_modelname = f[len(modelname):]
                    if after_modelname and after_modelname[0] in ['_', '.', 'v']:
                        cache_files.append(f)
                    elif not after_modelname.replace('.parquet', ''):  # exact match with just .parquet
                        cache_files.append(f)
        
        if cache_files:
            # Use the first matching file (or most recent if multiple versions exist)
            cache_file = sorted(cache_files)[-1]  # Get latest by filename
            cache_path = os.path.join(flowsa_cache, cache_file)
            print(f"✓ Found cached FBS data: {cache_file}")
            print(f"  Loading from: {cache_path}")
            fbs_data = pd.read_parquet(cache_path)
            print(f"✓ Loaded {len(fbs_data):,} records from FlowSA cache")
            return fbs_data
        else:
            print(f"  No exact match found for model: {modelname}")
            print(f"  Available files starting with '{modelname}':")
            matching_prefix = [f for f in all_files if f.startswith(modelname) and f.endswith('.parquet')]
            for f in matching_prefix[:5]:  # Show first 5
                print(f"    - {f}")
            if len(matching_prefix) > 5:
                print(f"    ... and {len(matching_prefix) - 5} more")
    
    # Fallback: try local output directory
    parquet_path = os.path.join(output_dir, f"{modelname}_generated.parquet")
    csv_path = os.path.join(output_dir, f"{modelname}_generated.csv")
    
    if os.path.exists(parquet_path):
        print(f"Loading from local file: {parquet_path}")
        fbs_data = pd.read_parquet(parquet_path)
        print(f"✓ Loaded {len(fbs_data):,} records")
        return fbs_data
    elif os.path.exists(csv_path):
        print(f"Loading from local file: {csv_path}")
        fbs_data = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(fbs_data):,} records")
        return fbs_data
    else:
        error_msg = [
            "",
            "="*80,
            "ERROR: Pre-generated FBS data not found!",
            "="*80,
            "Searched in:",
            f"  FlowSA cache: {flowsa_cache}",
            f"  Local output: {parquet_path}",
            "",
            f"No cached file found for model: {modelname}",
            "The FlowBySector data needs to be generated first.",
            "",
            "To generate it, run:",
            f"  python -c \"import flowsa; flowsa.getFlowBySector('{modelname}')\"",
            "",
            "This will take several minutes on first run, then results are cached.",
            "="*80
        ]
        raise FileNotFoundError("\n".join(error_msg))


def aggregate_to_reference_format(fbs_with_activities):
    """
    Aggregate FlowBySector data to match reference format (without activity columns).
    
    This groups by all columns except activity columns and sums the FlowAmount,
    creating an equivalent dataset to what would be generated with 
    retain_activity_columns=False.
    
    Parameters:
    -----------
    fbs_with_activities : pandas.DataFrame
        FlowBySector data with activity columns retained
        
    Returns:
    --------
    pandas.DataFrame
        Aggregated FlowBySector data without activity columns
    """
    print("Aggregating data to reference format (grouping out activity columns)...")
    
    # Identify activity columns (these vary by source but typically include ActivityProducedBy, ActivityConsumedBy, etc.)
    activity_cols = [col for col in fbs_with_activities.columns if 'Activity' in col]
    
    if activity_cols:
        print(f"Found activity columns to aggregate: {activity_cols}")
    else:
        print("No activity columns found - data may already be in reference format")
        return fbs_with_activities.copy()
    
    # Group by all columns except activity columns
    groupby_cols = [col for col in fbs_with_activities.columns 
                    if col not in activity_cols and col != 'FlowAmount']
    
    print(f"Grouping by {len(groupby_cols)} columns...")
    
    # Aggregate: sum FlowAmount for each group
    aggregated = fbs_with_activities.groupby(groupby_cols, dropna=False).agg({
        'FlowAmount': 'sum'
    }).reset_index()
    
    print(f"✓ Aggregated from {len(fbs_with_activities):,} to {len(aggregated):,} records")
    
    return aggregated


def filter_columns(df, keep_cols, exclude_qc=False, qc_cols=None):
    """
    Filter DataFrame to keep only specified columns that are present.
    
    Optionally excludes quality control columns if requested.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame to filter
    keep_cols : list
        List of column names to keep (if present)
    exclude_qc : bool, optional
        If True, exclude quality control columns from output (default: False)
    qc_cols : list, optional
        List of quality control column names to exclude if exclude_qc=True
        
    Returns:
    --------
    pandas.DataFrame
        Filtered DataFrame with only the specified columns
    """
    # Remove QC columns from keep list if requested
    if exclude_qc and qc_cols:
        keep_cols = [c for c in keep_cols if c not in qc_cols]
        print(f"Excluding {len(qc_cols)} quality control columns from output")
    
    # Find which columns from our keep list are actually present in the data
    present_cols = [c for c in keep_cols if c in df.columns]
    missing_cols = [c for c in keep_cols if c not in df.columns]
    
    if missing_cols:
        print(f"Note: Some requested columns not found in data: {missing_cols}")
    
    if present_cols:
        print(f"Keeping {len(present_cols)} columns: {present_cols}")
        return df[present_cols].copy()
    else:
        print("Warning: No requested columns found, keeping all columns")
        return df.copy()


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
        elif 'fuel terms for lookup' in lookup_df.columns:
            # Alternative term-based lookup (lowercase)
            lookup_dict = dict(zip(
                lookup_df['fuel terms for lookup'].str.strip(),
                lookup_df['FuelConsumed'].str.strip()
            ))
        else:
            print(f"Warning: Unrecognized column format in {lookup_csv_path}")
            print(f"  Found columns: {lookup_df.columns.tolist()}")
            return None
        
        print(f"✓ Loaded {len(lookup_dict):,} fuel lookup entries")
        return lookup_dict
    else:
        print(f"Warning: fuel lookup file not found at {lookup_csv_path}")
        return None


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
    
    table_match_count = 0
    term_match_count = 0
    term_override_count = 0  # Track when term lookup overrides table lookup
    
    # Debug: Check what data we have
    print(f"DEBUG: fuel_by_table is {'available' if fuel_by_table else 'MISSING/EMPTY'}")
    print(f"DEBUG: fuel_by_term is {'available' if fuel_by_term else 'MISSING/EMPTY'}")
    print(f"DEBUG: Columns in fbs_data: {', '.join(fbs_data.columns.tolist())}")
    print(f"DEBUG: 'PrimaryActivity' column exists: {'PrimaryActivity' in fbs_data.columns}")
    print(f"  Logic: Term lookup (more precise) overrides table lookup if found")
    
    # Step 1: Match by table reference (fallback)
    if fuel_by_table and "MetaSources" in fbs_data.columns:
        print("  Step 1: Matching by table reference...")
        for idx, row in enriched_data.iterrows():
            meta_sources = row.get("MetaSources", "")
            
            if pd.isna(meta_sources) or not meta_sources:
                continue
            
            # Extract table reference (part before the period)
            table_ref = str(meta_sources).split('.')[0].strip()
            
            if table_ref in fuel_by_table:
                enriched_data.at[idx, 'Fuel Consumed'] = fuel_by_table[table_ref]
                table_match_count += 1
    
    # Step 2: Match by term in PrimaryActivity (overrides table matches if found - more precise)
    if fuel_by_term and "PrimaryActivity" in fbs_data.columns:
        print("  Step 2: Matching by terms in PrimaryActivity...")
        
        # Sort lookup terms by length (longest first) to prioritize more specific terms
        sorted_lookup = sorted(fuel_by_term.items(), key=lambda x: len(x[0]), reverse=True)
        
        # Debug: Show what terms we're looking for
        print(f"  DEBUG: Looking for {len(sorted_lookup)} fuel terms: {', '.join([term for term, _ in sorted_lookup[:10]])}{'...' if len(sorted_lookup) > 10 else ''}")
        
        # Track which fuels were found
        fuels_found = set()
    else:
        print("  Step 2: SKIPPED - Condition failed:")
        print(f"    fuel_by_term exists: {fuel_by_term is not None and len(fuel_by_term) > 0}")
        print(f"    PrimaryActivity column exists: {'PrimaryActivity' in fbs_data.columns}")
        if fuel_by_term:
            print(f"    fuel_by_term has {len(fuel_by_term)} entries")
        sorted_lookup = []
        fuels_found = set()
    
    if sorted_lookup:  # Only process if we have terms to match
        
        for idx, row in enriched_data.iterrows():
            primary_activity = row.get("PrimaryActivity", "")
            
            if pd.isna(primary_activity) or not primary_activity:
                continue
            
            primary_activity_str = str(primary_activity)
            
            # Track matched terms and their positions to avoid overlapping matches
            matched_fuels = {}  # {fossil_fuel: [match_positions]}
            matched_positions = set()  # Set of character ranges already matched
            
            # Search for each lookup term in the PrimaryActivity string (longest first)
            for lookup_term, fossil_fuel in sorted_lookup:
                # Find all occurrences of this term (case-insensitive)
                search_str = primary_activity_str.lower()
                term_lower = lookup_term.lower()
                start_pos = 0
                
                while True:
                    pos = search_str.find(term_lower, start_pos)
                    if pos == -1:
                        break
                    
                    # Check if this position overlaps with an already matched (more specific) term
                    match_range = set(range(pos, pos + len(term_lower)))
                    if not match_range.intersection(matched_positions):
                        # No overlap - this is a valid match
                        if fossil_fuel not in matched_fuels:
                            matched_fuels[fossil_fuel] = []
                        matched_fuels[fossil_fuel].append(pos)
                        matched_positions.update(match_range)
                        fuels_found.add(fossil_fuel)
                    
                    start_pos = pos + 1
            
            # If we found matches, join them with " | " and store (overrides table lookup)
            if matched_fuels:
                had_table_match = pd.notna(enriched_data.at[idx, 'Fuel Consumed']) and enriched_data.at[idx, 'Fuel Consumed'] != ''
                enriched_data.at[idx, 'Fuel Consumed'] = ' | '.join(sorted(matched_fuels.keys()))
                if had_table_match:
                    term_override_count += 1
                else:
                    term_match_count += 1
        
        # Debug: Show which fuels were actually found
        print(f"  DEBUG: Fuels found in data: {', '.join(sorted(fuels_found)) if fuels_found else 'NONE'}")
        all_possible_fuels = set([fuel for _, fuel in sorted_lookup])
        missing_fuels = all_possible_fuels - fuels_found
        if missing_fuels:
            print(f"  DEBUG: Fuels NOT found: {', '.join(sorted(missing_fuels))}")
    
    # Final count: table matches that weren't overridden + new term matches + term overrides
    final_table_only = table_match_count - term_override_count
    total_matched = final_table_only + term_match_count + term_override_count
    print(f"✓ Added fuel type to {total_matched:,} records")
    print(f"  - By table reference only: {final_table_only:,}")
    print(f"  - By term matching (new): {term_match_count:,}")
    print(f"  - By term matching (override): {term_override_count:,}")
    
    return enriched_data


def load_activity_sets_lookup(csv_path):
    """
    Load the activity sets lookup CSV file.
    
    Parameters:
    -----------
    csv_path : str
        Path to the activity sets CSV file
        
    Returns:
    --------
    dict
        Dictionary mapping MetaSources values to Activity Set names
    """
    if not os.path.exists(csv_path):
        print(f"Warning: Activity sets lookup file not found at {csv_path}")
        return {}
    
    try:
        df = pd.read_csv(csv_path)
        
        # Create dictionary: MetaSources -> Activity Set
        activity_sets_dict = dict(zip(df['MetaSources'], df['Activity Set']))
        
        print(f"✓ Loaded {len(activity_sets_dict)} activity set mappings")
        return activity_sets_dict
    except Exception as e:
        print(f"Error loading activity sets lookup: {e}")
        return {}


def enrich_with_activity_sets(fbs_data, activity_sets_dict):
    """
    Enrich FlowBySector data with Activity Set information.
    
    Logic:
    1. If MetaSources contains ".direct" or ".direct_attribution", use PrimaryActivity as Activity Set
    2. Otherwise, look up Activity Set from the CSV mapping using MetaSources
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with MetaSources and PrimaryActivity columns
    activity_sets_dict : dict
        Dictionary mapping MetaSources values to Activity Set names
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "Activity Set" column added
    """
    if "MetaSources" not in fbs_data.columns:
        print("Skipping activity set enrichment - MetaSources column not found")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with Activity Set information...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Initialize the new column
    enriched_data['Activity Set'] = None
    
    direct_count = 0
    lookup_count = 0
    
    for idx, row in enriched_data.iterrows():
        meta_sources = row.get("MetaSources", "")
        primary_activity = row.get("PrimaryActivity", "")
        
        if pd.isna(meta_sources) or not meta_sources:
            continue
        
        meta_sources_str = str(meta_sources).strip()
        
        # Check if this is a "direct" or "direct_attribution" activity set
        if '.direct' in meta_sources_str.lower() or '.direct_attribution' in meta_sources_str.lower():
            # Use PrimaryActivity as the Activity Set
            if pd.notna(primary_activity) and primary_activity:
                enriched_data.at[idx, 'Activity Set'] = str(primary_activity)
                direct_count += 1
        else:
            # Look up in the CSV mapping
            if meta_sources_str in activity_sets_dict:
                enriched_data.at[idx, 'Activity Set'] = activity_sets_dict[meta_sources_str]
                lookup_count += 1
    
    total_enriched = direct_count + lookup_count
    print(f"✓ Added Activity Set to {total_enriched:,} records")
    print(f"  - From PrimaryActivity (direct): {direct_count:,}")
    print(f"  - From CSV lookup: {lookup_count:,}")
    
    return enriched_data


def load_naics_to_useeio_crosswalk(csv_path):
    """
    Load the NAICS to USEEIO crosswalk CSV file.
    
    Parameters:
    -----------
    csv_path : str
        Path to the NAICS to USEEIO crosswalk CSV file
        
    Returns:
    --------
    dict
        Dictionary mapping NAICS codes to USEEIO codes
    """
    if not os.path.exists(csv_path):
        print(f"Warning: NAICS to USEEIO crosswalk file not found at {csv_path}")
        return {}
    
    try:
        df = pd.read_csv(csv_path)
        
        # Create dictionary: NAICS -> USEEIO
        # Convert NAICS to string to handle leading zeros
        naics_to_useeio = {}
        for _, row in df.iterrows():
            naics = str(row['NAICS']).strip()
            useeio = str(row['USEEIO']).strip()
            naics_to_useeio[naics] = useeio
        
        print(f"✓ Loaded {len(naics_to_useeio)} NAICS to USEEIO mappings")
        return naics_to_useeio
    except Exception as e:
        print(f"Error loading NAICS to USEEIO crosswalk: {e}")
        return {}


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
        
        # Look up in the crosswalk
        if naics_code in naics_to_useeio_dict:
            enriched_data.at[idx, 'USEEIO'] = naics_to_useeio_dict[naics_code]
            matched_count += 1
    
    print(f"✓ Added USEEIO code to {matched_count:,} records")
    
    return enriched_data


def load_metasource_to_ghgsource_mapping(csv_path):
    """
    Load the MetaSource to GHG Source categorization CSV file.
    
    This file contains comprehensive categorization information including:
    - IPCC/UNFCCC Category
    - Activity Category
    - Activity Subcategory
    - Activity Type
    
    Parameters:
    -----------
    csv_path : str
        Path to the activity_categorization.csv file
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame with the categorization data
    """
    if not os.path.exists(csv_path):
        print(f"Warning: GHG Source categorization file not found at {csv_path}")
        return None
    
    try:
        df = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(df)} GHG Source categorization mappings")
        print(f"  Columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        print(f"Error loading GHG Source categorization: {e}")
        return None


def enrich_with_ghg_source_categories(fbs_data, mapping_df):
    """
    Enrich FlowBySector data with comprehensive GHG categorization.
    
    Adds the following columns based on MetaSources and ActivityProducedBy:
    - IPCC/UNFCCC Category
    - Activity Category
    - Activity Subcategory
    - Activity Type
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with MetaSources and ActivityProducedBy columns
    mapping_df : pandas.DataFrame
        DataFrame with MetaSources, ActivityProducedBy, and all categorization columns
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with all categorization columns added
    """
    if mapping_df is None or "MetaSources" not in fbs_data.columns:
        print("Skipping GHG Source categorization enrichment - missing required data")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with comprehensive GHG categorization...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Initialize the new columns
    enriched_data['IPCC/UNFCCC Category'] = None
    enriched_data['Activity Category'] = None
    enriched_data['Activity Subcategory'] = None
    enriched_data['Activity Type'] = None
    
    matched_count = 0
    
    for idx, row in enriched_data.iterrows():
        meta_sources = row.get("MetaSources", "")
        activity_produced_by = row.get("ActivityProducedBy", "")
        
        if pd.isna(meta_sources) or not meta_sources:
            continue
        
        meta_sources_str = str(meta_sources).strip()
        activity_produced_by_str = str(activity_produced_by).strip() if pd.notna(activity_produced_by) else ""
        
        # Try to find a match in the mapping
        # First, try exact match with both MetaSources and ActivityProducedBy
        match = None
        
        if activity_produced_by_str:
            # Try exact match first
            match = mapping_df[
                (mapping_df['MetaSources'] == meta_sources_str) & 
                (mapping_df['ActivityProducedBy'] == activity_produced_by_str)
            ]
            # If no exact match, try matching just the source name (before the period)
            if match.empty:
                source_name = meta_sources_str.split('.')[0] if '.' in meta_sources_str else meta_sources_str
                match = mapping_df[
                    (mapping_df['MetaSources'] == source_name) & 
                    (mapping_df['ActivityProducedBy'] == activity_produced_by_str)
                ]
        else:
            # If ActivityProducedBy is empty, match only on MetaSources with empty ActivityProducedBy
            match = mapping_df[
                (mapping_df['MetaSources'] == meta_sources_str) & 
                (mapping_df['ActivityProducedBy'].isna() | (mapping_df['ActivityProducedBy'] == ''))
            ]
            
            # If no exact match, try matching just the source name
            if match.empty:
                source_name = meta_sources_str.split('.')[0] if '.' in meta_sources_str else meta_sources_str
                match = mapping_df[
                    (mapping_df['MetaSources'] == source_name) & 
                    (mapping_df['ActivityProducedBy'].isna() | (mapping_df['ActivityProducedBy'] == ''))
                ]
        
        if not match.empty:
            # Take the first match if there are multiple
            enriched_data.at[idx, 'IPCC/UNFCCC Category'] = match.iloc[0]['IPCC/UNFCCC Category']
            enriched_data.at[idx, 'Activity Category'] = match.iloc[0]['Activity Category']
            enriched_data.at[idx, 'Activity Subcategory'] = match.iloc[0]['Activity Subcategory']
            
            # Activity Type might be empty in the CSV
            activity_type = match.iloc[0].get('Activity Type', '')
            if pd.notna(activity_type) and activity_type:
                enriched_data.at[idx, 'Activity Type'] = activity_type
            
            matched_count += 1
    
    print(f"✓ Added comprehensive GHG categorization to {matched_count:,} records")
    print(f"  - IPCC/UNFCCC Category")
    print(f"  - Activity Category")
    print(f"  - Activity Subcategory")
    print(f"  - Activity Type (where applicable)")
    
    return enriched_data


def load_flowable_categorization(csv_path):
    """
    Load the flowable categorization CSV file.
    
    Parameters:
    -----------
    csv_path : str
        Path to the flowable categorization CSV file
        
    Returns:
    --------
    dict
        Dictionary mapping Flowable names to Gas category
    """
    if not os.path.exists(csv_path):
        print(f"Warning: Flowable categorization file not found at {csv_path}")
        return {}
    
    try:
        df = pd.read_csv(csv_path)
        
        # Create dictionary: Flowable -> Gas category
        flowable_to_gas = dict(zip(df['Flowable'], df['Gas Category']))
        
        print(f"✓ Loaded {len(flowable_to_gas)} flowable categorizations")
        return flowable_to_gas
    except Exception as e:
        print(f"Error loading flowable categorization: {e}")
        return {}


def enrich_with_gas_category(fbs_data, flowable_to_gas_dict):
    """
    Enrich FlowBySector data with Gas category.
    
    Maps Flowable names to their corresponding gas categories.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with Flowable column
    flowable_to_gas_dict : dict
        Dictionary mapping Flowable names to Gas category
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "Gas Category" column added
    """
    if "Flowable" not in fbs_data.columns:
        print("Skipping Gas category enrichment - Flowable column not found")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with Gas category...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Initialize the new column
    enriched_data['Gas Category'] = None
    
    matched_count = 0
    
    for idx, row in enriched_data.iterrows():
        flowable = row.get("Flowable", "")
        
        if pd.isna(flowable) or not flowable:
            continue
        
        flowable_str = str(flowable).strip()
        
        # Look up in the categorization
        if flowable_str in flowable_to_gas_dict:
            enriched_data.at[idx, 'Gas Category'] = flowable_to_gas_dict[flowable_str]
            matched_count += 1
    
    print(f"✓ Added Gas category to {matched_count:,} records")
    
    return enriched_data


def load_sector_classification(csv_path):
    """
    Load sector classification file to map USEEIO sector codes to names.
    
    Parameters:
    -----------
    csv_path : str
        Path to sector_classification.csv file
        
    Returns:
    --------
    dict
        Dictionary mapping sector code to sector name
    """
    if not os.path.exists(csv_path):
        print(f"Warning: Sector classification file not found at {csv_path}")
        return {}
    
    try:
        df = pd.read_csv(csv_path)
        # Create dictionary: Sector code -> Sector name
        code_to_name = dict(zip(df['Sector code'].astype(str), df['Sector name']))
        print(f"✓ Loaded {len(code_to_name)} sector classifications")
        return code_to_name
    except Exception as e:
        print(f"Error loading sector classification: {e}")
        return {}


def load_ipcc_ar5_100_gwp(parquet_path):
    """
    Load the IPCC Global Warming Potential factors.
    
    Filters IPCC data for specified indicator and context from config,
    then creates a lookup dictionary from Flow UUID to Characterization Factor.
    
    Parameters:
    -----------
    parquet_path : str
        Path to the IPCC parquet file
        
    Returns:
    --------
    dict
        Dictionary mapping Flow UUID to GWP characterization factor
    """
    if not os.path.exists(parquet_path):
        print(f"Warning: IPCC parquet file not found at {parquet_path}")
        return {}
    
    try:
        df = pd.read_parquet(parquet_path)
        
        # Filter using config parameters
        indicator = config.IPCC_INDICATOR
        context = config.IPCC_CONTEXT
        
        filtered = df[(df['Indicator'] == indicator) & (df['Context'] == context)]
        
        # Create dictionary: Flow UUID -> Characterization Factor
        uuid_to_gwp = dict(zip(filtered['Flow UUID'], filtered['Characterization Factor']))
        
        print(f"✓ Loaded {len(uuid_to_gwp)} {indicator} GWP factors (context: {context})")
        return uuid_to_gwp
    except Exception as e:
        print(f"Error loading IPCC GWP factors: {e}")
        return {}


def enrich_with_ar5_100_gwp(fbs_data, uuid_to_gwp_dict):
    """
    Enrich FlowBySector data with AR5-100 Global Warming Potentials.
    
    Maps Flow UUIDs to their AR5-100 GWP characterization factors,
    then calculates emissions in metric tons CO2 equivalent.
    
    For records with Unit = "kg CO2e", the values are already in CO2 equivalent,
    so GWP = 1.0 and we just convert kg to metric tons (divide by 1000).
    
    For records with Unit = "kg", we look up the GWP factor, multiply by FlowAmount,
    then convert to metric tons.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with FlowUUID, FlowAmount, and Unit columns
    uuid_to_gwp_dict : dict
        Dictionary mapping Flow UUID to AR5-100 GWP factor
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "AR5-100 GWP" and "Emissions (MTCO2e)" columns
    """
    if "FlowUUID" not in fbs_data.columns:
        print("Skipping AR5-100 GWP enrichment - FlowUUID column not found")
        return fbs_data.copy()
    
    if "FlowAmount" not in fbs_data.columns:
        print("Skipping AR5-100 GWP enrichment - FlowAmount column not found")
        return fbs_data.copy()
    
    if "Unit" not in fbs_data.columns:
        print("Skipping AR5-100 GWP enrichment - Unit column not found")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with AR5-100 GWP and calculating MTCO2e...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Initialize the new columns
    enriched_data['AR5-100 GWP'] = None
    enriched_data['Emissions (MTCO2e)'] = None
    
    matched_count = 0
    already_co2e_count = 0
    unmatched_flowables = set()
    
    for idx, row in enriched_data.iterrows():
        flow_uuid = row.get("FlowUUID", "")
        flow_amount = row.get("FlowAmount", 0)
        flowable = row.get("Flowable", "")
        unit = row.get("Unit", "")
        
        # Check if already in CO2e units
        if pd.notna(unit) and str(unit).strip() == "kg CO2e":
            # Already in CO2 equivalent, GWP = 1.0
            enriched_data.at[idx, 'AR5-100 GWP'] = 1.0
            
            # Just convert kg to metric tons (divide by 1000)
            if pd.notna(flow_amount) and flow_amount != 0:
                mtco2e = flow_amount / 1000.0
                enriched_data.at[idx, 'Emissions (MTCO2e)'] = mtco2e
            
            already_co2e_count += 1
            continue
        
        # For other units (typically "kg"), look up GWP
        # Skip if UUID is missing or n.a.
        if pd.isna(flow_uuid) or not flow_uuid or flow_uuid == "n.a.":
            if flowable and flowable != "n.a.":
                unmatched_flowables.add(str(flowable))
            continue
        
        flow_uuid_str = str(flow_uuid).strip()
        
        # Look up GWP factor
        if flow_uuid_str in uuid_to_gwp_dict:
            gwp = uuid_to_gwp_dict[flow_uuid_str]
            enriched_data.at[idx, 'AR5-100 GWP'] = gwp
            
            # Calculate emissions in MTCO2e
            # FlowAmount is in kg, multiply by GWP, then convert to metric tons (divide by 1000)
            if pd.notna(flow_amount) and flow_amount != 0:
                mtco2e = (flow_amount * gwp) / 1000.0
                enriched_data.at[idx, 'Emissions (MTCO2e)'] = mtco2e
            
            matched_count += 1
        else:
            if flowable and flowable != "n.a.":
                unmatched_flowables.add(str(flowable))
    
    total_enriched = matched_count + already_co2e_count
    print(f"✓ Added AR5-100 GWP to {total_enriched:,} records")
    print(f"  - From IPCC lookup (kg → MTCO2e): {matched_count:,}")
    print(f"  - Already in CO2e (kg CO2e → MTCO2e): {already_co2e_count:,}")
    print(f"✓ Calculated Emissions (MTCO2e) for {total_enriched:,} records")
    
    if unmatched_flowables:
        print(f"⚠ Warning: {len(unmatched_flowables)} flowables without AR5-100 GWP factors:")
        for flowable in sorted(unmatched_flowables):
            print(f"  - {flowable}")
    
    return enriched_data


def calculate_contribution_by_sector(fbs_data):
    """
    Calculate percentage contribution of each record to its USEEIO sector total.
    
    For each USEEIO sector, calculates what percentage each record's emissions
    contribute to the total emissions for that sector.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with USEEIO Sector Code and Emissions (MTCO2e) columns
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "Contribution to USEEIO Sector's Scope 1 (%)" column added
    """
    # Check for the column (try both old and new names for compatibility)
    useeio_col = None
    if "USEEIO Sector Code" in fbs_data.columns:
        useeio_col = "USEEIO Sector Code"
    elif "USEEIO" in fbs_data.columns:
        useeio_col = "USEEIO"
    else:
        print("Skipping contribution calculation - USEEIO Sector Code column not found")
        return fbs_data.copy()
    
    if "Emissions (MTCO2e)" not in fbs_data.columns:
        print("Skipping contribution calculation - Emissions (MTCO2e) column not found")
        return fbs_data.copy()
    
    print("Calculating contribution fractions by USEEIO sector...")
    
    # Make a copy to avoid modifying the original
    enriched_data = fbs_data.copy()
    
    # Calculate sector totals
    sector_totals = enriched_data.groupby(useeio_col)['Emissions (MTCO2e)'].sum()
    
    # Initialize the new column
    enriched_data["Contribution to USEEIO Sector's Scope 1 (%)"] = None
    
    # Calculate contribution as decimal (0-1) for each record
    for idx, row in enriched_data.iterrows():
        useeio_sector = row.get(useeio_col, '')
        mtco2e = row.get('Emissions (MTCO2e)', 0)
        
        if pd.isna(useeio_sector) or not useeio_sector:
            continue
        
        if pd.isna(mtco2e) or mtco2e == 0:
            enriched_data.at[idx, "Contribution to USEEIO Sector's Scope 1 (%)"] = 0.0
            continue
        
        # Get sector total
        if useeio_sector in sector_totals.index:
            sector_total = sector_totals[useeio_sector]
            if sector_total > 0:
                # Store as decimal (0-1) instead of percentage (0-100)
                contribution_decimal = mtco2e / sector_total
                enriched_data.at[idx, "Contribution to USEEIO Sector's Scope 1 (%)"] = contribution_decimal
    
    # Count records with contribution calculated
    contrib_count = enriched_data["Contribution to USEEIO Sector's Scope 1 (%)"].notna().sum()
    print(f"✓ Calculated contribution fractions for {contrib_count:,} records (stored as decimals 0-1)")
    
    return enriched_data


def enrich_with_useeio_sector_name(fbs_data, sector_code_to_name):
    """
    Add USEEIO Sector Name column based on USEEIO Sector Code.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with USEEIO column
    sector_code_to_name : dict
        Dictionary mapping sector codes to names
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "USEEIO Sector Name" column added
    """
    if "USEEIO" not in fbs_data.columns:
        print("Skipping USEEIO sector name enrichment - USEEIO column not found")
        return fbs_data.copy()
    
    if not sector_code_to_name:
        print("Warning: No sector classification data available")
        return fbs_data.copy()
    
    print("Enriching with USEEIO sector names...")
    
    enriched_data = fbs_data.copy()
    enriched_data['USEEIO Sector Name'] = enriched_data['USEEIO'].map(sector_code_to_name)
    
    # Count matches
    match_count = enriched_data['USEEIO Sector Name'].notna().sum()
    match_rate = (match_count / len(enriched_data)) * 100 if len(enriched_data) > 0 else 0
    print(f"✓ Matched {match_count:,} / {len(enriched_data):,} records ({match_rate:.1f}%)")
    
    return enriched_data


def rename_and_create_columns(fbs_data):
    """
    Rename columns to final names and create new emission columns.
    
    Renames:
    - USEEIO → USEEIO Sector Code
    - SectorProducedBy → NAICS Sector Code  
    - Subcategory → GHG Source Subcategory
    - PrimaryActivity → Activity
    - Flowable → Gas
    - Unit → FlowAmount Unit
    - chapter → US GHGI Chapter
    - table_id → US GHGI Table ID
    - desc → US GHGI Table Name
    - AttributionSources → Attribution Sources
    
    Creates:
    - Emissions (kg) from FlowAmount if Unit != "kg CO2e"
    - Emissions (kgCO2e) from FlowAmount if Unit == "kg CO2e"
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with original column names
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame with renamed columns and new emission columns
    """
    print("Renaming columns and creating emission columns...")
    
    enriched_data = fbs_data.copy()
    
    # Rename columns
    rename_map = {
        'USEEIO': 'USEEIO Sector Code',
        'SectorProducedBy': 'NAICS Sector Code',
        # Note: 'Subcategory' removed from rename - now enriched as 'Activity Subcategory' in Step 7.6
        'PrimaryActivity': 'Activity',
        'Flowable': 'Gas',
        'Unit': 'FlowAmount Unit',
        'chapter': 'US GHGI Chapter',
        'table_id': 'US GHGI Table ID',
        'desc': 'US GHGI Table Name',
        'AttributionSources': 'Attribution Sources'
    }
    
    enriched_data.rename(columns=rename_map, inplace=True)
    
    # Create new emission columns based on FlowAmount Unit (before renaming)
    # Note: We need to use the original 'Unit' column which is now 'FlowAmount Unit'
    if 'FlowAmount' in enriched_data.columns and 'FlowAmount Unit' in enriched_data.columns:
        enriched_data['Emissions (kg)'] = enriched_data.apply(
            lambda row: row['FlowAmount'] if row['FlowAmount Unit'] != 'kg CO2e' else None,
            axis=1
        )
        enriched_data['Emissions (kgCO2e)'] = enriched_data.apply(
            lambda row: row['FlowAmount'] if row['FlowAmount Unit'] == 'kg CO2e' else None,
            axis=1
        )
        
        # Count how many of each
        kg_count = enriched_data['Emissions (kg)'].notna().sum()
        kgco2e_count = enriched_data['Emissions (kgCO2e)'].notna().sum()
        print(f"✓ Created Emissions (kg): {kg_count:,} records")
        print(f"✓ Created Emissions (kgCO2e): {kgco2e_count:,} records")
    
    print(f"✓ Renamed {len([k for k in rename_map.keys() if k in fbs_data.columns])} columns")
    
    return enriched_data


def load_method_yaml(yaml_path):
    """
    Load the method YAML file to extract PrimaryActivity information.
    
    Always loads from m1 file regardless of whether m2 is specified,
    since m1 contains all the PrimaryActivity definitions.
    
    Parameters:
    -----------
    yaml_path : str
        Path to the method YAML file (m1 or m2)
        
    Returns:
    --------
    str or None
        Raw YAML content as text from m1 file, or None if file doesn't exist
    """
    # Always use m1 file for PrimaryActivity extraction
    m1_yaml_path = yaml_path.replace('GHG_national_m2', 'GHG_national_m1')
    
    if not os.path.exists(m1_yaml_path):
        print(f"Warning: Method YAML file not found at {m1_yaml_path}")
        return None
    
    try:
        with open(m1_yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"OK - Successfully loaded method YAML from: {m1_yaml_path}")
        return content
    except Exception as e:
        print(f"Error loading YAML file {m1_yaml_path}: {e}")
        return None





def extract_primary_activities_mapping(yaml_content):
    """
    Extract PrimaryActivity information from the m1 method YAML content using simple text parsing.
    
    This creates a mapping: source_name.activity_set → dict with 'full' and 'short' activity lists
    If there's no activity_set, just uses source_name → dict with 'full' and 'short' activity lists
    
    The 'full' list contains original activity names (e.g., "General Aviation Aircraft Aviation Gasoline")
    The 'short' list contains mapped/shortened names (e.g., "General Aviation Aircraft")
    
    Resolves YAML anchor references (e.g., *mobile, *stationary_combustion).
    
    Parameters:
    -----------
    yaml_content : str
        Raw m1 YAML content as text
        
    Returns:
    --------
    dict
        Mapping of "source_name.activity_set" or "source_name" → {'full': [...], 'short': [...]}
    """
    if not yaml_content:
        return {}
    
    print("Extracting PrimaryActivity information from m1 method YAML...")
    
    mapping = {}
    anchor_definitions = {}  # Store anchor definitions: {anchor_name: source_name}
    lines = yaml_content.split('\n')
    
    # First pass: identify anchor definitions (e.g., "EPA_GHGI_T_3_14: &mobile")
    for line in lines:
        if line.startswith('  ') and not line.startswith('    '):
            # Source level (2 spaces)
            match = re.match(r'\s{2}([A-Z_0-9]+):\s*&(\w+)', line)
            if match:
                source_name = match.group(1).strip()
                anchor_name = match.group(2).strip()
                anchor_definitions[anchor_name] = source_name
                print(f"  Found anchor definition: &{anchor_name} defined at {source_name}")
    
    current_source = None
    current_activity_set = None
    in_source_names = False
    in_activity_sets = False
    in_selection_fields = False
    collecting_primary_activities = False
    primary_activities_full = []  # Original full names
    primary_activities_short = []  # Mapped short names
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        
        # Detect source_names section
        if stripped.startswith('source_names:'):
            in_source_names = True
            continue
        
        # End of source_names section (back to top level)
        if in_source_names and line.startswith(' ') == False and ':' in line:
            in_source_names = False
            break
        
        if not in_source_names:
            continue
            
        # Parse source name (2-space indent under source_names)
        if line.startswith('  ') and not line.startswith('    ') and ':' in line:
            # Save previous source/activity_set data
            if current_source and (primary_activities_full or primary_activities_short):
                key = f"{current_source}.{current_activity_set}" if current_activity_set else current_source
                mapping[key] = {
                    'full': primary_activities_full.copy(),
                    'short': primary_activities_short.copy()
                }
            
            # Reset for new source
            current_source = line.split(':')[0].strip()
            current_activity_set = None
            in_activity_sets = False
            in_selection_fields = False
            collecting_primary_activities = False
            primary_activities_full = []
            primary_activities_short = []
            
            # Check if this source uses an anchor reference (e.g., "*mobile")
            rest_of_line = line.split(':', 1)[1].strip()
            anchor_ref_match = re.match(r'\*(\w+)', rest_of_line)
            if anchor_ref_match:
                anchor_name = anchor_ref_match.group(1)
                if anchor_name in anchor_definitions:
                    # This source references another source's definition
                    ref_source = anchor_definitions[anchor_name]
                    print(f"  {current_source} references *{anchor_name} (copying from {ref_source})")
                    
                    # Copy all mappings from the referenced source after this pass completes
                    # Mark it for later copying
                    mapping[f"__ANCHOR_REF__{current_source}"] = ref_source
        
        # Check for activity_sets
        elif stripped.startswith('activity_sets:'):
            in_activity_sets = True
            in_selection_fields = False
            collecting_primary_activities = False
            
        # Parse activity set name (4-space indent under activity_sets)
        elif in_activity_sets and line.startswith('      ') and not line.startswith('        ') and ':' in line:
            # Save previous activity set data
            if current_source and (primary_activities_full or primary_activities_short):
                key = f"{current_source}.{current_activity_set}" if current_activity_set else current_source
                mapping[key] = {
                    'full': primary_activities_full.copy(),
                    'short': primary_activities_short.copy()
                }
            
            # Reset for new activity set
            current_activity_set = line.split(':')[0].strip()
            in_selection_fields = False
            collecting_primary_activities = False
            primary_activities_full = []
            primary_activities_short = []
        
        # Check for selection_fields
        elif stripped.startswith('selection_fields:'):
            in_selection_fields = True
            collecting_primary_activities = False
        
        # Extract PrimaryActivity line
        elif in_selection_fields and 'PrimaryActivity:' in line:
            # Check if there's a value on the same line
            value_part = line.split('PrimaryActivity:')[-1].strip()
            
            # Remove inline comments
            if '#' in value_part:
                value_part = value_part.split('#')[0].strip()
            
            if value_part and not value_part.startswith('-') and not value_part.startswith('{'):
                # Single-line value (no hierarchy, same for both)
                primary_activities_full.append(value_part)
                primary_activities_short.append(value_part)
                collecting_primary_activities = False
            else:
                # Multi-line list will follow
                collecting_primary_activities = True
        
        # Collect PrimaryActivity list items
        elif collecting_primary_activities:
            if stripped.startswith('-'):
                # List item format: "- Activity Name" (no hierarchy, same for both)
                activity = stripped[1:].strip()
                # Remove inline comments
                if '#' in activity:
                    activity = activity.split('#')[0].strip()
                if activity:
                    primary_activities_full.append(activity)
                    primary_activities_short.append(activity)
            elif ':' in stripped and not stripped.startswith('-') and not stripped.startswith('attribution'):
                # Dictionary format: "Original Activity Name: Mapped Name"
                # Store KEY in full, VALUE in short
                if 'attribution_method' not in stripped:
                    parts = stripped.split(':', 1)
                    # Check if this is actually another selection field (stop collecting)
                    field_name = parts[0].strip()
                    if field_name in ['FlowName', 'Class', 'Unit', 'Location', 'Description', 'ActivityProducedBy', 'ActivityConsumedBy', 'SectorProducedBy', 'SectorConsumedBy']:
                        collecting_primary_activities = False
                    else:
                        # Full name (key) and short name (value)
                        full_name = parts[0].strip()
                        short_name = parts[1].strip() if len(parts) > 1 else full_name
                        
                        # Remove inline comments
                        if '#' in full_name:
                            full_name = full_name.split('#')[0].strip()
                        if '#' in short_name:
                            short_name = short_name.split('#')[0].strip()
                        
                        if full_name:
                            primary_activities_full.append(full_name)
                            primary_activities_short.append(short_name if short_name else full_name)
            elif in_selection_fields and stripped and not stripped.startswith('#'):
                # Stop collecting if we hit another field
                if 'attribution' in stripped.lower() or 'selection' in stripped.lower():
                    collecting_primary_activities = False
    
    # Save the last source/activity_set
    if current_source and (primary_activities_full or primary_activities_short):
        key = f"{current_source}.{current_activity_set}" if current_activity_set else current_source
        mapping[key] = {
            'full': primary_activities_full.copy(),
            'short': primary_activities_short.copy()
        }
    
    # Resolve anchor references: copy mappings from referenced sources
    anchor_refs_to_resolve = [(k, v) for k, v in mapping.items() if k.startswith("__ANCHOR_REF__")]
    for anchor_key, ref_source in anchor_refs_to_resolve:
        target_source = anchor_key.replace("__ANCHOR_REF__", "")
        # Remove the marker
        del mapping[anchor_key]
        
        # Copy all activity_sets from the referenced source
        for key, values_dict in list(mapping.items()):
            if key == ref_source or key.startswith(ref_source + '.'):
                if '.' in key:
                    # It's an activity_set
                    activity_set = key.split('.', 1)[1]
                    new_key = f"{target_source}.{activity_set}"
                else:
                    # It's a base source
                    new_key = target_source
                mapping[new_key] = {
                    'full': values_dict['full'].copy(),
                    'short': values_dict['short'].copy()
                }
                print(f"    Copied {key} -> {new_key}: {' | '.join(values_dict['full'])}")
    
    print(f"OK - Extracted PrimaryActivity mappings for {len(mapping)} source/activity combinations")
    
    # Print some examples for debugging
    test_keys = [
        'EPA_GHGI_T_2_1.electric_power', 
        'EPA_GHGI_T_4_127.refrigerants', 
        'EPA_GHGI_T_4_109', 
        'EPA_GHGI_T_2_1.carbonate_use',
        'EPA_GHGI_T_3_15.direct_gasoline',  # Uses *mobile anchor
        'EPA_GHGI_T_3_9.residential',  # Uses *stationary_combustion anchor
        'EPA_GHGI_T_3_13.direct_petroleum'  # Has hierarchy mapping
    ]
    for key in test_keys:
        if key in mapping:
            full_activities = ' | '.join(mapping[key]['full'])
            short_activities = ' | '.join(mapping[key]['short'])
            if full_activities == short_activities:
                print(f"  {key} -> {full_activities}")
            else:
                print(f"  {key}:")
                print(f"    Full:  {full_activities[:150]}...")
                print(f"    Short: {short_activities[:150]}...")
    
    return mapping


def _save_activity_mapping(mapping, source_name, activity_set, primary_activities, attribution_method):
    """Helper function - no longer needed with simplified approach."""
    pass


def _extract_primary_activities_from_line(line, lines, line_index):
    """Helper function - no longer needed with simplified approach."""
    pass


def _parse_primary_activity_value(pa_value):
    """
    Parse PrimaryActivity values from YAML in various formats.
    
    Parameters:
    -----------
    pa_value : str, list, or dict
        PrimaryActivity value from YAML
        
    Returns:
    --------
    list
        List of primary activity names
    """
    primary_activities = []
    
    if isinstance(pa_value, list):
        primary_activities.extend(pa_value)
    elif isinstance(pa_value, dict):
        # Handle dictionary format like {"activity_name": "mapped_name"}
        # or {"Activity Name: Description": "Activity Name"}
        for key, value in pa_value.items():
            # Use the key as the primary activity name, but clean up format
            if ':' in key:
                # Split on first colon and take the part before it
                activity_name = key.split(':')[0].strip()
            else:
                activity_name = key.strip()
            primary_activities.append(activity_name)
    elif isinstance(pa_value, str):
        primary_activities.append(pa_value)
    
    return primary_activities


def _deduplicate_and_simplify_activities(activities):
    """
    Deduplicate and simplify a list of primary activities.
    
    Rules:
    1. Remove exact duplicates (case-insensitive)
    2. If all activities share a common base term (e.g., "Fuel Oil"), return just that term
    3. Examples:
       - "Natural gas Industrial - Manufacturing | Natural Gas Industrial - Manufacturing" → "Natural gas Industrial - Manufacturing"
       - "Fuel Oil Commercial | Fuel Oil Industrial" → "Fuel Oil"
       - "Commercial Refrigeration | Industrial Process Refrigeration" → "Refrigeration"
    
    Parameters:
    -----------
    activities : list
        List of activity name strings
        
    Returns:
    --------
    str
        Simplified activity string (joined with " | " if multiple remain)
    """
    if not activities:
        return None
    
    # Step 1: Deduplicate (case-insensitive)
    seen = {}
    unique_activities = []
    for activity in activities:
        activity_lower = activity.lower().strip()
        if activity_lower not in seen:
            seen[activity_lower] = activity.strip()
            unique_activities.append(activity.strip())
    
    if len(unique_activities) == 1:
        return unique_activities[0]
    
    # Step 2: Check for common base terms
    # Split each activity into words and find common terms
    activity_words = [set(act.lower().split()) for act in unique_activities]
    
    # Find words that appear in ALL activities
    if activity_words:
        common_words = set.intersection(*activity_words)
        
        # Special cases: if we have words like "refrigeration", "fuel", etc.
        priority_terms = ['refrigeration', 'fuel oil', 'natural gas', 'coal', 'wood']
        
        for term in priority_terms:
            term_words = set(term.split())
            if term_words.issubset(common_words):
                # Return the capitalized term from the original activities
                # Find it in one of the original activities to preserve capitalization
                for activity in unique_activities:
                    activity_lower = activity.lower()
                    if term in activity_lower:
                        # Extract the term with original capitalization
                        start_idx = activity_lower.index(term)
                        return activity[start_idx:start_idx + len(term)].strip()
    
    # If no simplification possible, return all unique activities joined
    return ' | '.join(unique_activities)


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
    
    enriched_count = 0
    direct_count = 0
    yaml_count = 0
    processed_count = 0
    
    for idx, row in enriched_data.iterrows():
        attribution_sources = row.get("AttributionSources", "")
        activity_produced_by = row.get("ActivityProducedBy", "")
        meta_sources = row.get("MetaSources", "")
        
        # Check if AttributionSources is "direct"
        if pd.notna(attribution_sources) and str(attribution_sources).strip().lower() == "direct":
            # Exception for "Semiconductors" - use YAML PrimaryActivity values instead of ActivityProducedBy
            activity_str = str(activity_produced_by).strip() if pd.notna(activity_produced_by) else ""
            if activity_str.lower() == "semiconductors":
                # For Semiconductors, use the YAML mapping approach instead of direct attribution
                # This will fall through to the YAML mapping code below
                pass
            # For other direct attribution, look up ActivityProducedBy in the YAML mapping
            # to find ALL original full activity names from the YAML keys that map to this short name
            elif pd.notna(activity_produced_by) and activity_produced_by and pd.notna(meta_sources) and meta_sources:
                meta_sources_str = str(meta_sources).strip()
                
                # Try to find this activity in the mapping for this source
                # Collect ALL full names that map to this short name
                found_activities = []
                
                if meta_sources_str in primary_activity_mapping:
                    activity_dict = primary_activity_mapping[meta_sources_str]
                    # Look for the activity in the 'short' list
                    # Collect all 'full' names that map to this short name
                    if activity_dict['short']:
                        for i, short_name in enumerate(activity_dict['short']):
                            if short_name.strip().lower() == activity_str.lower():
                                # Found a match - collect the corresponding full name
                                if i < len(activity_dict['full']):
                                    found_activities.append(activity_dict['full'][i])
                
                # If not found, try matching just the source name
                if not found_activities:
                    source_name = meta_sources_str.split('.')[0] if '.' in meta_sources_str else meta_sources_str
                    if source_name in primary_activity_mapping:
                        activity_dict = primary_activity_mapping[source_name]
                        if activity_dict['short']:
                            for i, short_name in enumerate(activity_dict['short']):
                                if short_name.strip().lower() == activity_str.lower():
                                    if i < len(activity_dict['full']):
                                        found_activities.append(activity_dict['full'][i])
                
                if found_activities:
                    # Join all found activities with " | "
                    enriched_data.at[idx, 'PrimaryActivity'] = ' | '.join(found_activities)
                    enriched_count += 1
                    direct_count += 1
                else:
                    # Fallback: use ActivityProducedBy if we can't find it in the mapping
                    enriched_data.at[idx, 'PrimaryActivity'] = activity_str
                    enriched_count += 1
                    direct_count += 1
                continue
            else:
                continue
        
        # Otherwise, use YAML mapping
        if pd.isna(meta_sources) or not meta_sources:
            continue
        
        processed_count += 1
        meta_sources_str = str(meta_sources).strip()
        
        # Try exact match first (with activity_set)
        if meta_sources_str in primary_activity_mapping:
            activity_dict = primary_activity_mapping[meta_sources_str]
            if activity_dict['full']:
                simplified = _deduplicate_and_simplify_activities(activity_dict['full'])
                if simplified:
                    enriched_data.at[idx, 'PrimaryActivity'] = simplified
                    enriched_count += 1
                    yaml_count += 1
                continue
        
        # Try matching just the source name (without activity_set)
        source_name = meta_sources_str.split('.')[0] if '.' in meta_sources_str else meta_sources_str
        
        if source_name in primary_activity_mapping:
            activity_dict = primary_activity_mapping[source_name]
            if activity_dict['full']:
                simplified = _deduplicate_and_simplify_activities(activity_dict['full'])
                if simplified:
                    enriched_data.at[idx, 'PrimaryActivity'] = simplified
                    enriched_count += 1
                    yaml_count += 1
    
    print(f"✓ Processed {processed_count:,} records with MetaSources (non-direct)")
    print(f"✓ Added PrimaryActivity from direct attribution: {direct_count:,} records")
    print(f"✓ Added PrimaryActivity from YAML mapping: {yaml_count:,} records")
    print(f"✓ Total PrimaryActivity enrichment: {enriched_count:,} records")
    
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
    
    # Extract meta_id from MetaSources for matching
    fbs_data["__meta_id"] = fbs_data["MetaSources"].apply(_extract_meta_id)
    
    # Count how many records have extractable meta_ids
    records_with_meta = fbs_data["__meta_id"].notna().sum()
    print(f"Found {records_with_meta:,} records with extractable EPA GHGI table references")
    
    # Perform left join to add metadata columns
    merged = fbs_data.merge(meta_map, left_on="__meta_id", right_on="meta_id", how="left")
    
    # Clean up temporary columns
    merged.drop(columns=[c for c in ["meta_id", "__meta_id"] if c in merged.columns], inplace=True)
    
    # Count successful matches
    records_with_ipcc = merged["IPCC_Category"].notna().sum() if "IPCC_Category" in merged.columns else 0
    match_rate = (records_with_ipcc / len(merged)) * 100
    
    print(f"✓ Successfully matched {records_with_ipcc:,} records with IPCC categories ({match_rate:.1f}%)")
    
    return merged


def compare_with_reference(fbs_calculated, fbs_reference):
    """
    Compare generated FlowBySector data with reference parquet file.
    
    This performs a sanity check to ensure the generated data matches the 
    reference data that was previously downloaded, excluding any new columns
    we may have added in the generated version.
    
    Parameters:
    -----------
    fbs_calculated : pandas.DataFrame
        Newly generated FlowBySector data
    fbs_reference : pandas.DataFrame
        Reference FlowBySector data from parquet file
        
    Returns:
    --------
    dict
        Comparison results with match status and details
    """
    print("\n" + "="*80)
    print("SANITY CHECK: Comparing Generated vs Reference Data")
    print("="*80)
    
    results = {
        "row_count_match": False,
        "column_match": False,
        "data_match": False,
        "details": []
    }
    
    # Clean Location formatting in reference (remove Excel string formatting)
    if "Location" in fbs_reference.columns:
        fbs_reference = fbs_reference.copy()
        fbs_reference["Location"] = fbs_reference["Location"].astype(str).str.replace('="', '').str.replace('"', '')
    
    # 1. Compare row counts
    print(f"\n1. Row Count Comparison:")
    print(f"   Generated: {len(fbs_calculated):,} rows")
    print(f"   Reference: {len(fbs_reference):,} rows")
    
    if len(fbs_calculated) == len(fbs_reference):
        print("   ✓ Row counts match!")
        results["row_count_match"] = True
    else:
        diff = len(fbs_calculated) - len(fbs_reference)
        print(f"   ✗ Row count mismatch: {diff:+,} rows difference")
        results["details"].append(f"Row count difference: {diff:+,}")
        
        # Identify missing/extra rows
        if "FlowUUID" in fbs_calculated.columns and "FlowUUID" in fbs_reference.columns:
            calc_uuids = set(fbs_calculated["FlowUUID"])
            ref_uuids = set(fbs_reference["FlowUUID"])
            
            only_in_ref = ref_uuids - calc_uuids
            only_in_calc = calc_uuids - ref_uuids
            
            if only_in_ref:
                print(f"\n   FlowUUIDs only in reference ({len(only_in_ref)}):")
                # Show first 10 with their MetaSource if available
                for uuid in list(only_in_ref)[:10]:
                    row = fbs_reference[fbs_reference["FlowUUID"] == uuid].iloc[0]
                    meta_source = row.get("MetaSources", "N/A")
                    flowable = row.get("Flowable", "N/A")
                    sector = row.get("SectorProducedBy", "N/A")
                    print(f"     - {uuid}")
                    print(f"       MetaSource: {meta_source}")
                    print(f"       Flowable: {flowable}, Sector: {sector}")
                if len(only_in_ref) > 10:
                    print(f"     ... and {len(only_in_ref) - 10} more")
            
            if only_in_calc:
                print(f"\n   FlowUUIDs only in calculated ({len(only_in_calc)}):")
                for uuid in list(only_in_calc)[:10]:
                    row = fbs_calculated[fbs_calculated["FlowUUID"] == uuid].iloc[0]
                    meta_source = row.get("MetaSources", "N/A")
                    flowable = row.get("Flowable", "N/A")
                    sector = row.get("SectorProducedBy", "N/A")
                    print(f"     - {uuid}")
                    print(f"       MetaSource: {meta_source}")
                    print(f"       Flowable: {flowable}, Sector: {sector}")
                if len(only_in_calc) > 10:
                    print(f"     ... and {len(only_in_calc) - 10} more")
    
    # 2. Compare columns (using reference columns as baseline)
    print(f"\n2. Column Comparison:")
    ref_cols = set(fbs_reference.columns)
    calc_cols = set(fbs_calculated.columns)
    
    common_cols = sorted(ref_cols & calc_cols)
    only_in_calc = sorted(calc_cols - ref_cols)
    only_in_ref = sorted(ref_cols - calc_cols)
    
    print(f"   Common columns: {len(common_cols)}")
    print(f"   Only in generated: {len(only_in_calc)}")
    if only_in_calc:
        print(f"     {only_in_calc}")
    print(f"   Only in reference: {len(only_in_ref)}")
    if only_in_ref:
        print(f"     {only_in_ref}")
    
    if len(only_in_ref) == 0:
        print("   ✓ All reference columns present in generated data!")
        results["column_match"] = True
    else:
        print("   ✗ Some reference columns missing from generated data")
        results["details"].append(f"Missing columns: {only_in_ref}")
    
    # 3. Compare data values for common columns
    if len(fbs_calculated) == len(fbs_reference) and common_cols:
        print(f"\n3. Data Value Comparison (for {len(common_cols)} common columns):")
        
        # Sort both dataframes identically for row-by-row comparison
        # Use common columns for sorting
        sort_cols = [col for col in ["Class", "SourceName", "Flowable", "SectorProducedBy", "Location", "Year"] 
                     if col in common_cols]
        
        if sort_cols:
            fbs_calc_sorted = fbs_calculated[common_cols].sort_values(by=sort_cols).reset_index(drop=True)
            fbs_ref_sorted = fbs_reference[common_cols].sort_values(by=sort_cols).reset_index(drop=True)
            
            # Compare column by column
            mismatches = {}
            for col in common_cols:
                try:
                    # Handle numeric columns
                    if pd.api.types.is_numeric_dtype(fbs_calc_sorted[col]) and pd.api.types.is_numeric_dtype(fbs_ref_sorted[col]):
                        # Use relative tolerance for floating point comparison
                        diff = ~pd.isna(fbs_calc_sorted[col]) & ~pd.isna(fbs_ref_sorted[col]) & \
                               ~pd.Series(pd.np.isclose(fbs_calc_sorted[col], fbs_ref_sorted[col], rtol=1e-9, atol=1e-12, equal_nan=True))
                        diff_count = diff.sum()
                    else:
                        # Use exact match for non-numeric
                        diff = (fbs_calc_sorted[col].astype(str) != fbs_ref_sorted[col].astype(str)) & \
                               ~(fbs_calc_sorted[col].isna() & fbs_ref_sorted[col].isna())
                        diff_count = diff.sum()
                    
                    if diff_count > 0:
                        mismatches[col] = diff_count
                except Exception as e:
                    print(f"   Warning: Could not compare column '{col}': {e}")
            
            if not mismatches:
                print("   ✓ All data values match between generated and reference!")
                results["data_match"] = True
            else:
                print(f"   ✗ Found mismatches in {len(mismatches)} columns:")
                for col, count in sorted(mismatches.items(), key=lambda x: -x[1])[:10]:  # Show top 10
                    print(f"     - {col}: {count:,} differing values")
                results["details"].append(f"Value mismatches in {len(mismatches)} columns")
        else:
            print("   ⚠️  Cannot compare values - no common sortable columns")
            results["details"].append("No common columns for value comparison")
    else:
        print(f"\n3. Data Value Comparison: Skipped (row count mismatch or no common columns)")
    
    # 4. Overall result
    print("\n" + "="*80)
    if results["row_count_match"] and results["column_match"] and results["data_match"]:
        print("✓✓✓ SANITY CHECK PASSED ✓✓✓")
        print("Generated data matches reference parquet file!")
    else:
        print("⚠️  SANITY CHECK: Differences detected")
        if results["details"]:
            print("\nIssues found:")
            for detail in results["details"]:
                print(f"  - {detail}")
        
        # Known issue note
        if not results["row_count_match"]:
            print("\n📝 Known Issue:")
            print("   There may be 2 extra rows in the reference from EPA_GHGI_T_4_64:")
            print("   - FlowUUID: b79859f9-9979-3708-9390-a3d6c0690561")
            print("   - FlowUUID: abbacdaf-9d6d-3805-bd10-d35905d7dff8")
            print("   This is a known discrepancy between FlowSA versions.")
    print("="*80 + "\n")
    
    return results


def validate_data(df, model_name):
    """
    Validate enriched data for common issues.
    
    Checks:
    - Missing values in key columns
    - Negative flow amounts (if configured)
    - Data types
    - Value ranges
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data to validate
    model_name : str
        Model name for logging
        
    Returns:
    --------
    bool
        True if validation passes, False otherwise
    """
    if not config.ENABLE_VALIDATION:
        print("Data validation skipped (ENABLE_VALIDATION=False)")
        return True
    
    print(f"\nValidating data for model: {model_name}")
    
    issues_found = False
    
    # Check for missing values in key columns
    key_columns = ['USEEIO Sector Code', 'Activity Category', 'Gas Category', 
                   'Emissions (MTCO2e)', "Contribution to USEEIO Sector's Scope 1 (%)"]
    
    for col in key_columns:
        if col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_pct = (missing_count / len(df)) * 100
                print(f"⚠ {col}: {missing_count:,} missing values ({missing_pct:.1f}%)")
                issues_found = True
    
    # Check for negative flow amounts
    if config.FLAG_NEGATIVE_FLOWS and 'Emissions (MTCO2e)' in df.columns:
        negative_count = (df['Emissions (MTCO2e)'] < 0).sum()
        if negative_count > 0:
            print(f"⚠ Found {negative_count:,} negative emission values")
            issues_found = True
    
    # Check for very small values
    if 'Emissions (MTCO2e)' in df.columns:
        tiny_count = ((df['Emissions (MTCO2e)'] > 0) & 
                     (df['Emissions (MTCO2e)'] < config.MIN_FLOW_AMOUNT)).sum()
        if tiny_count > 0:
            print(f"ℹ Found {tiny_count:,} very small emission values (< {config.MIN_FLOW_AMOUNT})")
    
    if not issues_found:
        print("✓ Data validation passed - no issues found")
        return True
    else:
        print("⚠ Data validation found issues - review warnings above")
        return False


def load_industry_output(csv_path):
    """
    Load industry output data (x.csv) for normalization.
    
    Parameters:
    -----------
    csv_path : str
        Path to x.csv file (USEEIO industry output in dollars)
        
    Returns:
    --------
    dict
        Dictionary mapping USEEIO sector code (without /US suffix) to output value in USD
    """
    print(f"Loading industry output data from: {csv_path}")
    
    # Read CSV with first column as index
    df = pd.read_csv(csv_path, index_col=0)
    
    # Strip "/US" suffix from index to get clean USEEIO codes
    df.index = df.index.str.replace('/US', '', regex=False)
    
    # First column contains the output values
    output_dict = df.iloc[:, 0].to_dict()
    
    print(f"✓ Loaded {len(output_dict):,} industry output values")
    print(f"  Total output: ${sum(output_dict.values()):,.0f}")
    print(f"  Min: ${min(output_dict.values()):,.0f}, Max: ${max(output_dict.values()):,.0f}")
    
    return output_dict


def load_market_share_matrix(csv_path):
    """
    Load V_n market share matrix for industry-to-commodity transformation.
    
    Parameters:
    -----------
    csv_path : str
        Path to V_n.csv file (market share matrix: industries × commodities)
        
    Returns:
    --------
    pandas.DataFrame
        Market share matrix with industry codes as rows, commodity codes as columns
    """
    print(f"Loading market share matrix from: {csv_path}")
    
    # Read CSV with first column as index
    df = pd.read_csv(csv_path, index_col=0)
    
    # Strip "/US" suffix from both index (industries) and columns (commodities)
    df.index = df.index.str.replace('/US', '', regex=False)
    df.columns = df.columns.str.replace('/US', '', regex=False)
    
    print(f"✓ Loaded V_n matrix: {len(df)} industries × {len(df.columns)} commodities")
    
    # Validate: each row should sum to approximately 1.0
    row_sums = df.sum(axis=1)
    max_deviation = abs(row_sums - 1.0).max()
    
    if max_deviation > 0.01:  # Allow 1% deviation
        print(f"  ⚠ Warning: Maximum row sum deviation from 1.0: {max_deviation:.4f}")
    else:
        print(f"  ✓ Row sums validated (max deviation: {max_deviation:.6f})")
    
    return df


def normalize_emissions_by_output(df, industry_output_dict):
    """
    Normalize emissions by industry output to get emission intensities (kg/USD).
    
    This creates emission intensity coefficients that can then be allocated
    to commodities based on market shares.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with emissions in kg
    industry_output_dict : dict
        Dictionary mapping USEEIO sector codes to output values in USD
        
    Returns:
    --------
    pandas.DataFrame
        Data with added 'Emissions Intensity (kg/USD)' column
    """
    print("Normalizing emissions by industry output...")
    
    # Create copy to avoid modifying original
    df_normalized = df.copy()
    
    # Map output values to each record
    df_normalized['Industry Output (USD)'] = df_normalized['USEEIO Sector Code'].map(industry_output_dict)
    
    # Check for missing mappings
    missing_count = df_normalized['Industry Output (USD)'].isna().sum()
    if missing_count > 0:
        missing_codes = df_normalized[df_normalized['Industry Output (USD)'].isna()]['USEEIO Sector Code'].unique()
        print(f"  ⚠ Warning: {missing_count:,} records have missing industry output values")
        print(f"    Missing USEEIO codes: {', '.join(sorted(missing_codes)[:10])}")
        if len(missing_codes) > 10:
            print(f"    ... and {len(missing_codes) - 10} more")
    
    # Calculate emission intensity (kg emissions per dollar of output)
    # Only for records with valid output values
    valid_mask = df_normalized['Industry Output (USD)'].notna() & (df_normalized['Industry Output (USD)'] > 0)
    
    emissions_intensity_col = get_emissions_intensity_col()
    df_normalized.loc[valid_mask, emissions_intensity_col] = (
        df_normalized.loc[valid_mask, 'Emissions (kg)'] / 
        df_normalized.loc[valid_mask, 'Industry Output (USD)']
    )
    
    # Log statistics
    valid_count = valid_mask.sum()
    total_kg = df_normalized.loc[valid_mask, 'Emissions (kg)'].sum()
    total_output = df_normalized.loc[valid_mask, 'Industry Output (USD)'].sum()
    avg_intensity = total_kg / total_output if total_output > 0 else 0
    
    print(f"✓ Calculated emission intensities for {valid_count:,} records")
    print(f"  Total emissions: {total_kg:,.0f} kg")
    print(f"  Total output: ${total_output:,.0f}")
    print(f"  Average intensity: {avg_intensity:.6e} kg/USD")
    
    return df_normalized


def transform_to_commodity_form(df_normalized, market_share_matrix, sector_code_to_name):
    """
    Transform industry-form emissions to commodity-form using V_n market share matrix.
    
    Process:
    1. For each industry USEEIO code, get its market share row from V_n
    2. Multiply emission intensity by market shares to allocate to commodities
    3. Create new records with commodity USEEIO codes
    4. Aggregate by commodity code and all other dimensions
    5. Recalculate kgCO2e and MTCO2e
    
    Parameters:
    -----------
    df_normalized : pandas.DataFrame
        Normalized data with emission intensities
    market_share_matrix : pandas.DataFrame
        V_n matrix (industries × commodities)
    sector_code_to_name : dict
        Mapping of USEEIO sector codes to names (for commodity enrichment)
        
    Returns:
    --------
    pandas.DataFrame
        Commodity-form data with recalculated emissions
    """
    print("Transforming to commodity form using V_n matrix...")
    
    # Only process records with valid intensities
    emissions_intensity_col = get_emissions_intensity_col()
    valid_mask = df_normalized[emissions_intensity_col].notna()
    df_to_transform = df_normalized[valid_mask].copy()
    
    print(f"  Processing {len(df_to_transform):,} records with valid emission intensities")
    
    # List to collect commodity records
    commodity_records = []
    
    # Group by industry USEEIO code for efficient processing
    grouped = df_to_transform.groupby('USEEIO Sector Code')
    
    processed_industries = 0
    total_industries = len(grouped)
    
    for industry_code, industry_group in grouped:
        processed_industries += 1
        
        if processed_industries % 50 == 0:
            print(f"  Progress: {processed_industries}/{total_industries} industries ({processed_industries/total_industries*100:.1f}%)")
        
        # Get market share row for this industry
        if industry_code not in market_share_matrix.index:
            # print(f"  ⚠ Industry code not in V_n matrix: {industry_code}")
            continue
        
        market_shares = market_share_matrix.loc[industry_code]
        
        # Get non-zero commodity allocations (skip zeros for efficiency)
        nonzero_commodities = market_shares[market_shares > 0]
        
        if len(nonzero_commodities) == 0:
            # print(f"  ⚠ No non-zero market shares for industry: {industry_code}")
            continue
        
        # For each record in this industry group
        emissions_intensity_col = get_emissions_intensity_col()
        for _, record in industry_group.iterrows():
            intensity = record[emissions_intensity_col]
            
            # Create new record for each commodity with non-zero market share
            for commodity_code, market_share in nonzero_commodities.items():
                # Create copy of record as dict to avoid duplicate column issues
                commodity_record = record.to_dict()
                
                # Replace industry code with commodity code
                commodity_record['USEEIO Sector Code'] = commodity_code
                
                # Transform emissions using V_n matrix (intensity * market_share * output)
                # The market share represents the portion of industry output allocated to this commodity
                commodity_record['Emissions (kg)'] = intensity * market_share * record['Industry Output (USD)']
                
                # Transform emission intensity using V_n matrix (intensity * market_share)
                # This allocates the intensity proportionally to each commodity
                commodity_record[emissions_intensity_col] = intensity * market_share
                
                # Remove Industry Output column (not meaningful for commodity form)
                if 'Industry Output (USD)' in commodity_record:
                    del commodity_record['Industry Output (USD)']
                
                commodity_records.append(commodity_record)
    
    print(f"✓ Created {len(commodity_records):,} commodity records")
    
    # Convert to DataFrame
    commodity_df = pd.DataFrame(commodity_records)
    
    # Aggregate by USEEIO Sector Code (commodity) + all other dimensions
    # NOTE: NAICS Sector Code is EXCLUDED - we're converting from industry to commodity form
    # The NAICS code represents the producing industry, which is no longer relevant for commodities
    agg_columns = [
        'USEEIO Sector Code',  # Now represents commodity, not industry
        'Activity Category',
        'IPCC/UNFCCC Category',
        'Activity Subcategory',
        'Activity Type',
        'Activity',  # Granular activity level - describes the emission source, not the industry
        'Fuel Consumed',
        'Gas Category',
        'Gas',
        'US GHGI Table ID',
        'US GHGI Chapter',
        'US GHGI Table Name',
        'Attribution Sources'
    ]
    
    # Filter to only columns that exist
    agg_columns = [col for col in agg_columns if col in commodity_df.columns]
    
    print(f"  Aggregating by: {', '.join(agg_columns)}")
    print(f"  Note: NAICS Sector Code excluded (rolling up from industry to commodity form)")
    
    # Group and aggregate
    # Emission intensity is already transformed by V_n, so just sum it
    emissions_intensity_col = get_emissions_intensity_col()
    agg_dict = {
        'Emissions (kg)': 'sum',
        emissions_intensity_col: 'sum',  # Already transformed by V_n matrix
        'AR5-100 GWP': 'first',  # GWP is same for same gas
    }
    
    commodity_agg = commodity_df.groupby(agg_columns, dropna=False).agg(agg_dict).reset_index()
    
    # Set NAICS Sector Code to None for commodity form (no longer meaningful)
    commodity_agg['NAICS Sector Code'] = None
    
    print(f"✓ Aggregated to {len(commodity_agg):,} commodity records (NAICS codes removed)")
    
    # Recalculate kgCO2e and MTCO2e using GWP
    commodity_agg['Emissions (kgCO2e)'] = commodity_agg['Emissions (kg)'] * commodity_agg['AR5-100 GWP']
    commodity_agg['Emissions (MTCO2e)'] = commodity_agg['Emissions (kgCO2e)'] / 1_000_000
    
    # Enrich with USEEIO Sector Names for commodity codes
    commodity_agg['USEEIO Sector Name'] = commodity_agg['USEEIO Sector Code'].map(sector_code_to_name)
    
    # Calculate contribution percentages by commodity USEEIO sector
    print("  Calculating contribution percentages for commodity form...")
    commodity_agg = calculate_contribution_by_sector(commodity_agg)
    
    # Reorder columns to match the expected output structure
    # Using the same order as KEEP_COLUMNS in config.py
    column_order = [
        'USEEIO Sector Name',
        'USEEIO Sector Code',
        'NAICS Sector Code',  # Will be None for commodity form
        'Activity Category',
        'IPCC/UNFCCC Category',
        'Activity Subcategory',
        'Activity Type',
        'Activity',
        'Fuel Consumed',
        'Gas Category',
        'Gas',
        'Emissions (kg)',
        get_emissions_intensity_col(),
        'AR5-100 GWP',
        'Emissions (kgCO2e)',
        'Emissions (MTCO2e)',
        "Contribution to USEEIO Sector's Scope 1 (%)",
        'US GHGI Chapter',
        'US GHGI Table ID',
        'US GHGI Table Name',
        'Attribution Sources',
    ]
    
    # Only include columns that exist
    final_columns = [col for col in column_order if col in commodity_agg.columns]
    commodity_agg = commodity_agg[final_columns]
    
    # Verify total emissions preserved
    original_total_kg = df_to_transform['Emissions (kg)'].sum()
    commodity_total_kg = commodity_agg['Emissions (kg)'].sum()
    difference_pct = abs(commodity_total_kg - original_total_kg) / original_total_kg * 100
    
    print(f"✓ Emission totals:")
    print(f"  Industry form: {original_total_kg:,.0f} kg")
    print(f"  Commodity form: {commodity_total_kg:,.0f} kg")
    print(f"  Difference: {difference_pct:.2f}%")
    
    if difference_pct > 1.0:
        print(f"  ⚠ Warning: Emissions difference exceeds 1% ({difference_pct:.2f}%)")
    
    return commodity_agg


def build_hierarchical_jsonld(df, include_all_fields=True):
    """
    Build hierarchical JSON-LD structure from flat DataFrame.
    
    Note: Row ID is excluded from JSON-LD exports (only for tabular formats).
    
    Full Hierarchy:
    - USEEIO Sector Code (top level)
      - USEEIO Sector Name (attribute)
      - NAICS Sector Code (child)
        - Activity Category (child)
          - IPCC/UNFCCC Category (child)
            - Activity Subcategory (child)
              - Activity Type (child)
                - GHG Source (child)
                  - Fuel Consumed (child)
                    - Gas Category (child)
                      - Gas (leaf with emission values)
    
    Light/Sunburst Hierarchy (aggregated):
    - USEEIO Sector Code (top level)
      - Activity Category (child)
        - Activity Type (child)
          - Gas category (child with summed contributions)
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with all columns
    include_all_fields : bool
        If True, include all fields (full version with complete hierarchy)
        If False, simplified hierarchy for visualization with aggregated contributions
        
    Returns:
    --------
    dict
        JSON-LD structure with @context and @graph
    """
    import json
    from collections import defaultdict
    
    print(f"Building {'full' if include_all_fields else 'light'} hierarchical JSON-LD...")
    
    if include_all_fields:
        # Full hierarchy structure
        hierarchy = defaultdict(lambda: {
            'naics_sectors': defaultdict(lambda: {
                'ghg_categories': defaultdict(lambda: {
                    'ipcc_categories': defaultdict(lambda: {
                        'ghg_subcategories': defaultdict(lambda: {
                            'activity_sets': defaultdict(lambda: {
                                'activities': defaultdict(lambda: {
                                    'fuels': defaultdict(lambda: {
                                        'gas_categories': defaultdict(lambda: {
                                            'gases': defaultdict(lambda: {
                                                'ghgi_tables': defaultdict(lambda: {
                                                    'emissions': []
                                                })
                                            })
                                        })
                                    })
                                })
                            })
                        })
                    })
                })
            })
        })
        
        # Fields that are part of the hierarchy structure (don't duplicate in emissions)
        hierarchy_fields = {
            'Row ID',  # Exclude Row ID from hierarchy (only for tabular exports)
            'USEEIO Sector Name', 'USEEIO Sector Code', 'NAICS Sector Code',
            'Activity Category', 'IPCC/UNFCCC Category', 'Activity Subcategory',
            'Activity Type', 'GHG Source', 'Fuel Consumed', 'Gas Category', 'Gas',
            'US GHGI Chapter', 'US GHGI Table ID', 'US GHGI Table Name', 'Attribution Sources'
        }
        
        # Build full hierarchy
        for _, row in df.iterrows():
            useeio_code = row.get('USEEIO Sector Code')
            if pd.isna(useeio_code):
                continue
                
            useeio_name = row.get('USEEIO Sector Name')
            naics_code = row.get('NAICS Sector Code')
            ghg_category = row.get('Activity Category')
            ipcc_category = row.get('IPCC/UNFCCC Category')
            ghg_subcategory = row.get('Activity Subcategory')
            ghg_sub_subcategory = row.get('Activity Type')
            ghg_source = row.get('GHG Source')
            fuel = row.get('Fuel Consumed')
            gas_category = row.get('Gas Category')
            gas = row.get('Gas')
            ghgi_table_id = row.get('US GHGI Table ID')
            ghgi_chapter = row.get('US GHGI Chapter')
            ghgi_table_name = row.get('US GHGI Table Name')
            attribution_sources = row.get('Attribution Sources')
            
            # Convert NaN to None for JSON compatibility
            if pd.isna(useeio_name):
                useeio_name = None
            if pd.isna(ghg_subcategory):
                ghg_subcategory = None
            if pd.isna(ghg_sub_subcategory):
                ghg_sub_subcategory = None
            if pd.isna(fuel):
                fuel = None
            if pd.isna(attribution_sources):
                attribution_sources = None
            
            # Store USEEIO sector info
            if 'useeio_sector_name' not in hierarchy[useeio_code]:
                hierarchy[useeio_code]['useeio_sector_name'] = useeio_name
            
            # Navigate full hierarchy
            naics_dict = hierarchy[useeio_code]['naics_sectors'][naics_code]
            ghg_dict = naics_dict['ghg_categories'][ghg_category]
            ipcc_dict = ghg_dict['ipcc_categories'][ipcc_category]
            subcategory_dict = ipcc_dict['ghg_subcategories'][ghg_subcategory]
            sub_subcategory_dict = subcategory_dict['activity_sets'][ghg_sub_subcategory]
            source_dict = sub_subcategory_dict['activities'][ghg_source]
            fuel_dict = source_dict['fuels'][fuel]
            gas_cat_dict = fuel_dict['gas_categories'][gas_category]
            gas_dict = gas_cat_dict['gases'][gas]
            
            # Store gas-level attributes (only once)
            if 'attribution_sources' not in gas_dict:
                gas_dict['attribution_sources'] = attribution_sources
            
            # Navigate to GHGI table level
            ghgi_table_dict = gas_dict['ghgi_tables'][ghgi_table_id]
            
            # Store GHGI table metadata (only once)
            if 'ghgi_chapter' not in ghgi_table_dict:
                ghgi_table_dict['ghgi_chapter'] = ghgi_chapter
            if 'ghgi_table_name' not in ghgi_table_dict:
                ghgi_table_dict['ghgi_table_name'] = ghgi_table_name
            
            # Store emission data (only non-hierarchy fields)
            emission_record = {}
            for col, val in row.items():
                if col not in hierarchy_fields and not pd.isna(val):
                    emission_record[col] = val
            
            if emission_record:
                ghgi_table_dict['emissions'].append(emission_record)
    
    else:
        # Light hierarchy: USEEIO → Activity Category → Activity Set → Gas Category
        # Aggregate by summing contributions
        aggregation = defaultdict(lambda: {
            'ghg_categories': defaultdict(lambda: {
                'activity_sets': defaultdict(lambda: {
                    'gas_categories': defaultdict(float)
                })
            })
        })
        
        # Aggregate contributions
        for _, row in df.iterrows():
            useeio_code = row.get('USEEIO Sector Code')
            if pd.isna(useeio_code):
                continue
                
            ghg_category = row.get('Activity Category')
            ghg_sub_subcategory = row.get('Activity Type')
            gas_category = row.get('Gas Category')
            contribution = row.get("Contribution to USEEIO Sector's Scope 1 (%)", 0)
            
            if pd.isna(contribution):
                contribution = 0
            
            # Sum contributions for this combination
            aggregation[useeio_code]['ghg_categories'][ghg_category]['activity_sets'][ghg_sub_subcategory]['gas_categories'][gas_category] += contribution
        
        hierarchy = aggregation
    
    # Convert nested defaultdicts to regular dicts for JSON serialization
    def convert_to_dict(obj):
        if isinstance(obj, defaultdict):
            obj = {k: convert_to_dict(v) for k, v in obj.items()}
        return obj
    
    hierarchy = convert_to_dict(hierarchy)
    
    # Build final JSON-LD structure
    graph = []
    
    if include_all_fields:
        # Full hierarchy structure
        for useeio_code, useeio_data in hierarchy.items():
            useeio_obj = {
                'useeio_sector_code': useeio_code,
                'useeio_sector_name': useeio_data.get('useeio_sector_name'),
                'naics_sectors': []
            }
            
            for naics_code, naics_data in useeio_data['naics_sectors'].items():
                naics_obj = {
                    'naics_sector_code': naics_code,
                    'ghg_categories': []
                }
                
                for ghg_cat, ghg_data in naics_data['ghg_categories'].items():
                    ghg_obj = {
                        'ghg_source_category': ghg_cat,
                        'ipcc_categories': []
                    }
                    
                    for ipcc_cat, ipcc_data in ghg_data['ipcc_categories'].items():
                        ipcc_obj = {
                            'ipcc_unfccc_category': ipcc_cat,
                            'ghg_subcategories': []
                        }
                        
                        for subcategory, subcategory_data in ipcc_data['ghg_subcategories'].items():
                            subcategory_obj = {
                                'ghg_source_subcategory': subcategory,
                                'activity_sets': []
                            }
                            
                            for activity_set, activity_set_data in subcategory_data['activity_sets'].items():
                                activity_set_obj = {
                                    'ghg_source_sub_subcategory': activity_set,
                                    'activities': []
                                }
                                
                                for activity, activity_data in activity_set_data['activities'].items():
                                    activity_obj = {
                                        'ghg_source': activity,
                                        'fuels': []
                                    }
                                    
                                    for fuel, fuel_data in activity_data['fuels'].items():
                                        fuel_obj = {
                                            'fuel': fuel,
                                            'gas_categories': []
                                        }
                                        
                                        for gas_cat, gas_cat_data in fuel_data['gas_categories'].items():
                                            gas_cat_obj = {
                                                'gas_category': gas_cat,
                                                'gases': []
                                            }
                                            
                                            for gas, gas_data in gas_cat_data['gases'].items():
                                                gas_obj = {
                                                    'gas': gas,
                                                    'attribution_sources': gas_data.get('attribution_sources'),
                                                    'ghgi_tables': []
                                                }
                                                
                                                # Add GHGI table hierarchy
                                                for ghgi_table_id, ghgi_table_data in gas_data['ghgi_tables'].items():
                                                    ghgi_table_obj = {
                                                        'ghgi_table_id': ghgi_table_id,
                                                        'ghgi_chapter': ghgi_table_data.get('ghgi_chapter'),
                                                        'ghgi_table_name': ghgi_table_data.get('ghgi_table_name'),
                                                        'emissions': ghgi_table_data['emissions']
                                                    }
                                                    gas_obj['ghgi_tables'].append(ghgi_table_obj)
                                                
                                                gas_cat_obj['gases'].append(gas_obj)
                                            
                                            fuel_obj['gas_categories'].append(gas_cat_obj)
                                        
                                        activity_obj['fuels'].append(fuel_obj)
                                    
                                    activity_set_obj['activities'].append(activity_obj)
                                
                                subcategory_obj['activity_sets'].append(activity_set_obj)
                            
                            ipcc_obj['ghg_subcategories'].append(subcategory_obj)
                        
                        ghg_obj['ipcc_categories'].append(ipcc_obj)
                    
                    naics_obj['ghg_categories'].append(ghg_obj)
                
                useeio_obj['naics_sectors'].append(naics_obj)
            
            graph.append(useeio_obj)
        
        # Count nodes at each level for full hierarchy
        total_useeio = len(graph)
        total_naics = sum(len(u['naics_sectors']) for u in graph)
        total_ghg = sum(len(n['ghg_categories']) for u in graph for n in u['naics_sectors'])
        total_ipcc = sum(len(g['ipcc_categories']) for u in graph for n in u['naics_sectors'] 
                        for g in n['ghg_categories'])
        
        print(f"✓ Built full hierarchy: {total_useeio} USEEIO sectors → {total_naics} NAICS → {total_ghg} GHG categories → {total_ipcc} IPCC categories")
    
    else:
        # Light hierarchy structure (aggregated)
        for useeio_code, useeio_data in hierarchy.items():
            useeio_obj = {
                'useeio_sector_code': useeio_code,
                'ghg_categories': []
            }
            
            for ghg_cat, ghg_data in useeio_data['ghg_categories'].items():
                ghg_obj = {
                    'ghg_source_category': ghg_cat,
                    'activity_sets': []
                }
                
                for activity_set, activity_set_data in ghg_data['activity_sets'].items():
                    activity_set_obj = {
                        'ghg_source_sub_subcategory': activity_set,
                        'gas_categories': []
                    }
                    
                    for gas_cat, contribution in activity_set_data['gas_categories'].items():
                        gas_cat_obj = {
                            'gas_category': gas_cat,
                            'contribution_pct': contribution
                        }
                        activity_set_obj['gas_categories'].append(gas_cat_obj)
                    
                    ghg_obj['activity_sets'].append(activity_set_obj)
                
                useeio_obj['ghg_categories'].append(ghg_obj)
            
            graph.append(useeio_obj)
        
        # Count nodes at each level for light hierarchy
        total_useeio = len(graph)
        total_ghg = sum(len(u['ghg_categories']) for u in graph)
        total_activity_sets = sum(len(g['activity_sets']) for u in graph for g in u['ghg_categories'])
        total_gas_cats = sum(len(a['gas_categories']) for u in graph for g in u['ghg_categories'] 
                            for a in g['activity_sets'])
        
        print(f"✓ Built light hierarchy: {total_useeio} USEEIO sectors → {total_ghg} GHG categories → {total_activity_sets} activity sets → {total_gas_cats} gas categories")
    
    # Create JSON-LD with context
    jsonld = {
        "@context": {
            "@vocab": "http://example.org/ghg#",
            "useeio": "http://useeio.org/sectors/",
            "naics": "http://naics.org/sectors/",
            "ipcc": "http://ipcc.org/categories/",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "@graph": graph
    }
    
    return jsonld


def build_ghg_source_classification_jsonld(df):
    """
    Build GHG source classification in multidimensional JSON-LD format.
    
    Creates separate hierarchies for different dimensions:
    1. GHG Source Hierarchy: Category → Subcategory → SubSubcategory → Activity
    2. Fuel Dimension: Independent list of fuels
    3. Gas Hierarchy: Gas Category → Gas
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with GHG classification columns
        
    Returns:
    --------
    dict
        JSON-LD structure with @context and @graph containing multidimensional GHG classifications
    """
    from collections import defaultdict
    import json
    
    print("Building GHG source classification JSON-LD...")
    
    # Build GHG Source Hierarchy: Category → Subcategory → SubSubcategory → Activity
    ghg_hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    
    # Build Fuel list (independent dimension)
    fuels = set()
    
    # Build Gas Hierarchy: Gas Category → Gas
    gas_hierarchy = defaultdict(set)
    
    for _, row in df.iterrows():
        ghg_cat = row.get('Activity Category', 'Unknown')
        ghg_subcat = row.get('Activity Subcategory', 'Unknown')
        ghg_subsubcat = row.get('Activity Type', 'Unknown')
        activity = row.get('Activity', 'Unknown')
        fuel = row.get('Fuel Consumed')
        gas_cat = row.get('Gas Category', 'Unknown')
        gas = row.get('Gas', 'Unknown')
        
        # Handle None values
        if pd.isna(ghg_cat) or ghg_cat is None:
            ghg_cat = 'Unknown'
        if pd.isna(ghg_subcat) or ghg_subcat is None:
            ghg_subcat = 'Unknown'
        if pd.isna(ghg_subsubcat) or ghg_subsubcat is None:
            ghg_subsubcat = 'Unknown'
        if pd.isna(activity) or activity is None:
            activity = 'Unknown'
        if pd.isna(gas_cat) or gas_cat is None:
            gas_cat = 'Unknown'
        if pd.isna(gas) or gas is None:
            gas = 'Unknown'
        
        # Store in GHG source hierarchy
        ghg_hierarchy[ghg_cat][ghg_subcat][ghg_subsubcat].add(activity)
        
        # Store fuel (independent)
        if pd.notna(fuel) and fuel is not None and fuel != 'None' and fuel != '':
            fuels.add(fuel)
        
        # Store in gas hierarchy
        gas_hierarchy[gas_cat].add(gas)
    
    # Convert to JSON-LD graph structure
    graph = []
    
    # 1. GHG Source Hierarchy
    ghg_source_categories = []
    for ghg_cat in sorted(ghg_hierarchy.keys()):
        category_obj = {
            get_jsonld_property('activity_level_1'): ghg_cat,
            "subcategories": []
        }
        
        for ghg_subcat in sorted(ghg_hierarchy[ghg_cat].keys()):
            subcat_obj = {
                get_jsonld_property('activity_level_2'): ghg_subcat,
                "activity_types": []
            }
            
            for ghg_subsubcat in sorted(ghg_hierarchy[ghg_cat][ghg_subcat].keys()):
                subsubcat_obj = {
                    get_jsonld_property('activity_level_3'): ghg_subsubcat,
                    "activities": sorted(list(ghg_hierarchy[ghg_cat][ghg_subcat][ghg_subsubcat]))
                }
                subcat_obj["activity_types"].append(subsubcat_obj)
            
            category_obj["subcategories"].append(subcat_obj)
        
        ghg_source_categories.append(category_obj)
    
    # 2. Fuel Dimension (independent list)
    fuel_list = sorted(list(fuels))
    
    # 3. Gas Hierarchy
    gas_categories = []
    for gas_cat in sorted(gas_hierarchy.keys()):
        gas_cat_obj = {
            get_jsonld_property('gas_level_1'): gas_cat,
            "gases": sorted(list(gas_hierarchy[gas_cat]))
        }
        gas_categories.append(gas_cat_obj)
    
    # Build graph with all three dimensions
    graph.append({
        "classification_type": "activity_hierarchy",
        "categories": ghg_source_categories
    })
    
    graph.append({
        "classification_type": "fuel_dimension",
        "fuels": fuel_list
    })
    
    graph.append({
        "classification_type": "gas_hierarchy",
        "gas_categories": gas_categories
    })
    
    # Count unique elements
    total_ghg_categories = len(ghg_hierarchy)
    total_fuels = len(fuels)
    total_gas_categories = len(gas_hierarchy)
    
    print(f"✓ Built GHG source classification:")
    print(f"  - {total_ghg_categories} activity categories")
    print(f"  - {total_fuels} unique fuels")
    print(f"  - {total_gas_categories} gas categories")
    
    # Create JSON-LD with context
    jsonld = {
        "@context": {
            "@vocab": "http://example.org/ghg#",
            "ipcc": "http://ipcc.org/categories/",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "@graph": graph
    }
    
    return jsonld


def build_ghg_source_classification_csv(df):
    """
    Build GHG source classification as CSV with unique combinations.
    
    Extracts unique combinations of classification columns from enriched data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with GHG classification columns
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame with unique classification combinations
    """
    print("Building GHG source classification CSV...")
    
    # Define classification columns
    classification_columns = [
        'Activity Category',
        'IPCC/UNFCCC Category',
        'Activity Subcategory',
        'Activity Type',
        'Activity',
        'Fuel Consumed',
        'Gas Category',
        'Gas'
    ]
    
    # Get unique combinations (drop duplicates)
    classification_df = df[classification_columns].drop_duplicates().sort_values(by=classification_columns)
    
    # Reset index to get clean row numbers
    classification_df = classification_df.reset_index(drop=True)
    
    print(f"✓ Built GHG source classification CSV with {len(classification_df)} unique combinations")
    
    return classification_df


def generate_event_id(row):
    """
    Generate composite event ID: useeio_activity_gas_fuel
    
    Handles null/missing values gracefully by using 'none' placeholder.
    Creates human-readable IDs that are unique per emission event.
    
    Parameters:
    -----------
    row : pandas.Series
        DataFrame row with emission data
        
    Returns:
    --------
    str
        Composite event ID (e.g., "331313_aluminum_production_hexafluoroethane_none")
    """
    def sanitize(val):
        """Convert value to safe ID component."""
        if pd.isna(val) or val == '' or val is None:
            return 'none'
        # Convert to lowercase, replace spaces and hyphens with underscores
        return str(val).lower().replace(' ', '_').replace('-', '_').replace('/', '_')
    
    parts = [
        sanitize(row.get('USEEIO Sector Code')),
        sanitize(row.get('Activity')),  # This is ActivityProducedBy after renaming
        sanitize(row.get('Gas')),  # This is Flowable after renaming
        sanitize(row.get('Fuel Consumed'))
    ]
    
    return '_'.join(parts)


def build_emission_event_full(row):
    """
    Build complete emission event structure for RDF/knowledge graph.
    
    Creates a fully structured event with all metadata following the
    event-based ontology for semantic querying and linked data.
    
    Parameters:
    -----------
    row : pandas.Series
        DataFrame row with enriched emission data
        
    Returns:
    --------
    dict
        Complete emission event structure
    """
    event_id = generate_event_id(row)
    
    # Helper to handle NaN values
    def get_value(key, default=None):
        val = row.get(key, default)
        return None if pd.isna(val) else val
    
    event = {
        "@id": f"emission_event:{event_id}",
        "@type": "EmissionEvent",
        "eventId": event_id,
        
        "hasCategory": {
            "@type": "ActivityCategory",
            "name": get_value('Activity Category'),
            "subcategory": get_value('Activity Subcategory'),
            "subSubcategory": get_value('Activity Type')
        },
        
        "fromActivity": {
            "@type": "ActivityContext",
            "activitySet": get_value('Activity Set'),
            "activity": get_value('Activity')
        },
        
        "fromProcess": get_value('Process'),
        
        "consumesFuel": {
            "@type": "Fuel",
            "name": get_value('Fuel Consumed'),
            "category": get_value('Fuel Category')
        },
        
        "emitsGas": {
            "@type": "GreenhouseGas",
            "gasCategory": get_value('Gas Category'),
            "gas": get_value('Gas'),
            "chemicalFormula": get_value('Chemical Formula'),
            "co2eGWP": "AR5-100yr",
            "gwpAR5_100": get_value('AR5-100 GWP')
        },
        
        "mapsToIPCC": {
            "@type": "IPCCCategory",
            "category": get_value('IPCC/UNFCCC Category')
        },
        
        "inSector": {
            "@type": "EconomicSector",
            "useeioCode": get_value('USEEIO Sector Code'),
            "naicsCodes": [get_value('NAICS Sector Code')] if get_value('NAICS Sector Code') else []
        },
        
        "hasEmission": {
            "@type": "EmissionQuantity",
            "contributionToSectorScope1Percent": get_value("Contribution to USEEIO Sector's Scope 1 (%)")
        },
        
        "derivedFrom": {
            "@type": "DataProvenance",
            "publication": "Inventory of U.S. Greenhouse Gas Emissions and Sinks: 1990-2022",
            "chapter": get_value('US GHGI Chapter'),
            "tableId": get_value('US GHGI Table ID'),
            "tableName": get_value('US GHGI Table Name'),
            "year": config.MODEL_YEAR,
            "location": "US"
        },
        
        "attributedBy": {
            "@type": "AttributionMethod",
            "source": "flowsa",
            "method": get_value('Attribution Method', 'Direct'),
            "metaSources": get_value('MetaSources')
        },
        
        "metadata": {
            "modelVersion": config.MODELNAME,
            "modelName": "FlowSA with DecarbNexus Custom Outputs"
        }
    }
    
    return event


def build_emission_events_jsonld(df):
    """
    Build event-based JSON-LD for RDF/knowledge graph.
    
    Converts flat DataFrame to semantic event structure suitable for
    SPARQL queries, knowledge graphs, and linked data applications.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched emissions data
        
    Returns:
    --------
    dict
        JSON-LD structure with @context and @graph
    """
    print("Building event-based JSON-LD for RDF/knowledge graph...")
    
    context = {
        "@vocab": "http://decarbonexus.org/ghg#",
        "ipcc": "http://ipcc.org/categories/",
        "naics": "http://naics.com/",
        "useeio": "http://useeio.org/sectors/",
        "xsd": "http://www.w3.org/2001/XMLSchema#"
    }
    
    events = []
    for idx, row in df.iterrows():
        event = build_emission_event_full(row)
        events.append(event)
        
        # Progress indicator for large datasets
        if (idx + 1) % 5000 == 0:
            print(f"  Processed {idx + 1:,} emission events...")
    
    jsonld_data = {
        "@context": context,
        "@graph": events
    }
    
    print(f"✓ Built {len(events):,} emission events")
    
    return jsonld_data


def build_d3_sunburst_hierarchy(df):
    """
    Build simplified 3-level D3.js sunburst hierarchy.
    
    Creates a clean 3-ring structure:
    - USEEIO Sector (root level)
      → Activity Category (ring 1)
        → Activity Type (ring 2)
          → Gas Category (ring 3, with contribution values)
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched emissions data
        
    Returns:
    --------
    dict
        D3.js-optimized hierarchical structure with 3 levels
    """
    from collections import defaultdict
    
    print("Building D3.js sunburst hierarchy...")
    
    # Filter out F01000 sector (used goods, non-emission producing)
    df = df[df['USEEIO Sector Code'] != 'F01000'].copy()
    
    # Build 3-level nested hierarchy: USEEIO → GHG Category → SubSubcategory → Gas Category
    hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(float))))
    
    for _, row in df.iterrows():
        useeio = row.get('USEEIO Sector Code')
        if pd.isna(useeio):
            continue
            
        ghg_cat = row.get('Activity Category', 'Unknown')
        subsubcat = row.get('Activity Type', 'Unknown')
        gas_cat = row.get('Gas Category', 'Unknown')
        contribution = row.get("Contribution to USEEIO Sector's Scope 1 (%)", 0)
        
        if pd.isna(contribution):
            contribution = 0
        
        # Aggregate contributions at this level
        hierarchy[useeio][ghg_cat][subsubcat][gas_cat] += contribution
    
    # Convert to D3.js format
    root_children = []
    
    for useeio, ghg_cats in hierarchy.items():
        ghg_cat_children = []
        
        for ghg_cat, subsubcats in ghg_cats.items():
            subsubcat_children = []
            
            for subsubcat, gas_cats in subsubcats.items():
                gas_cat_children = []
                
                for gas_cat, contrib in gas_cats.items():
                    gas_cat_children.append({
                        "name": gas_cat,
                        get_jsonld_property('contribution'): contrib,
                        "category": get_jsonld_property('gas_level_1')
                    })
                
                subsubcat_children.append({
                    "name": subsubcat,
                    "children": gas_cat_children,
                    "category": get_jsonld_property('activity_level_3')
                })
            
            ghg_cat_children.append({
                "name": ghg_cat,
                "children": subsubcat_children,
                "category": get_jsonld_property('activity_level_1')
            })
        
        root_children.append({
            "name": useeio,
            "children": ghg_cat_children,
            "category": "useeio_sector",
            "useeio_code": useeio
        })
    
    root = {
        "name": "GHG Emissions",
        "children": root_children
    }
    
    # Count nodes
    total_useeio = len(root_children)
    total_ghg_cats = sum(len(u['children']) for u in root_children)
    total_nodes = 1  # root
    for sector in root_children:
        total_nodes += 1  # sector
        for ghg in sector['children']:
            total_nodes += 1  # ghg category
            for subsubcat in ghg['children']:
                total_nodes += 1  # subsubcategory
                total_nodes += len(subsubcat['children'])  # gas categories
    
    print(f"✓ Built D3.js sunburst: {total_useeio} USEEIO sectors → {total_ghg_cats} GHG categories")
    
    return root


def export_event_based_outputs(enriched_data, output_dir, model_name):
    """
    Export event-based JSON-LD files.
    
    Exports:
    --------
    1. {model}_emission_events.jsonld - Full RDF structure for knowledge graphs
    2. {model}_emission_events_sunburst.json - Optimized for D3.js visualization
    
    Parameters:
    -----------
    enriched_data : pandas.DataFrame
        Enriched emissions data
    output_dir : str
        Output directory path
    model_name : str
        Model name for file naming
        
    Returns:
    --------
    dict
        Paths to exported files
    """
    print("\n" + "="*80)
    print("EXPORTING EVENT-BASED OUTPUTS")
    print("="*80)
    
    # Filter out F01000 sector (used goods, non-emission producing)
    enriched_data = enriched_data[enriched_data['USEEIO Sector Code'] != 'F01000'].copy()
    
    # Full RDF format
    print("\n1. Full Emission Events (RDF/Knowledge Graph)")
    print("-" * 40)
    full_jsonld = build_emission_events_jsonld(enriched_data)
    full_path = os.path.join(output_dir, f"{model_name}_emission_events.jsonld")
    
    try:
        with open(full_path, 'w') as f:
            import json
            json.dump(full_jsonld, f, indent=2)
        print(f"✓ Saved: {os.path.basename(full_path)}")
        print(f"  Events: {len(full_jsonld['@graph']):,}")
    except Exception as e:
        print(f"⚠ Error saving full events: {e}")
        full_path = None
    
    # D3.js Sunburst format
    print("\n2. D3.js Sunburst Visualization")
    print("-" * 40)
    sunburst_data = build_d3_sunburst_hierarchy(enriched_data)
    sunburst_path = os.path.join(output_dir, f"{model_name}_emission_events_sunburst.json")
    
    try:
        with open(sunburst_path, 'w') as f:
            import json
            json.dump(sunburst_data, f, indent=2)
        print(f"✓ Saved: {os.path.basename(sunburst_path)}")
        
        # Count total nodes for info
        def count_nodes(node):
            count = 1
            if 'children' in node:
                for child in node['children']:
                    count += count_nodes(child)
            return count
        
        total_nodes = count_nodes(sunburst_data)
        print(f"  Total nodes: {total_nodes:,}")
    except Exception as e:
        print(f"⚠ Error saving sunburst: {e}")
        sunburst_path = None
    
    print("\n" + "="*80)
    
    return {
        'full_events': full_path,
        'sunburst': sunburst_path
    }


def save_outputs(fbs_parquet, fbs_calculated, enriched_data, config_dict, commodity_data=None):
    """
    Save all outputs in multiple formats for different use cases.
    
    Exports both industry form and commodity form (if provided):
    - Excel (.xlsx) - For manual analysis
    - CSV (.csv) - For general data interchange
    - Parquet (.parquet) - For efficient data science workflows (columnar format)
    - JSON-LD (.jsonld) - Event-based emission events for RDF/knowledge graphs
    - JSON (_sunburst.json) - D3.js-optimized hierarchy for visualization
    
    Parameters:
    -----------
    fbs_parquet : pandas.DataFrame
        Raw parquet data (optional, can be None)
    fbs_calculated : pandas.DataFrame  
        Generated FlowBySector data (not exported anymore)
    enriched_data : pandas.DataFrame
        Final enriched data with metadata (industry form)
    config_dict : dict
        Configuration parameters for file naming
    commodity_data : pandas.DataFrame, optional
        Commodity-form data (if None, only industry form is exported)
    """
    # Ensure output directory exists
    os.makedirs(config_dict["output_dir"], exist_ok=True)
    
    # Create subdirectories for industry and commodity forms
    industry_dir = os.path.join(config_dict["output_dir"], "industry")
    commodity_dir = os.path.join(config_dict["output_dir"], "commodity")
    os.makedirs(industry_dir, exist_ok=True)
    os.makedirs(commodity_dir, exist_ok=True)
    
    print("="*80)
    print("SAVING OUTPUTS")
    print("="*80)
    
    # Prepare both forms for export
    forms_to_export = [
        {'data': enriched_data, 'suffix': '_industry', 'label': 'Industry form', 'subdir': industry_dir}
    ]
    
    if commodity_data is not None:
        forms_to_export.append({
            'data': commodity_data, 
            'suffix': '_commodity', 
            'label': 'Commodity form',
            'subdir': commodity_dir
        })
    
    # Export each form
    for form in forms_to_export:
        data = form['data']
        suffix = form['suffix']
        label = form['label']
        subdir = form['subdir']
        
        print(f"\n{label}:")
        print("-" * 40)
        
        # Filter out F01000 sector (used goods, non-emission producing)
        data = data[data['USEEIO Sector Code'] != 'F01000'].copy()
        
        # Remove QC columns if configured (for Excel, CSV, Parquet)
        export_data = data.copy()
        
        # For commodity form, remove NAICS Sector Code column
        if suffix == '_commodity' and 'NAICS Sector Code' in export_data.columns:
            export_data = export_data.drop(columns=['NAICS Sector Code'])
            print(f"  Excluded NAICS Sector Code (not applicable to commodity form)")
        
        if config.EXCLUDE_QC_COLUMNS:
            qc_cols_present = [col for col in config.QC_ONLY_COLUMNS if col in export_data.columns]
            if qc_cols_present:
                export_data = export_data.drop(columns=qc_cols_present)
                print(f"  Excluded {len(qc_cols_present)} QC columns from flat exports")
        
        # For JSON-LD exports, ALWAYS exclude QC columns (regardless of config flag)
        jsonld_data = data.copy()
        
        # For commodity form, remove NAICS Sector Code from JSON-LD too
        if suffix == '_commodity' and 'NAICS Sector Code' in jsonld_data.columns:
            jsonld_data = jsonld_data.drop(columns=['NAICS Sector Code'])
        
        qc_cols_in_jsonld = [col for col in config.QC_ONLY_COLUMNS if col in jsonld_data.columns]
        if qc_cols_in_jsonld:
            jsonld_data = jsonld_data.drop(columns=qc_cols_in_jsonld)
            if config.EXCLUDE_QC_COLUMNS:  # Only print if not already printed above
                pass
            else:
                print(f"  Excluded {len(qc_cols_in_jsonld)} QC columns from JSON-LD exports")
        
        # Base filename without extension
        base_filename = config.MODELNAME + suffix
        
        # -------------------------------------------------------------------------
        # 1. Excel format - for manual analysis and Excel users
        # -------------------------------------------------------------------------
        excel_path = os.path.join(subdir, f"{base_filename}.xlsx")
        try:
            # Create metadata sheets
            author_info = pd.DataFrame({
                'Field': [
                    'Author',
                    'Organization',
                    'Website',
                    'Contact',
                    'Open-source repository',
                    'Q&A + Discussion',
                    'Data License',
                    'License URL',
                    '',  # Blank row
                    'Required Attribution',
                    'Cite This Dataset',
                    'Cite EPA GHGI',
                    'Cite FlowSA',
                    'Cite USEEIOR',
                    '',  # Blank row
                    'License Compliance',
                    'Third-Party Licenses',
                    'Full Citation Info'
                ],
                'Value': [
                    'DecarbNexus',
                    'DecarbNexus LLC',
                    'decarbnexus.com',
                    'contact@decarbnexus.com',
                    'https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation',
                    'https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation/discussions',
                    'CC BY 4.0',
                    'https://creativecommons.org/licenses/by/4.0/',
                    '',  # Blank
                    'You must cite this dataset AND the original sources (EPA GHGI, FlowSA, USEEIOR)',
                    'DecarbNexus (2025). U.S. GHG Emissions by USEEIO Sector. DecarbNexus.',
                    'EPA (2024). Inventory of U.S. GHG Emissions and Sinks: 1990-2022. EPA 430-R-24-004',
                    'Birney et al. (2023). FlowSA v2.0.3. U.S. EPA. MIT License.',
                    'Li et al. (2022). useeior. Applied Sciences 12(9):4469. MIT License.',
                    '',  # Blank
                    'FlowSA and USEEIOR are MIT licensed. Full license texts in outputs/THIRD_PARTY_LICENSES.txt',
                    'See outputs/THIRD_PARTY_LICENSES.txt for MIT license text (FlowSA, USEEIOR)',
                    'See outputs/CITATION.md for complete BibTeX citations and attribution guide'
                ]
            })
            
            # Determine perspective type
            perspective = 'Industry' if suffix == '' else 'Commodity'
            
            model_specs = pd.DataFrame({
                'Field': [
                    'Dataset Version',
                    'Release Year',
                    '',  # Blank row
                    'Model Name',
                    'Model Description',
                    'Model Year',
                    'FlowSA Version',
                    'Reference File',
                    'IPCC Indicator',
                    'IPCC GWP Data File',
                    'Input-Output Perspective',
                    '',  # Blank row
                    'EPA GHGI Report (2022)',
                    'Main Text Tables (zip)',
                    'All Annexes (pdf)',
                    'Annex Tables (zip)',
                    'GHG Inventory Data Explorer'
                ],
                'Value': [
                    '1.0',
                    '2025',
                    '',  # Blank
                    config.MODELNAME,
                    config.MODEL_DESCRIPTION,
                    str(config.MODEL_YEAR),
                    config.REQUIRED_FLOWSA_VERSION,
                    config.FILE_NAME_PARQUET,
                    config.IPCC_INDICATOR,
                    config.IPCC_AR5_100_PARQUET,
                    perspective,
                    '',  # Blank
                    'https://www.epa.gov/ghgemissions/inventory-us-greenhouse-gas-emissions-and-sinks-1990-2022',
                    'https://www.epa.gov/system/files/other-files/2024-06/2024-main-text-tables.zip',
                    'https://www.epa.gov/system/files/documents/2024-04/us-ghg-inventory-2024-annexes.pdf',
                    'https://www.epa.gov/system/files/other-files/2024-06/2024-annex-tables.zip',
                    'https://cfpub.epa.gov/ghgdata/inventoryexplorer/chartindex.html'
                ]
            })
            
            # Load reference data for additional tabs
            # GHG source classification - use the final classification we just built
            ghg_classification_df = build_ghg_source_classification_csv(export_data)
            
            try:
                # Sector classification
                sector_classification_df = pd.read_csv(config.SECTOR_CLASSIFICATION_CSV)
            except:
                sector_classification_df = None
            
            try:
                # NAICS to USEEIO crosswalk
                naics_useeio_df = pd.read_csv(config.NAICS_TO_USEEIO_CSV)
            except:
                naics_useeio_df = None
            
            try:
                # V_n matrix (market share)
                v_n_df = pd.read_csv('data/V_n.csv', index_col=0)
            except:
                v_n_df = None
            
            try:
                # x vector (industry output)
                x_df = pd.read_csv('data/x.csv')
            except:
                x_df = None
            
            # Check if baseline tab should be included
            if config.INCLUDE_BASELINE_TAB and fbs_parquet is not None:
                # Export with multiple sheets
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Front matter
                    author_info.to_excel(writer, sheet_name='Author_Info', index=False)
                    model_specs.to_excel(writer, sheet_name='Model_Specs', index=False)
                    # Main data
                    export_data.to_excel(writer, sheet_name='Enriched', index=False)
                    fbs_parquet.to_excel(writer, sheet_name='Baseline', index=False)
                    # Reference data
                    if ghg_classification_df is not None:
                        ghg_classification_df.to_excel(writer, sheet_name='GHG_Classification', index=False)
                    if sector_classification_df is not None:
                        sector_classification_df.to_excel(writer, sheet_name='Sector_Classification', index=False)
                    if naics_useeio_df is not None:
                        naics_useeio_df.to_excel(writer, sheet_name='NAICS_to_USEEIO', index=False)
                    if v_n_df is not None:
                        v_n_df.to_excel(writer, sheet_name='V_n_Matrix', index=True)
                    if x_df is not None:
                        x_df.to_excel(writer, sheet_name='x_Vector', index=False)
                print(f"  ✓ Excel: {base_filename}.xlsx (with Author_Info, Model_Specs, Baseline, and reference data tabs)")
            else:
                # Export single sheet
                with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                    # Front matter
                    author_info.to_excel(writer, sheet_name='Author_Info', index=False)
                    model_specs.to_excel(writer, sheet_name='Model_Specs', index=False)
                    # Main data
                    export_data.to_excel(writer, sheet_name='Enriched', index=False)
                    # Reference data
                    if ghg_classification_df is not None:
                        ghg_classification_df.to_excel(writer, sheet_name='GHG_Classification', index=False)
                    if sector_classification_df is not None:
                        sector_classification_df.to_excel(writer, sheet_name='Sector_Classification', index=False)
                    if naics_useeio_df is not None:
                        naics_useeio_df.to_excel(writer, sheet_name='NAICS_to_USEEIO', index=False)
                    if v_n_df is not None:
                        v_n_df.to_excel(writer, sheet_name='V_n_Matrix', index=True)
                    if x_df is not None:
                        x_df.to_excel(writer, sheet_name='x_Vector', index=False)
                print(f"  ✓ Excel: {base_filename}.xlsx (with Author_Info, Model_Specs, and reference data tabs)")
        except PermissionError:
            print(f"  ⚠ Excel export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ Excel export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 2. CSV format - for general data interchange
        # -------------------------------------------------------------------------
        csv_path = os.path.join(subdir, f"{base_filename}.csv")
        try:
            export_data.to_csv(csv_path, index=False)
            print(f"  ✓ CSV: {base_filename}.csv")
        except PermissionError:
            print(f"  ⚠ CSV export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ CSV export failed: {str(e)}")
        
        # Export baseline CSV if configured
        if config.EXPORT_BASELINE_CSV and config.INCLUDE_BASELINE_TAB and fbs_parquet is not None:
            baseline_csv_path = os.path.join(subdir, f"{config.MODELNAME}{suffix}_baseline.csv")
            try:
                fbs_parquet.to_csv(baseline_csv_path, index=False)
                print(f"  ✓ CSV (baseline): {config.MODELNAME}{suffix}_baseline.csv")
            except PermissionError:
                print(f"  ⚠ Baseline CSV export skipped - file is open")
            except Exception as e:
                print(f"  ⚠ Baseline CSV export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 3. Parquet format - for efficient data science workflows
        # -------------------------------------------------------------------------
        parquet_path = os.path.join(subdir, f"{base_filename}.parquet")
        try:
            export_data.to_parquet(parquet_path, index=False, engine='pyarrow', compression='snappy')
            print(f"  ✓ Parquet: {base_filename}.parquet")
        except PermissionError:
            print(f"  ⚠ Parquet export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ Parquet export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 4. JSON-LD format (Full) - Event-based emission events for RDF/knowledge graphs
        # -------------------------------------------------------------------------
        jsonld_path = os.path.join(subdir, f"{base_filename}.jsonld")
        
        try:
            # Build event-based JSON-LD
            emission_events_jsonld = build_emission_events_jsonld(jsonld_data)
            
            with open(jsonld_path, 'w') as f:
                import json
                json.dump(emission_events_jsonld, f, indent=2)
            
            event_count = len(emission_events_jsonld.get('@graph', []))
            print(f"  ✓ JSON-LD (event-based): {base_filename}.jsonld ({event_count:,} events)")
        except PermissionError:
            print(f"  ⚠ JSON-LD export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ JSON-LD export failed: {str(e)}")
        
        # -------------------------------------------------------------------------
        # 5. JSON format (Sunburst) - D3.js-optimized hierarchy for visualization
        # -------------------------------------------------------------------------
        sunburst_path = os.path.join(subdir, f"{base_filename}_sunburst.json")
        
        try:
            # Build D3.js sunburst hierarchy
            sunburst_hierarchy = build_d3_sunburst_hierarchy(jsonld_data)
            
            with open(sunburst_path, 'w') as f:
                json.dump(sunburst_hierarchy, f, indent=2)
            
            # Count total nodes in hierarchy
            def count_nodes(node):
                count = 1
                if 'children' in node:
                    for child in node['children']:
                        count += count_nodes(child)
                return count
            
            total_nodes = count_nodes(sunburst_hierarchy)
            print(f"  ✓ JSON (sunburst): {base_filename}_sunburst.json ({total_nodes:,} nodes)")
            
            # Copy industry sunburst to docs/visualization/data for web visualization
            if suffix == '_industry':
                import shutil
                viz_data_dir = os.path.join(os.path.dirname(config_dict["output_dir"]), "docs", "visualization", "data")
                if os.path.exists(viz_data_dir):
                    viz_sunburst_path = os.path.join(viz_data_dir, "industry_sunburst.json")
                    try:
                        shutil.copy2(sunburst_path, viz_sunburst_path)
                        print(f"  ✓ Copied to visualization: docs/visualization/data/industry_sunburst.json")
                    except Exception as e:
                        print(f"  ⚠ Could not copy to visualization folder: {e}")
                        print(f"  → Manual step: Copy {base_filename}_sunburst.json to docs/visualization/data/industry_sunburst.json")
                else:
                    print(f"  ℹ Visualization folder not found: {viz_data_dir}")
                    print(f"  → To enable web visualization, manually copy:")
                    print(f"      {sunburst_path}")
                    print(f"      to docs/visualization/data/industry_sunburst.json")
        except PermissionError:
            print(f"  ⚠ Sunburst JSON export skipped - file is open")
        except Exception as e:
            print(f"  ⚠ Sunburst JSON export failed: {str(e)}")
    
    # Export GHG source classification (separate from sector-based data)
    print("\n" + "-"*80)
    print("Exporting GHG Source Classification...")
    print("-"*80)
    
    ghg_classification_dir = os.path.join(config_dict["output_dir"], "ghg_source_classification")
    os.makedirs(ghg_classification_dir, exist_ok=True)
    
    # Build classification structures from industry form data (most complete)
    ghg_classification_csv_df = build_ghg_source_classification_csv(enriched_data)
    ghg_classification_jsonld = build_ghg_source_classification_jsonld(enriched_data)
    
    # Export CSV
    ghg_classification_csv_path = os.path.join(
        ghg_classification_dir,
        f"{config.MODELNAME}_ghg_source_classification.csv"
    )
    try:
        ghg_classification_csv_df.to_csv(ghg_classification_csv_path, index=False)
        print(f"✓ GHG source classification CSV saved: {os.path.basename(ghg_classification_csv_path)}")
    except PermissionError:
        print(f"⚠ Permission denied: Close {os.path.basename(ghg_classification_csv_path)} if it's open")
    except Exception as e:
        print(f"⚠ Error saving GHG classification CSV: {e}")
    
    # Export JSON-LD
    ghg_classification_jsonld_path = os.path.join(
        ghg_classification_dir,
        f"{config.MODELNAME}_ghg_source_classification.jsonld"
    )
    try:
        with open(ghg_classification_jsonld_path, 'w') as f:
            import json
            json.dump(ghg_classification_jsonld, f, indent=2)
        print(f"✓ GHG source classification JSON-LD saved: {os.path.basename(ghg_classification_jsonld_path)}")
    except PermissionError:
        print(f"⚠ Permission denied: Close {os.path.basename(ghg_classification_jsonld_path)} if it's open")
    except Exception as e:
        print(f"⚠ Error saving GHG classification JSON-LD: {e}")
    
    print("\n" + "="*80)
    print("ALL OUTPUTS SAVED")
    print("="*80)
    print(f"Output directory: {config_dict['output_dir']}/")
    print(f"\nDirectory structure:")
    print(f"  - industry/: Emissions by producing industry")
    if commodity_data is not None:
        print(f"  - commodity/: Emissions by product/commodity (supply chain analysis)")
    print(f"  - ghg_source_classification/: GHG classification JSON-LD")
    print(f"\nFormat recommendations:")
    print(f"  - Excel: Manual analysis, visualization in Excel")
    print(f"  - CSV: Import into any tool, simple text format")
    print(f"  - Parquet: Python/R data science (pandas, polars, DuckDB)")
    print(f"  - JSON-LD: Event-based emission events for RDF/knowledge graphs")
    print(f"  - JSON (sunburst): D3.js-optimized hierarchy for visualization")
    print(f"  - JSON-LD (classification): GHG source taxonomy (ghg_source_classification/ folder)")



def main(fbs_calculated=None):
    """
    Main function to run the FlowBySector enrichment process.
    
    This function orchestrates the enrichment workflow:
    0. Validate FlowSA version
    1. Load configuration settings
    2. Use provided FlowBySector data (generated by run_extraction.py)
    3. Filter to relevant columns
    4. Load EPA GHGI metadata
    5. Enrich data with metadata
    6. Validate results
    7. Save outputs
    
    Parameters:
    -----------
    fbs_calculated : pandas.DataFrame, optional
        Pre-generated FlowBySector data with activity columns retained.
        If None, will raise an error (data must be generated externally).
    """
    print("="*80)
    print("FlowSA GHG SOURCES EXTRACTION - DATA ENRICHMENT")
    print("="*80)
    print(f"Processing model: {config.MODELNAME}")
    print(f"Model year: {config.MODEL_YEAR}")
    print(f"Description: {config.MODEL_DESCRIPTION}")
    print("="*80)
    
    # -------------------------------------------------------------------------
    # STEP 0: Validate FlowSA version
    # -------------------------------------------------------------------------
    validate_flowsa_version()
    
    # Create configuration dictionary for easy passing
    config_dict = {
        "input_path": config.FLOWSA_DATA_PATH,
        "subfolder": config.FLOWBYSECTOR_SUBFOLDER, 
        "file_name_parquet": config.FILE_NAME_PARQUET,
        "modelname": config.MODELNAME,
        "output_dir": config.OUTPUT_DIR,
    }
    
    # Ensure output directory exists
    os.makedirs(config_dict["output_dir"], exist_ok=True)


    # -------------------------------------------------------------------------
    # STEP 1: Load or download baseline parquet data (for comparison/export)
    # -------------------------------------------------------------------------
    fbs_parquet = None
    fbs_folder = os.path.join(config_dict["input_path"], config_dict["subfolder"])
    parquet_path = os.path.join(fbs_folder, config_dict["file_name_parquet"])
    
    print(f"Step 1: Checking for baseline parquet data...")
    print(f"  Path: {parquet_path}")
    print(f"  File exists: {os.path.exists(parquet_path)}")
    
    if os.path.exists(parquet_path):
        print("  ✓ Loading existing baseline parquet data...")
        fbs_parquet = load_parquet_data(
            config_dict["input_path"], 
            config_dict["subfolder"], 
            config_dict["file_name_parquet"]
        )
    else:
        # Download baseline using FlowSA's getFlowBySector function
        print("  ✗ Baseline parquet not found - need to download from FlowSA")
        print(f"\nWARNING: Baseline file missing")
        print(f"  Expected: {config_dict['file_name_parquet']}")
        print(f"  This file is needed for:")
        print(f"    - Sanity check (Step 2.5)")
        print(f"    - Baseline export (Excel tab and CSV)")
        
        user_input = input("\nDownload baseline from FlowSA? (yes/no) [default: no]: ").strip().lower()
        if not user_input:  # Empty input = use default
            user_input = 'no'
        
        if user_input in ['yes', 'y']:
            try:
                # Use FlowSA to download the baseline data (don't pass download_sources_ok, use default)
                print(f"  Downloading {config_dict['modelname']} using flowsa.getFlowBySector()...")
                fbs_parquet = flowsa.getFlowBySector(config_dict['modelname'])
                
                print(f"  ✓ Downloaded {len(fbs_parquet):,} records from FlowSA")
                
                # Save to the expected location with the EXACT filename from config
                os.makedirs(fbs_folder, exist_ok=True)
                fbs_parquet.to_parquet(parquet_path, engine='pyarrow', compression='snappy')
                print(f"  ✓ Saved baseline to: {parquet_path}")
                
                # Apply the same Location formatting as load_parquet_data
                fbs_parquet.Location = fbs_parquet.Location.apply('="{}"'.format)
                
            except Exception as e:
                print(f"  ⚠ Error downloading baseline parquet: {e}")
                print(f"  Continuing without baseline...")
                fbs_parquet = None
        else:
            print("  Continuing without baseline (sanity check and baseline export will be skipped)")
            fbs_parquet = None
    
    # -------------------------------------------------------------------------
    # STEP 2: Verify FlowBySector data was provided
    # -------------------------------------------------------------------------
    if fbs_calculated is None:
        raise ValueError(
            "FlowBySector data must be generated before calling main().\n"
            "This script should be called from run_extraction.py which generates the data."
        )
    
    print(f"\nStep 2: Using provided FlowBySector data ({len(fbs_calculated):,} records)...")
    
    # -------------------------------------------------------------------------
    # STEP 2.5: Sanity check - Compare with reference parquet (if available)
    # -------------------------------------------------------------------------
    if fbs_parquet is not None:
        print("\nStep 2.5: Running sanity check against reference parquet...")
        
        # Aggregate calculated data to match reference format (without activity columns)
        fbs_calculated_aggregated = aggregate_to_reference_format(fbs_calculated)
        
        # Compare aggregated calculated data with reference
        comparison_results = compare_with_reference(fbs_calculated_aggregated, fbs_parquet)
        
        # Optionally halt if sanity check fails
        if not (comparison_results["row_count_match"] and comparison_results["data_match"]):
            print("\n⚠️  WARNING: Sanity check detected differences!")
            print("Generated data does not exactly match reference parquet.")
            print("\nPossible causes:")
            print("1. FlowSA version mismatch - check that v2.0.3 is installed")
            print("2. Cached FlowByActivity files from different versions")
            print("\nTo fix cached data issues:")
            print("  python clear_flowsa_cache.py --activity-only")
            print("  (This will delete cached FlowByActivity files and force fresh downloads)")
            
            if config.STRICT_VERSION_CHECK:
                print("\nReview the differences above before proceeding.")
                user_input = input("\nContinue anyway? (yes/no) [default: yes]: ").strip().lower()
                if not user_input:  # Empty input = use default
                    user_input = 'yes'
                if user_input not in ['yes', 'y']:
                    print("Aborted by user.")
                    return
    
    # -------------------------------------------------------------------------  
    # STEP 3: Prepare data for enrichment (no column filtering yet)
    # -------------------------------------------------------------------------
    print("\nStep 3: Preparing data for enrichment...")
    fbs_filtered = fbs_calculated.copy()  # Keep all columns for now
    
    # -------------------------------------------------------------------------
    # STEP 4: Load EPA GHGI metadata mapping
    # -------------------------------------------------------------------------
    print("\nStep 4: Loading EPA GHGI metadata...")
    mapping_csv_path = os.path.join(config_dict["output_dir"], config.EPA_GHGI_META_CSV)
    meta_map = load_metadata_mapping(mapping_csv_path)
    
    # -------------------------------------------------------------------------
    # STEP 4.5: Load fuel lookup tables
    # -------------------------------------------------------------------------
    print("\nStep 4.5: Loading fuel lookup tables...")
    fuel_by_table = load_fuel_lookup(config.FUEL_BY_TABLE_CSV)
    fuel_by_term = load_fuel_lookup(config.FUEL_BY_TERM_CSV)
    
    # -------------------------------------------------------------------------
    # STEP 4.6: Load NAICS to USEEIO crosswalk
    # -------------------------------------------------------------------------
    print("\nStep 4.6: Loading NAICS to USEEIO crosswalk...")
    naics_to_useeio_dict = load_naics_to_useeio_crosswalk(config.NAICS_TO_USEEIO_CSV)
    
    # -------------------------------------------------------------------------
    # STEP 4.7: Load GHG Source categorization mapping
    # -------------------------------------------------------------------------
    print("\nStep 4.7: Loading GHG Source categorization mapping...")
    metasource_to_ghgsource_mapping = load_metasource_to_ghgsource_mapping(config.METASOURCE_TO_GHGSOURCE_CSV)
    
    # -------------------------------------------------------------------------
    # STEP 4.9: Load Flowable categorization
    # -------------------------------------------------------------------------
    print("\nStep 4.9: Loading Flowable categorization...")
    flowable_to_gas_dict = load_flowable_categorization(config.FLOWABLE_CATEGORIZATION_CSV)
    
    # -------------------------------------------------------------------------
    # STEP 4.10: Load IPCC AR5-100 GWP factors
    # -------------------------------------------------------------------------
    print("\nStep 4.10: Loading IPCC AR5-100 GWP factors...")
    uuid_to_gwp_dict = load_ipcc_ar5_100_gwp(config.IPCC_AR5_100_PARQUET)
    
    # -------------------------------------------------------------------------
    # STEP 4.11: Load USEEIO sector classification
    # -------------------------------------------------------------------------
    print("\nStep 4.11: Loading USEEIO sector classification...")
    sector_code_to_name = load_sector_classification(config.SECTOR_CLASSIFICATION_CSV)
    
    # -------------------------------------------------------------------------
    # STEP 5: Load method YAML and extract PrimaryActivity information
    # -------------------------------------------------------------------------
    print("\nStep 5: Loading method YAML for PrimaryActivity information...")
    
    # Determine the method YAML file path
    method_yaml_path = os.path.join(
        os.path.dirname(config_dict["input_path"]), 
        "Python workspace", 
        "Flowsa_extract_GHG_sources", 
        ".venv", 
        "Lib", 
        "site-packages", 
        "flowsa", 
        "methods", 
        "flowbysectormethods", 
        "GHG_national_m2_common_DecarbNexus.yaml"
    )
    
    # Try alternative path if the above doesn't work
    if not os.path.exists(method_yaml_path):
        method_yaml_path = os.path.join(
            os.getcwd(),
            ".venv",
            "Lib",
            "site-packages", 
            "flowsa",
            "methods",
            "flowbysectormethods",
            "GHG_national_m2_common_DecarbNexus.yaml"
        )
    
    # Load YAML and extract PrimaryActivity mapping
    yaml_content = load_method_yaml(method_yaml_path)
    primary_activity_mapping = extract_primary_activities_mapping(yaml_content) if yaml_content else {}
    
    # -------------------------------------------------------------------------
    # STEP 6: Enrich data with metadata (if metadata is available)
    # -------------------------------------------------------------------------
    if meta_map is not None and "MetaSources" in fbs_filtered.columns:
        print("\nStep 6: Enriching data with EPA GHGI metadata...")
        enriched_data = enrich_with_metadata(fbs_filtered, meta_map)
    else:
        print("\nStep 6: Skipping metadata enrichment (metadata not available)")
        enriched_data = fbs_filtered.copy()
        
        if "MetaSources" not in fbs_filtered.columns:
            print("  Reason: No 'MetaSources' column in FlowBySector data")
    
    # -------------------------------------------------------------------------
    # STEP 7.1: Enrich data with USEEIO sector codes
    # -------------------------------------------------------------------------
    print("\nStep 7.1: Enriching data with USEEIO sector codes...")
    enriched_data = enrich_with_useeio(enriched_data, naics_to_useeio_dict)
    
    # -------------------------------------------------------------------------
    # STEP 7.2: Enrich with USEEIO sector names
    # -------------------------------------------------------------------------
    print("\nStep 7.2: Enriching with USEEIO sector names...")
    enriched_data = enrich_with_useeio_sector_name(enriched_data, sector_code_to_name)
    
    # -------------------------------------------------------------------------
    # STEP 7.3: Enrich data with PrimaryActivity information
    # -------------------------------------------------------------------------
    print("\nStep 7.3: Enriching data with PrimaryActivity information...")
    enriched_data = enrich_with_primary_activities(enriched_data, primary_activity_mapping)
    
    # -------------------------------------------------------------------------
    # STEP 7.5: Enrich data with fuel type
    # -------------------------------------------------------------------------
    print("\nStep 7.5: Enriching data with fuel type...")
    enriched_data = enrich_with_fuel(enriched_data, fuel_by_table, fuel_by_term)
    
    # -------------------------------------------------------------------------
    # STEP 7.6: Enrich data with comprehensive GHG categorization
    # -------------------------------------------------------------------------
    print("\nStep 7.6: Enriching data with comprehensive GHG categorization...")
    enriched_data = enrich_with_ghg_source_categories(enriched_data, metasource_to_ghgsource_mapping)
    
    # -------------------------------------------------------------------------
    # STEP 7.7: Enrich data with Gas category
    # -------------------------------------------------------------------------
    print("\nStep 7.7: Enriching data with Gas category...")
    enriched_data = enrich_with_gas_category(enriched_data, flowable_to_gas_dict)
    
    # -------------------------------------------------------------------------
    # STEP 7.8: Enrich data with AR5-100 GWP and calculate MTCO2e
    # -------------------------------------------------------------------------
    print("\nStep 7.8: Enriching data with AR5-100 GWP and calculating MTCO2e...")
    enriched_data = enrich_with_ar5_100_gwp(enriched_data, uuid_to_gwp_dict)
    
    # -------------------------------------------------------------------------
    # STEP 7.9: Calculate contribution percentages by USEEIO sector
    # -------------------------------------------------------------------------
    print("\nStep 7.9: Calculating contribution percentages by USEEIO sector...")
    enriched_data = calculate_contribution_by_sector(enriched_data)
    
    # -------------------------------------------------------------------------
    # STEP 7.10: Rename columns and create emission columns
    # -------------------------------------------------------------------------
    print("\nStep 7.10: Renaming columns and creating emission columns...")
    enriched_data = rename_and_create_columns(enriched_data)
    
    # =========================================================================
    # INDUSTRY-TO-COMMODITY TRANSFORMATION
    # =========================================================================
    print("\n" + "="*80)
    print("INDUSTRY-TO-COMMODITY TRANSFORMATION")
    print("="*80)
    print("Converting industry-form emissions to commodity-form for USEEIO modeling")
    print("This enables supply chain analysis by product/commodity rather than by industry")
    print("="*80)
    
    # -------------------------------------------------------------------------
    # STEP 7.11: Load economic data files (x.csv and V_n.csv)
    # -------------------------------------------------------------------------
    print("\nStep 7.11: Loading economic data files...")
    
    # Path to data files
    x_csv_path = os.path.join(parent_dir, 'data', 'x.csv')
    v_n_csv_path = os.path.join(parent_dir, 'data', 'V_n.csv')
    
    # Check if files exist
    if not os.path.exists(x_csv_path):
        print(f"⚠ Warning: Industry output file not found: {x_csv_path}")
        print("  Skipping commodity transformation")
        industry_output_dict = None
        market_share_matrix = None
    elif not os.path.exists(v_n_csv_path):
        print(f"⚠ Warning: Market share matrix not found: {v_n_csv_path}")
        print("  Skipping commodity transformation")
        industry_output_dict = None
        market_share_matrix = None
    else:
        # Load industry output data (x.csv)
        industry_output_dict = load_industry_output(x_csv_path)
        
        # Load market share matrix (V_n.csv)
        market_share_matrix = load_market_share_matrix(v_n_csv_path)
    
    # -------------------------------------------------------------------------
    # STEP 7.12: Normalize and transform to commodity form
    # -------------------------------------------------------------------------
    commodity_data = None
    
    if industry_output_dict is not None and market_share_matrix is not None:
        print("\nStep 7.12: Normalizing and transforming to commodity form...")
        
        # Normalize emissions by industry output (adds intensity column to industry form too)
        enriched_data = normalize_emissions_by_output(enriched_data, industry_output_dict)
        
        # Transform to commodity form using V_n matrix
        commodity_data = transform_to_commodity_form(
            enriched_data, 
            market_share_matrix,
            sector_code_to_name
        )
        
        print(f"✓ Commodity transformation complete")
        print(f"  Industry form: {len(enriched_data):,} records (with emission intensity)")
        print(f"  Commodity form: {len(commodity_data):,} records (with emission intensity)")
        
        # -------------------------------------------------------------------------
        # STEP 7.13: Sort commodity data to match industry form
        # -------------------------------------------------------------------------
        print("\nStep 7.13: Sorting commodity data...")
        
        # Sort by USEEIO Sector Code, then by contribution (descending)
        sort_columns = []
        sort_ascending = []
        
        if "USEEIO Sector Code" in commodity_data.columns:
            sort_columns.append("USEEIO Sector Code")
            sort_ascending.append(True)
        
        if "Contribution to USEEIO Sector's Scope 1 (%)" in commodity_data.columns:
            sort_columns.append("Contribution to USEEIO Sector's Scope 1 (%)")
            sort_ascending.append(False)
        
        if sort_columns:
            commodity_data = commodity_data.sort_values(
                by=sort_columns,
                ascending=sort_ascending,
                na_position='last'
            )
            print(f"✓ Sorted commodity data by: {' → '.join(sort_columns)}")
        
        print(f"✓ Commodity data ready for export")
        print(f"  Records: {len(commodity_data):,}")
        print(f"  Columns: {len(commodity_data.columns)}")
    else:
        print("\nStep 7.12-7.13: Skipped (economic data files not found)")
        print("  Only industry form will be exported")
    
    print("="*80)
    print("TRANSFORMATION COMPLETE")
    print("="*80)
    
    # -------------------------------------------------------------------------
    # STEP 8: Validate data quality
    # -------------------------------------------------------------------------
    print("\nStep 8: Validating data quality...")
    validate_data(enriched_data, config_dict["modelname"])
    
    # -------------------------------------------------------------------------
    # STEP 9: Reorder columns and sort by USEEIO, NAICS, then contribution
    # -------------------------------------------------------------------------
    print("\nStep 9: Reordering columns and sorting data...")
    # Filter to columns that exist
    final_columns = [col for col in config.KEEP_COLUMNS if col in enriched_data.columns]
    enriched_data = enriched_data[final_columns]
    
    # Multi-level sort: USEEIO Sector Code → NAICS Sector Code → Contribution (desc)
    sort_columns = []
    sort_ascending = []
    
    if "USEEIO Sector Code" in enriched_data.columns:
        sort_columns.append("USEEIO Sector Code")
        sort_ascending.append(True)  # Ascending for sector codes
    
    if "NAICS Sector Code" in enriched_data.columns:
        sort_columns.append("NAICS Sector Code")
        sort_ascending.append(True)  # Ascending for sector codes
    
    if "Contribution to USEEIO Sector's Scope 1 (%)" in enriched_data.columns:
        sort_columns.append("Contribution to USEEIO Sector's Scope 1 (%)")
        sort_ascending.append(False)  # Descending for contribution
    
    if sort_columns:
        enriched_data = enriched_data.sort_values(
            by=sort_columns,
            ascending=sort_ascending,
            na_position='last'
        )
        print(f"✓ Sorted {len(enriched_data):,} records by: {' → '.join(sort_columns)}")
    
    # -------------------------------------------------------------------------
    # STEP 9.5: Add unique row identifier (after sorting)
    # -------------------------------------------------------------------------
    print("\nStep 9.5: Adding unique row identifiers...")
    
    # Add unique ID to industry form (1-based indexing)
    enriched_data.insert(0, 'Row ID', range(1, len(enriched_data) + 1))
    print(f"✓ Added Row ID to industry form: 1 to {len(enriched_data):,}")
    
    # Add unique ID to commodity form if it exists (separate sequence)
    if commodity_data is not None:
        commodity_data.insert(0, 'Row ID', range(1, len(commodity_data) + 1))
        print(f"✓ Added Row ID to commodity form: 1 to {len(commodity_data):,}")
    
    # Apply QC column filtering if configured
    if config.EXCLUDE_QC_COLUMNS and config.QC_ONLY_COLUMNS:
        qc_cols_to_remove = [col for col in config.QC_ONLY_COLUMNS if col in enriched_data.columns]
        if qc_cols_to_remove:
            enriched_data = enriched_data.drop(columns=qc_cols_to_remove)
            print(f"✓ Excluded {len(qc_cols_to_remove)} QC columns from output")
    
    print(f"✓ Final output has {len(enriched_data.columns)} columns")
    
    # -------------------------------------------------------------------------
    # STEP 10: Filter baseline data to relevant columns (for comparison)
    # -------------------------------------------------------------------------
    print("\nStep 10: Filtering baseline data to relevant columns...")
    fbs_filtered_final = filter_columns(
        fbs_filtered, 
        config.KEEP_COLUMNS,
        exclude_qc=config.EXCLUDE_QC_COLUMNS,
        qc_cols=config.QC_ONLY_COLUMNS
    )
    enriched_data_filtered = filter_columns(
        enriched_data, 
        config.KEEP_COLUMNS,
        exclude_qc=config.EXCLUDE_QC_COLUMNS,
        qc_cols=config.QC_ONLY_COLUMNS
    )
    
    # -------------------------------------------------------------------------
    # STEP 11: Save all outputs
    # -------------------------------------------------------------------------
    print("\nStep 11: Saving outputs...")
    save_outputs(fbs_parquet, fbs_filtered_final, enriched_data, config_dict, commodity_data=commodity_data)
    
    # -------------------------------------------------------------------------
    # COMPLETION SUMMARY
    # -------------------------------------------------------------------------
    print("="*80)
    print("PROCESSING COMPLETE!")
    print("="*80)
    print(f"✓ Model processed: {config_dict['modelname']}")
    print(f"\nIndustry form:")
    print(f"  Records: {len(enriched_data):,}")
    print(f"  Columns: {len(enriched_data.columns)}")
    
    if commodity_data is not None:
        print(f"\nCommodity form:")
        print(f"  Records: {len(commodity_data):,}")
        print(f"  Columns: {len(commodity_data.columns)}")
    
    # -------------------------------------------------------------------------
    # DATA ENRICHMENT SUMMARY - Count unique non-null/non-zero categories
    # -------------------------------------------------------------------------
    print(f"\n" + "="*80)
    print("ENRICHMENT SUMMARY - Unique Categories")
    print("="*80)
    
    # Helper function to count non-null, non-zero, non-empty values
    def count_unique_valid(df, col_name):
        if col_name not in df.columns:
            return 0
        # Filter out null, empty strings, and zeros
        valid_mask = df[col_name].notna() & (df[col_name] != '') & (df[col_name] != 0)
        return df.loc[valid_mask, col_name].nunique()
    
    # Count categories in industry form
    print("\nIndustry Form:")
    print("-" * 40)
    
    # Sectors
    useeio_count = count_unique_valid(enriched_data, 'USEEIO Sector Code')
    naics_count = count_unique_valid(enriched_data, 'NAICS Sector Code')
    print(f"  USEEIO Sectors: {useeio_count:,}")
    print(f"  NAICS Sectors: {naics_count:,}")
    
    # Activities (4-level hierarchy)
    activity_cat_count = count_unique_valid(enriched_data, 'Activity Category')
    activity_subcat_count = count_unique_valid(enriched_data, 'Activity Subcategory')
    activity_type_count = count_unique_valid(enriched_data, 'Activity Type')
    activity_count = count_unique_valid(enriched_data, 'Activity')
    print(f"\n  Activity Categories: {activity_cat_count:,}")
    print(f"  Activity Subcategories: {activity_subcat_count:,}")
    print(f"  Activity Types: {activity_type_count:,}")
    print(f"  Activities: {activity_count:,}")
    
    # Gases (2-level hierarchy)
    gas_cat_count = count_unique_valid(enriched_data, 'Gas Category')
    gas_count = count_unique_valid(enriched_data, 'Gas')
    print(f"\n  Gas Categories: {gas_cat_count:,}")
    print(f"  Gases: {gas_count:,}")
    
    # Fuels (independent dimension)
    fuel_count = count_unique_valid(enriched_data, 'Fuel Consumed')
    if fuel_count > 0:
        print(f"\n  Fuel Types: {fuel_count:,}")
    
    # IPCC Categories
    ipcc_count = count_unique_valid(enriched_data, 'IPCC/UNFCCC Category')
    if ipcc_count > 0:
        print(f"  IPCC Categories: {ipcc_count:,}")
    
    # EPA GHGI Tables
    ghgi_table_count = count_unique_valid(enriched_data, 'US GHGI Table ID')
    if ghgi_table_count > 0:
        print(f"  EPA GHGI Tables: {ghgi_table_count:,}")
    
    # Unique combinations (Activity hierarchy + Gas + Fuel)
    # Only count rows with valid emissions data
    combination_cols = ['Activity Category', 'Activity Subcategory', 'Activity Type', 'Activity', 
                       'Gas Category', 'Gas', 'Fuel Consumed']
    
    # Filter to rows with non-null/non-empty values and non-zero emissions
    combo_df = enriched_data.copy()
    has_emissions = (combo_df['Emissions (MTCO2e)'].notna()) & (combo_df['Emissions (MTCO2e)'] != 0)
    combo_df = combo_df[has_emissions]
    
    # Count unique combinations
    unique_combos = combo_df[combination_cols].drop_duplicates()
    print(f"\n  Unique Combinations (Activity + Gas + Fuel): {len(unique_combos):,}")
    
    # Commodity form statistics
    if commodity_data is not None:
        print("\n" + "-" * 40)
        print("Commodity Form:")
        print("-" * 40)
        comm_useeio_count = count_unique_valid(commodity_data, 'USEEIO Sector Code')
        print(f"  USEEIO Sectors: {comm_useeio_count:,}")
        
        # Activity hierarchy
        comm_activity_cat_count = count_unique_valid(commodity_data, 'Activity Category')
        comm_activity_subcat_count = count_unique_valid(commodity_data, 'Activity Subcategory')
        comm_activity_type_count = count_unique_valid(commodity_data, 'Activity Type')
        comm_activity_count = count_unique_valid(commodity_data, 'Activity')
        if comm_activity_cat_count > 0:
            print(f"\n  Activity Categories: {comm_activity_cat_count:,}")
        if comm_activity_subcat_count > 0:
            print(f"  Activity Subcategories: {comm_activity_subcat_count:,}")
        if comm_activity_type_count > 0:
            print(f"  Activity Types: {comm_activity_type_count:,}")
        if comm_activity_count > 0:
            print(f"  Activities: {comm_activity_count:,}")
        
        # Gas hierarchy
        comm_gas_cat_count = count_unique_valid(commodity_data, 'Gas Category')
        comm_gas_count = count_unique_valid(commodity_data, 'Gas')
        if comm_gas_cat_count > 0:
            print(f"\n  Gas Categories: {comm_gas_cat_count:,}")
        if comm_gas_count > 0:
            print(f"  Gases: {comm_gas_count:,}")
        
        # Fuel types
        comm_fuel_count = count_unique_valid(commodity_data, 'Fuel Consumed')
        if comm_fuel_count > 0:
            print(f"\n  Fuel Types: {comm_fuel_count:,}")
        
        # Unique combinations for commodity form
        comm_combination_cols = ['Activity Category', 'Activity Subcategory', 'Activity Type', 'Activity', 
                                'Gas Category', 'Gas', 'Fuel Consumed']
        
        # Filter to rows with non-null/non-empty values and non-zero emissions
        comm_combo_df = commodity_data.copy()
        comm_has_emissions = (comm_combo_df['Emissions (MTCO2e)'].notna()) & (comm_combo_df['Emissions (MTCO2e)'] != 0)
        comm_combo_df = comm_combo_df[comm_has_emissions]
        
        # Count unique combinations
        comm_unique_combos = comm_combo_df[comm_combination_cols].drop_duplicates()
        print(f"\n  Unique Combinations (Activity + Gas + Fuel): {len(comm_unique_combos):,}")
    
    print("="*80)
    
    print(f"\nNext steps:")
    print("1. Review the output files in the '{config_dict['output_dir']}/' directory")
    print("2. Use industry form for direct emission analysis by producing sector")
    if commodity_data is not None:
        print("3. Use commodity form for USEEIO supply chain analysis (emissions by product)")
    else:
        print("3. Add x.csv and V_n.csv to enable commodity form transformation")
    print("4. Check data quality validation results above")
    print("\nFor questions or issues, refer to the project documentation.")
    print("="*80)


if __name__ == "__main__":
    print("ERROR: This script should not be run directly.")
    print("Please use: python scripts/run_extraction.py")
    print("\nThe run_extraction.py script orchestrates the full workflow:")
    print("  1. Extract EPA GHGI metadata")
    print("  2. Generate FlowBySector data")
    print("  3. Enrich with metadata (this script)")
    import sys
    sys.exit(1)


