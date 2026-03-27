"""
Utility Functions for FlowBySector Data Processing

This module contains helper functions used across the enrichment pipeline.
"""

import os
import sys
import subprocess
import pandas as pd
from pathlib import Path

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(parent_dir))
import config


def get_emissions_intensity_col():
    """
    Get the emissions intensity column name with the model year.
    
    Returns:
    --------
    str
        Column name like "Emissions Intensity (kg/USD_2022)"
    """
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
        print(f"[SUCCESS] Created Emissions (kg): {kg_count:,} records")
        print(f"[SUCCESS] Created Emissions (kgCO2e): {kgco2e_count:,} records")
    
    print(f"[SUCCESS] Renamed {len([k for k in rename_map.keys() if k in fbs_data.columns])} columns")
    
    return enriched_data



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

def get_emissions_intensity_col():
    """Get the emissions intensity column name with the model year."""
    return f"Emissions Intensity (kg/USD_{config.MODEL_YEAR})"


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


def count_unique_valid(df, col_name):
    """Count unique non-null, non-empty, non-zero values in a DataFrame column."""
    if col_name not in df.columns:
        return 0
    valid_mask = df[col_name].notna() & (df[col_name] != '') & (df[col_name] != 0)
    return df.loc[valid_mask, col_name].nunique()