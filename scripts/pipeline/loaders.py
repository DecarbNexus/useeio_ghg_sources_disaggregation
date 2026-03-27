"""
Data Loading Functions for FlowBySector Processing

This module contains functions for loading various data sources including
parquet files, CSV mappings, YAML configurations, and lookups.
"""

import os
import re
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent.parent
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
    
    print(f"[SUCCESS] Loaded {len(fbs_parquet):,} records from parquet file")
    
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
            print(f"[SUCCESS] Found cached FBS data: {cache_file}")
            print(f"  Loading from: {cache_path}")
            fbs_data = pd.read_parquet(cache_path)
            print(f"[SUCCESS] Loaded {len(fbs_data):,} records from FlowSA cache")
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
        print(f"[SUCCESS] Loaded {len(fbs_data):,} records")
        return fbs_data
    elif os.path.exists(csv_path):
        print(f"Loading from local file: {csv_path}")
        fbs_data = pd.read_csv(csv_path)
        print(f"[SUCCESS] Loaded {len(fbs_data):,} records")
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
        print(f"[SUCCESS] Loaded {len(meta_map):,} metadata records")
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
        
        print(f"[SUCCESS] Loaded {len(lookup_dict):,} fuel lookup entries")
        return lookup_dict
    else:
        print(f"Warning: fuel lookup file not found at {lookup_csv_path}")
        return None

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
        
        print(f"[SUCCESS] Loaded {len(activity_sets_dict)} activity set mappings")
        return activity_sets_dict
    except Exception as e:
        print(f"Error loading activity sets lookup: {e}")
        return {}

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
        Dictionary mapping NAICS codes to lists of USEEIO codes (1:many)
    """
    if not os.path.exists(csv_path):
        print(f"Warning: NAICS to USEEIO crosswalk file not found at {csv_path}")
        return {}
    
    try:
        df = pd.read_csv(csv_path)
        
        # Create dictionary: NAICS -> [USEEIO, ...]
        # Use setdefault to handle 1:many mappings correctly
        naics_to_useeio = {}
        for _, row in df.iterrows():
            naics = str(row['NAICS']).strip()
            useeio = str(row['USEEIO']).strip()
            naics_to_useeio.setdefault(naics, []).append(useeio)
        
        multi_count = sum(1 for v in naics_to_useeio.values() if len(v) > 1)
        print(f"[SUCCESS] Loaded {len(naics_to_useeio)} NAICS to USEEIO mappings ({multi_count} are 1:many)")
        return naics_to_useeio
    except Exception as e:
        print(f"Error loading NAICS to USEEIO crosswalk: {e}")
        return {}

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
        print(f"[SUCCESS] Loaded {len(df)} GHG Source categorization mappings")
        print(f"  Columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        print(f"Error loading GHG Source categorization: {e}")
        return None

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
        
        print(f"[SUCCESS] Loaded {len(flowable_to_gas)} flowable categorizations")
        return flowable_to_gas
    except Exception as e:
        print(f"Error loading flowable categorization: {e}")
        return {}

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
        print(f"[SUCCESS] Loaded {len(code_to_name)} sector classifications")
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
        
        print(f"[SUCCESS] Loaded {len(uuid_to_gwp)} {indicator} GWP factors (context: {context})")
        return uuid_to_gwp
    except Exception as e:
        print(f"Error loading IPCC GWP factors: {e}")
        return {}

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
    
    print(f"[SUCCESS] Loaded {len(output_dict):,} industry output values")
    print(f"  Total output: ${sum(output_dict.values()):,.0f}")
    print(f"  Min: ${min(output_dict.values()):,.0f}, Max: ${max(output_dict.values()):,.0f}")
    
    return output_dict


def load_commodity_output(csv_path):
    """
    Load CPI-adjusted commodity output for the industry-to-commodity back-conversion.

    Uses adjusted_commodity_output.csv (adjustOutputbyCPI(..., "Commodity")), which
    puts 2022 commodity output on the same 2017$ basis as the industry denominator,
    so that E_commodity = B_commodity * q_adjusted is internally consistent.

    Parameters:
    -----------
    csv_path : str
        Path to adjusted_commodity_output.csv (exported from R)
        
    Returns:
    --------
    dict
        Dictionary mapping USEEIO sector code (without /US suffix) to output value in USD
    """
    print(f"Loading commodity output data from: {csv_path}")
    
    df = pd.read_csv(csv_path, index_col=0)
    df.index = df.index.str.replace('/US', '', regex=False)
    output_dict = df.iloc[:, 0].to_dict()
    
    print(f"[SUCCESS] Loaded {len(output_dict):,} commodity output values")
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
    
    print(f"[SUCCESS] Loaded V_n matrix: {len(df)} industries × {len(df.columns)} commodities")
    
    # Validate: each COLUMN should sum to approximately 1.0
    # V_n is normalized by commodity output q, so V_n[:,j] = V[:,j] / q_j
    # and sum_i(V_n[i,j]) = sum_i(V[i,j]) / q_j = q_j / q_j = 1
    col_sums = df.sum(axis=0)
    max_deviation = abs(col_sums - 1.0).max()
    
    if max_deviation > 0.01:  # Allow 1% deviation
        print(f"  ⚠ Warning: Maximum column sum deviation from 1.0: {max_deviation:.4f}")
    else:
        print(f"  [SUCCESS] Column sums validated (max deviation: {max_deviation:.6f})")
    
    return df


def load_naics_bea_allocation(csv_path):
    """
    Load NAICS-to-BEA allocation weights (pre-baked from R).
    
    The allocation weights are based on industry output and come from
    useeior's getNAICStoBEAAllocation(). They handle the case where
    one NAICS code maps to multiple BEA (USEEIO) sector codes.
    
    Parameters:
    -----------
    csv_path : str
        Path to naics_bea_allocation.csv
        
    Returns:
    --------
    dict
        Nested dict: {NAICS_Code: {BEA_Code: allocation_factor, ...}, ...}
    """
    if not os.path.exists(csv_path):
        print(f"Warning: NAICS-BEA allocation file not found at {csv_path}")
        return {}
    
    print(f"Loading NAICS-BEA allocation weights from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    allocation = {}
    for _, row in df.iterrows():
        naics = str(row['NAICS_Code']).strip()
        bea = str(row['BEA_Code']).strip()
        weight = float(row['allocation_factor'])
        allocation.setdefault(naics, {})[bea] = weight
    
    print(f"[SUCCESS] Loaded allocation weights for {len(allocation)} NAICS codes")
    return allocation


def load_adjusted_output(csv_path):
    """
    Load CPI-adjusted industry output (the CbS denominator from useeior).
    
    This is the result of useeior's adjustOutputbyCPI(2022, 2017, "US", FALSE, model, "Industry"),
    i.e. 2022 industry output deflated to 2017 dollars using sector-specific CPI.
    
    Parameters:
    -----------
    csv_path : str
        Path to adjusted_output.csv (exported from R)
        
    Returns:
    --------
    dict
        Dictionary mapping USEEIO sector code (without /US suffix) to adjusted output in USD
    """
    if not os.path.exists(csv_path):
        print(f"Warning: Adjusted output file not found at {csv_path}")
        return {}
    
    print(f"Loading CPI-adjusted industry output from: {csv_path}")
    df = pd.read_csv(csv_path, index_col=0)
    
    # Strip "/US" suffix from index to get clean USEEIO codes
    df.index = df.index.str.replace('/US', '', regex=False)
    
    # The value column name from R is like "2022IndustryOutput"
    output_dict = df.iloc[:, 0].to_dict()
    
    print(f"[SUCCESS] Loaded {len(output_dict):,} adjusted output values")
    print(f"  Total adjusted output: ${sum(output_dict.values()):,.0f}")
    
    return output_dict


def load_b_matrix(csv_path):
    """
    Load the B matrix (flows × commodities) exported from useeior for QC/QA.
    
    Parameters:
    -----------
    csv_path : str
        Path to B_matrix.csv
        
    Returns:
    --------
    pandas.DataFrame
        B matrix with flow identifiers as rows, commodity codes as columns
    """
    if not os.path.exists(csv_path):
        print(f"Warning: B matrix file not found at {csv_path}")
        return pd.DataFrame()
    
    print(f"Loading B matrix from: {csv_path}")
    df = pd.read_csv(csv_path, index_col=0)
    
    # Strip "/US" suffix from columns (commodity codes)
    df.columns = df.columns.str.replace('/US', '', regex=False)
    
    print(f"[SUCCESS] Loaded B matrix: {len(df)} flows × {len(df.columns)} commodities")
    return df