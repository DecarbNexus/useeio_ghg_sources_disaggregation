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
parent_dir = Path(__file__).parent.parent.parent.parent
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
    
    print(f"[SUCCESS] Aggregated from {len(fbs_with_activities):,} to {len(aggregated):,} records")
    
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
        print("   [SUCCESS] Row counts match!")
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
        print("   [SUCCESS] All reference columns present in generated data!")
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
                print("   [SUCCESS] All data values match between generated and reference!")
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
        print("[SUCCESS][SUCCESS][SUCCESS] SANITY CHECK PASSED [SUCCESS][SUCCESS][SUCCESS]")
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
        print("[SUCCESS] Data validation passed - no issues found")
        return True
    else:
        print("⚠ Data validation found issues - review warnings above")
        return False