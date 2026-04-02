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
import config
from .utils import _extract_meta_id, _deduplicate_and_simplify_activities


def _prompt_continue(issue_description, saved_path):
    """Warn about a data mismatch, print the saved file path, then optionally halt."""
    print(f"\n  [MISMATCH] {issue_description}")
    print(f"  File saved: {saved_path}")
    try:
        answer = input("  Continue? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = ''
    if answer in ('n', 'no'):
        print("  Stopping. Re-run after reviewing the file.")
        sys.exit(0)


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
    records_matched = merged["chapter"].notna().sum() if "chapter" in merged.columns else 0
    match_rate = (records_matched / len(merged)) * 100
    
    print(f"[SUCCESS] Successfully matched {records_matched:,} records with EPA GHGI metadata ({match_rate:.1f}%)")
    
    return merged

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
    
    print(f"[SUCCESS] Processed {processed_count:,} records with MetaSources (non-direct)")
    print(f"[SUCCESS] Added PrimaryActivity from direct attribution: {direct_count:,} records")
    print(f"[SUCCESS] Added PrimaryActivity from YAML mapping: {yaml_count:,} records")
    print(f"[SUCCESS] Total PrimaryActivity enrichment: {enriched_count:,} records")
    
    return enriched_data

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
    print(f"[SUCCESS] Added Activity Set to {total_enriched:,} records")
    print(f"  - From PrimaryActivity (direct): {direct_count:,}")
    print(f"  - From CSV lookup: {lookup_count:,}")
    
    return enriched_data

def enrich_with_useeio(fbs_data, naics_to_useeio_dict, allocation_dict=None):
    """
    Enrich FlowBySector data with USEEIO sector codes.
    
    Maps NAICS codes in SectorProducedBy to USEEIO codes using the crosswalk.
    When a NAICS code maps to multiple BEA codes and allocation_dict is provided,
    the row is expanded into N rows with FlowAmount weighted by allocation factor.
    
    Parameters:
    -----------
    fbs_data : pandas.DataFrame
        FlowBySector data with SectorProducedBy column containing NAICS codes
    naics_to_useeio_dict : dict
        Dictionary mapping NAICS codes to lists of USEEIO codes (1:many)
    allocation_dict : dict, optional
        Nested dict {NAICS_Code: {BEA_Code: weight, ...}} from R export.
        When provided, 1:many mappings expand rows and weight FlowAmount.
        
    Returns:
    --------
    pandas.DataFrame
        Enhanced DataFrame with "USEEIO" column added (rows may be expanded)
    """
    if "SectorProducedBy" not in fbs_data.columns:
        print("Skipping USEEIO enrichment - SectorProducedBy column not found")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with USEEIO sector codes...")
    
    rows = []
    matched_count = 0
    expanded_count = 0
    
    for _, row in fbs_data.iterrows():
        sector_produced_by = row.get("SectorProducedBy", "")
        
        if pd.isna(sector_produced_by) or not sector_produced_by:
            row_copy = row.copy()
            row_copy['USEEIO'] = None
            rows.append(row_copy)
            continue
        
        naics_code = str(sector_produced_by).strip()
        
        if naics_code not in naics_to_useeio_dict:
            row_copy = row.copy()
            row_copy['USEEIO'] = None
            rows.append(row_copy)
            continue
        
        useeio_codes = naics_to_useeio_dict[naics_code]
        
        if len(useeio_codes) == 1:
            # Simple 1:1 mapping
            row_copy = row.copy()
            row_copy['USEEIO'] = useeio_codes[0]
            rows.append(row_copy)
            matched_count += 1
        else:
            # 1:many — expand rows with allocation weights
            weights = allocation_dict.get(naics_code, {}) if allocation_dict else {}
            
            for bea_code in useeio_codes:
                weight = weights.get(bea_code, 1.0 / len(useeio_codes))
                row_copy = row.copy()
                row_copy['USEEIO'] = bea_code
                # Weight FlowAmount (only quantity column that exists at this stage)
                if 'FlowAmount' in row_copy.index and pd.notna(row_copy['FlowAmount']):
                    row_copy['FlowAmount'] = row_copy['FlowAmount'] * weight
                rows.append(row_copy)
            
            matched_count += 1
            expanded_count += len(useeio_codes) - 1
    
    enriched_data = pd.DataFrame(rows)
    enriched_data.reset_index(drop=True, inplace=True)
    
    print(f"[SUCCESS] Added USEEIO code to {matched_count:,} records")
    if expanded_count > 0:
        print(f"  Expanded {expanded_count:,} additional rows from 1:many NAICS->BEA mappings")
        print(f"  Total rows: {len(fbs_data):,} -> {len(enriched_data):,}")
    
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
    print(f"[SUCCESS] Matched {match_count:,} / {len(enriched_data):,} records ({match_rate:.1f}%)")
    
    return enriched_data

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
    enriched_data['IPCC Category Code'] = None
    enriched_data['Activity Category'] = None
    enriched_data['Activity Subcategory'] = None
    enriched_data['Activity Type'] = None
    
    matched_count = 0
    matched_mapping_indices = set()

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
            enriched_data.at[idx, 'IPCC Category Code'] = match.iloc[0].get('IPCC Category Code', '')
            enriched_data.at[idx, 'Activity Category'] = match.iloc[0]['Activity Category']
            enriched_data.at[idx, 'Activity Subcategory'] = match.iloc[0]['Activity Subcategory']
            
            # Activity Type might be empty in the CSV
            activity_type = match.iloc[0].get('Activity Type', '')
            if pd.notna(activity_type) and activity_type:
                enriched_data.at[idx, 'Activity Type'] = activity_type
            
            matched_count += 1
            matched_mapping_indices.update(match.index.tolist())

    print(f"[SUCCESS] Added comprehensive GHG categorization to {matched_count:,} records")
    print(f"  - IPCC/UNFCCC Category")
    print(f"  - IPCC Category Code")
    print(f"  - Activity Category")
    print(f"  - Activity Subcategory")
    print(f"  - Activity Type (where applicable)")

    # Detect rows with a MetaSources value that found no mapping entry
    unmatched_mask = (
        enriched_data['Activity Category'].isna()
        & enriched_data['MetaSources'].notna()
        & (enriched_data['MetaSources'].astype(str).str.strip() != '')
    )

    # CSV-side unmatched: mapping rows whose (MetaSources, ActivityProducedBy) pair
    # was never used to fill in any dataset row during this run.
    csv_unmatched = (
        mapping_df.loc[~mapping_df.index.isin(matched_mapping_indices),
                       ['MetaSources', 'ActivityProducedBy']]
        .drop_duplicates()
        .sort_values(['MetaSources', 'ActivityProducedBy'])
        .reset_index(drop=True)
    )

    if unmatched_mask.any():
        unmatched_count = int(unmatched_mask.sum())
        unmatched_pairs = (
            enriched_data.loc[unmatched_mask, ['MetaSources', 'ActivityProducedBy']]
            .drop_duplicates()
            .sort_values(['MetaSources', 'ActivityProducedBy'])
            .reset_index(drop=True)
        )
        print(f"\n  WARNING: {unmatched_count:,} rows had no match in activity_categorization.csv")
        print(f"  Unique unmatched (MetaSources, ActivityProducedBy) pairs: {len(unmatched_pairs)}")
        for _, up_row in unmatched_pairs.iterrows():
            apb = up_row['ActivityProducedBy']
            apb_str = repr(apb) if pd.notna(apb) and str(apb).strip() else '(empty)'
            print(f"    MetaSources={up_row['MetaSources']!r}  ActivityProducedBy={apb_str}")
    else:
        unmatched_pairs = pd.DataFrame(columns=['MetaSources', 'ActivityProducedBy'])
        print(f"  All rows with MetaSources matched successfully.")

    if not unmatched_pairs.empty or not csv_unmatched.empty:
        unmatched_path = os.path.join(config.OUTPUT_DIR, 'unmatched_activity_categorization.xlsx')
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        with pd.ExcelWriter(unmatched_path, engine='openpyxl') as writer:
            unmatched_pairs.to_excel(writer, sheet_name='Dataset Unmatched', index=False)
            csv_unmatched.to_excel(writer, sheet_name='CSV Unmatched', index=False)
        print(f"  Saved unmatched pairs to: {unmatched_path}")
        if not csv_unmatched.empty:
            print(f"  CSV-side: {len(csv_unmatched)} mapping rows were never used by any dataset row")
        print(f"  To fix: add a row for each pair to {config.METASOURCE_TO_GHGSOURCE_CSV}")
        print(f"  See docs/USER_GUIDE.md § 'Filling gaps in activity_categorization.csv'")
        _prompt_continue(
            f"{len(unmatched_pairs)} dataset (MetaSources, ActivityProducedBy) pairs had no match; "
            f"{len(csv_unmatched)} CSV rows were never used",
            unmatched_path
        )

    return enriched_data

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
    
    print(f"[SUCCESS] Added Gas category to {matched_count:,} records")
    
    return enriched_data

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
    print(f"[SUCCESS] Added AR5-100 GWP to {total_enriched:,} records")
    print(f"  - From IPCC lookup (kg -> MTCO2e): {matched_count:,}")
    print(f"  - Already in CO2e (kg CO2e -> MTCO2e): {already_co2e_count:,}")
    print(f"[SUCCESS] Calculated Emissions (MTCO2e) for {total_enriched:,} records")
    
    if unmatched_flowables:
        print(f"⚠ Warning: {len(unmatched_flowables)} flowables without AR5-100 GWP factors:")
        for flowable in sorted(unmatched_flowables):
            print(f"  - {flowable}")
    
    return enriched_data

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
    enriched_data['Fuel'] = None
    
    table_match_count = 0
    term_match_count = 0
    term_override_count = 0  # Track when term lookup overrides table lookup
    matched_table_keys = set()
    
    # Step 1: Match by table reference (fallback)
    if fuel_by_table and "MetaSources" in fbs_data.columns:
        print("  Step 1: Matching by table reference...")
        for idx, row in enriched_data.iterrows():
            meta_sources = row.get("MetaSources", "")
            
            if pd.isna(meta_sources) or not meta_sources:
                continue
            
            # Match semantics are driven by the CSV key format:
            # - A suffix key (e.g. EPA_GHGI_T_A_5.non_manufacturing_natural_gas) targets
            #   only that exact activity set → try exact match first.
            # - A suffix-less key (e.g. EPA_GHGI_T_3_14) acts as a wildcard for all
            #   activity sets from that table → fall back to the prefix if no exact match.
            meta_sources_key = str(meta_sources).strip()
            lookup_key = meta_sources_key if meta_sources_key in fuel_by_table \
                else meta_sources_key.split('.')[0]
            if lookup_key in fuel_by_table:
                enriched_data.at[idx, 'Fuel'] = fuel_by_table[lookup_key]
                table_match_count += 1
                matched_table_keys.add(lookup_key)
    
    # Step 2: Match by term in PrimaryActivity (overrides table matches if found - more precise)
    if fuel_by_term and "PrimaryActivity" in fbs_data.columns:
        print("  Step 2: Matching by terms in PrimaryActivity...")
        
        # Sort lookup terms by length (longest first) to prioritize more specific terms
        sorted_lookup = sorted(fuel_by_term.items(), key=lambda x: len(x[0]), reverse=True)
        
        # Track which fuels and terms were found
        fuels_found = set()
        matched_terms = set()
    else:
        print("  Step 2: SKIPPED - Condition failed:")
        print(f"    fuel_by_term exists: {fuel_by_term is not None and len(fuel_by_term) > 0}")
        print(f"    PrimaryActivity column exists: {'PrimaryActivity' in fbs_data.columns}")
        if fuel_by_term:
            print(f"    fuel_by_term has {len(fuel_by_term)} entries")
        sorted_lookup = []
        fuels_found = set()
        matched_terms = set()
    
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
                        matched_terms.add(lookup_term)
                    
                    start_pos = pos + 1
            
            # If we found matches, join them with " | " and store (overrides table lookup)
            if matched_fuels:
                had_table_match = pd.notna(enriched_data.at[idx, 'Fuel']) and enriched_data.at[idx, 'Fuel'] != ''
                enriched_data.at[idx, 'Fuel'] = ' | '.join(sorted(matched_fuels.keys()))
                if had_table_match:
                    term_override_count += 1
                else:
                    term_match_count += 1
    
    # Final count: table matches that weren't overridden + new term matches + term overrides
    final_table_only = table_match_count - term_override_count
    total_matched = final_table_only + term_match_count + term_override_count
    print(f"[SUCCESS] Added fuel type to {total_matched:,} records")
    print(f"  - By table reference only: {final_table_only:,}")
    print(f"  - By term matching (new): {term_match_count:,}")
    print(f"  - By term matching (override): {term_override_count:,}")

    # Detect unmatched dataset rows (MetaSources present but no fuel assigned)
    fuel_unmatched_mask = (
        enriched_data['Fuel'].isna()
        & enriched_data['MetaSources'].notna()
        & (enriched_data['MetaSources'].astype(str).str.strip() != '')
    )
    dataset_unmatched_fuel = (
        enriched_data.loc[fuel_unmatched_mask, ['MetaSources', 'PrimaryActivity']]
        .drop_duplicates()
        .sort_values(['MetaSources', 'PrimaryActivity'])
        .reset_index(drop=True)
    )

    # CSV-side unmatched: table keys and term keys never triggered during this run
    csv_unmatched_table = pd.DataFrame(
        [(k, v) for k, v in fuel_by_table.items() if k not in matched_table_keys],
        columns=['Key', 'Fuel']
    ).assign(Source='Table').sort_values('Key').reset_index(drop=True)

    csv_unmatched_terms = pd.DataFrame(
        [(k, v) for k, v in fuel_by_term.items() if k not in matched_terms],
        columns=['Key', 'Fuel']
    ).assign(Source='Term').sort_values('Key').reset_index(drop=True)

    csv_unmatched_fuel = pd.concat(
        [csv_unmatched_table, csv_unmatched_terms], ignore_index=True
    )[['Source', 'Key', 'Fuel']]

    if not dataset_unmatched_fuel.empty or not csv_unmatched_fuel.empty:
        fuel_unmatched_path = os.path.join(config.OUTPUT_DIR, 'unmatched_fuel.xlsx')
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        with pd.ExcelWriter(fuel_unmatched_path, engine='openpyxl') as writer:
            dataset_unmatched_fuel.to_excel(writer, sheet_name='Dataset Unmatched', index=False)
            csv_unmatched_fuel.to_excel(writer, sheet_name='CSV Unmatched', index=False)
        print(f"\n  Dataset rows with no fuel: {len(dataset_unmatched_fuel)} unique (MetaSources, PrimaryActivity) pairs")
        if not csv_unmatched_fuel.empty:
            print(f"  CSV entries never used: {len(csv_unmatched_fuel)} ({len(csv_unmatched_table)} table, {len(csv_unmatched_terms)} term)")
        print(f"  Saved fuel unmatched pairs to: {fuel_unmatched_path}")
        _prompt_continue(
            f"{len(dataset_unmatched_fuel)} dataset rows had no fuel match; "
            f"{len(csv_unmatched_fuel)} CSV entries were never used",
            fuel_unmatched_path
        )

    return enriched_data