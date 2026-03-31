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