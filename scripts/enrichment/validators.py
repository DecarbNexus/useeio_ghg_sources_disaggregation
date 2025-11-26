"""
Data Validation Functions for FlowBySector Processing

This module contains functions for validating enriched data and comparing
calculated results with reference datasets.
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))
import config
# COLUMN_MAPPING removed - using direct column names


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
                    meta_info = fbs_reference[fbs_reference["FlowUUID"] == uuid]["MetaSource"].iloc[0] if "MetaSource" in fbs_reference.columns else "N/A"
                    print(f"     - {uuid} (MetaSource: {meta_info})")
                if len(only_in_ref) > 10:
                    print(f"     ... and {len(only_in_ref) - 10} more")
            
            if only_in_calc:
                print(f"\n   FlowUUIDs only in calculated ({len(only_in_calc)}):")
                for uuid in list(only_in_calc)[:10]:
                    meta_info = fbs_calculated[fbs_calculated["FlowUUID"] == uuid]["MetaSource"].iloc[0] if "MetaSource" in fbs_calculated.columns else "N/A"
                    print(f"     - {uuid} (MetaSource: {meta_info})")
                if len(only_in_calc) > 10:
                    print(f"     ... and {len(only_in_calc) - 10} more")
    
    # TODO: Add column comparison logic
    # TODO: Add data value comparison logic
    # TODO: Add summary statistics comparison
    
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


# TODO: Add more validation functions as needed during incremental migration
# Candidates from enrich_fbs_with_meta.py:
# - validate_sector_codes()
# - validate_flow_names()
# - check_data_completeness()
# - validate_attribution_percentages()
# - etc.
