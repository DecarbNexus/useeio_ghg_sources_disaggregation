"""
Emission Transformation Functions for FlowBySector Processing

This module contains functions for normalizing emissions by industry output
and transforming industry-form emissions to commodity-form using the USEEIO
make matrix (V_n) via matrix multiplication, matching useeior's B = B_industry %*% V_n.
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(parent_dir))
import config
from .utils import get_emissions_intensity_col, get_emissions_intensity_kgco2e_col, get_emissions_intensity_mtco2e_musd_col


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
    print(f"[SUCCESS] Calculated contribution fractions for {contrib_count:,} records (stored as decimals 0-1)")
    
    return enriched_data


def normalize_emissions_by_output(df, adjusted_output_dict):
    """
    Normalize emissions by CPI-adjusted industry output to get emission intensities (kg/USD).
    
    Uses the CbS denominator from useeior: adjustOutputbyCPI(2022, 2017, "US", FALSE, model, "Industry"),
    i.e. 2022 industry output deflated to 2017$ using sector-specific CPI.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Enriched data with emissions in kg
    adjusted_output_dict : dict
        Dictionary mapping USEEIO sector codes to CPI-adjusted output values in USD
        (from data/adjusted_output.csv, exported by R)
        
    Returns:
    --------
    pandas.DataFrame
        Data with added 'Emissions Intensity (kg/USD_YYYY)' column
    """
    print("Normalizing emissions by CPI-adjusted industry output...")
    
    df_normalized = df.copy()
    
    df_normalized['Industry Output (USD)'] = df_normalized['USEEIO Sector Code'].map(adjusted_output_dict)
    
    missing_count = df_normalized['Industry Output (USD)'].isna().sum()
    if missing_count > 0:
        missing_codes = df_normalized[df_normalized['Industry Output (USD)'].isna()]['USEEIO Sector Code'].unique()
        print(f"  Warning: {missing_count:,} records have missing industry output values")
        print(f"    Missing USEEIO codes: {', '.join(sorted(missing_codes)[:10])}")
        if len(missing_codes) > 10:
            print(f"    ... and {len(missing_codes) - 10} more")
    
    valid_mask = df_normalized['Industry Output (USD)'].notna() & (df_normalized['Industry Output (USD)'] > 0)
    
    emissions_intensity_col = get_emissions_intensity_col()
    df_normalized.loc[valid_mask, emissions_intensity_col] = (
        df_normalized.loc[valid_mask, 'Emissions (kg)'] / 
        df_normalized.loc[valid_mask, 'Industry Output (USD)']
    )
    
    valid_count = valid_mask.sum()
    total_kg = df_normalized.loc[valid_mask, 'Emissions (kg)'].sum()
    total_output = df_normalized.loc[valid_mask, 'Industry Output (USD)'].sum()
    avg_intensity = total_kg / total_output if total_output > 0 else 0
    
    print(f"[SUCCESS] Calculated emission intensities for {valid_count:,} records")
    print(f"  Total emissions: {total_kg:,.0f} kg")
    print(f"  Total adjusted output: ${total_output:,.0f}")
    print(f"  Average intensity: {avg_intensity:.6e} kg/USD")

    # ----- CO2e intensity -----
    # Rows with valid output AND a kgCO2e value (includes CO2e-only gases where Emissions (kg) is null)
    kgco2e_intensity_col = get_emissions_intensity_kgco2e_col()
    mtco2e_musd_intensity_col = get_emissions_intensity_mtco2e_musd_col()

    valid_co2e_mask = valid_mask & df_normalized['Emissions (kgCO2e)'].notna()
    df_normalized.loc[valid_co2e_mask, kgco2e_intensity_col] = (
        df_normalized.loc[valid_co2e_mask, 'Emissions (kgCO2e)']
        / df_normalized.loc[valid_co2e_mask, 'Industry Output (USD)']
    )
    # MTCO2e/million_USD = kgCO2e/USD × 1000  (1 MT = 1000 kg; 1M USD = 1e6 USD → net factor 1000)
    df_normalized.loc[valid_co2e_mask, mtco2e_musd_intensity_col] = (
        df_normalized.loc[valid_co2e_mask, kgco2e_intensity_col] * 1000
    )

    co2e_count = valid_co2e_mask.sum()
    # CO2e-only rows: gases reported only in CO2e units (e.g. HFCs/PFCs unspecified)
    co2e_only_mask = (
        df_normalized['Emissions (kg)'].isna()
        & df_normalized['Emissions (kgCO2e)'].notna()
        & valid_mask
    )
    co2e_only_count = co2e_only_mask.sum()
    co2e_only_total = df_normalized.loc[co2e_only_mask, 'Emissions (kgCO2e)'].sum()
    print(f"[SUCCESS] Calculated kgCO2e/USD intensities for {co2e_count:,} records")
    print(f"  CO2e-only rows (null kg, excluded from kg/USD intensity): {co2e_only_count:,} rows, "
          f"{co2e_only_total:,.0f} kgCO2e")

    return df_normalized


def transform_to_commodity_form(df_normalized, market_share_matrix, commodity_output_dict, sector_code_to_name):
    """
    Transform industry-form emissions to commodity-form using V_n market share matrix.
    
    Uses matrix multiplication matching useeior's B = B_industry %*% V_n:
    
    1. Pivot industry-form intensities into a matrix:
       rows = unique (Flowable, Context, ...) combinations, cols = BEA industry codes
    2. Matrix multiply: intensity_commodity = intensity_industry @ V_n
    3. Unpivot back to long-form DataFrame
    4. Recalculate all quantity columns from commodity intensity × q_j
    
    Parameters:
    -----------
    df_normalized : pandas.DataFrame
        Normalized data with emission intensities
    market_share_matrix : pandas.DataFrame
        V_n matrix (industries × commodities)
    commodity_output_dict : dict
        Dictionary mapping USEEIO commodity codes to CPI-adjusted output values in USD
        (from data/adjusted_commodity_output.csv, exported by R — same 2017$ basis as
        the industry denominator so intensities and absolute values are consistent)
    sector_code_to_name : dict
        Mapping of USEEIO sector codes to names
        
    Returns:
    --------
    pandas.DataFrame
        Commodity-form data with recalculated emissions
    """
    print("Transforming to commodity form using matrix multiply (B_industry @ V_n)...")

    emissions_intensity_col = get_emissions_intensity_col()
    kgco2e_intensity_col = get_emissions_intensity_kgco2e_col()
    mtco2e_musd_intensity_col = get_emissions_intensity_mtco2e_musd_col()

    # Only process records with valid kg intensities (first pass)
    valid_mask = df_normalized[emissions_intensity_col].notna()
    df_to_transform = df_normalized[valid_mask].copy()

    # Save industry-form kgCO2e total for conservation check later
    _industry_kgco2e_total = (
        df_normalized.loc[df_normalized[kgco2e_intensity_col].notna(), 'Emissions (kgCO2e)'].sum()
    )
    
    print(f"  Processing {len(df_to_transform):,} records with valid kg emission intensities (first pass)")
    
    # ----- Step 1: Identify grouping dimensions (everything except sector and quantities) -----
    # These columns define unique "flow" rows in the intensity matrix
    group_cols = [
        'Activity Category',
        'IPCC/UNFCCC Category',
        'IPCC Category Code',
        'Activity Subcategory',
        'Activity Type',
        'Activity',
        'Fuel',
        'Gas Category',
        'Gas',
        'US GHGI Table ID',
        'US GHGI Chapter',
        'US GHGI Table Name',
        'Attribution Sources',
        'AR5-100 GWP',
    ]
    group_cols = [col for col in group_cols if col in df_to_transform.columns]
    
    # ----- Step 2: Aggregate intensity by (group_cols, USEEIO Sector Code) -----
    # Multiple records per (industry, flow) get summed into a single intensity
    agg_df = (
        df_to_transform
        .groupby(group_cols + ['USEEIO Sector Code'], dropna=False)
        .agg({emissions_intensity_col: 'sum'})
        .reset_index()
    )
    
    print(f"  Aggregated to {len(agg_df):,} (flow, industry) pairs")
    
    # ----- Step 3: Create a composite row key for the intensity matrix -----
    # Assign a unique integer ID to each group_cols combination
    group_keys = agg_df[group_cols].drop_duplicates().reset_index(drop=True)
    group_keys['_flow_id'] = range(len(group_keys))
    agg_df = agg_df.merge(group_keys, on=group_cols, how='left')
    
    # ----- Step 4: Pivot to matrix form -----
    # rows = _flow_id, cols = USEEIO Sector Code, values = intensity
    intensity_industry = agg_df.pivot_table(
        index='_flow_id',
        columns='USEEIO Sector Code',
        values=emissions_intensity_col,
        aggfunc='sum',
        fill_value=0.0,
    )
    
    print(f"  Industry intensity matrix: {intensity_industry.shape[0]} flows × {intensity_industry.shape[1]} industries")
    
    # ----- Step 5: Align columns with V_n rows (industries) -----
    # V_n index = industry codes, V_n columns = commodity codes
    common_industries = intensity_industry.columns.intersection(market_share_matrix.index)
    missing_industries = set(intensity_industry.columns) - set(common_industries)
    if missing_industries:
        print(f"  Warning: {len(missing_industries)} industry codes not in V_n: {sorted(missing_industries)[:5]}")
    
    # Subset and align
    I_aligned = intensity_industry.reindex(columns=common_industries, fill_value=0.0)
    V_aligned = market_share_matrix.reindex(index=common_industries, fill_value=0.0)
    
    # ----- Step 6: Matrix multiply -----
    # intensity_commodity = intensity_industry @ V_n  (flows × commodities)
    intensity_commodity = I_aligned.values @ V_aligned.values
    intensity_commodity_df = pd.DataFrame(
        intensity_commodity,
        index=I_aligned.index,
        columns=V_aligned.columns,
    )
    
    print(f"  Commodity intensity matrix: {intensity_commodity_df.shape[0]} flows × {intensity_commodity_df.shape[1]} commodities")
    
    # ----- Step 7: Unpivot back to long form -----
    intensity_commodity_df.index.name = '_flow_id'
    commodity_long = intensity_commodity_df.reset_index().melt(
        id_vars='_flow_id',
        var_name='USEEIO Sector Code',
        value_name=emissions_intensity_col,
    )
    
    # Drop zero-intensity records (no contribution from that industry to that commodity)
    commodity_long = commodity_long[commodity_long[emissions_intensity_col].abs() > 1e-20].copy()
    
    # Merge back the group columns
    commodity_long = commodity_long.merge(group_keys, on='_flow_id', how='left')
    commodity_long.drop(columns='_flow_id', inplace=True)
    
    print(f"  Unpivoted to {len(commodity_long):,} non-zero commodity records")
    
    # ----- Step 8: Recalculate quantity columns from intensity × q_j -----
    commodity_long['Emissions (kg)'] = commodity_long.apply(
        lambda r: r[emissions_intensity_col] * commodity_output_dict.get(r['USEEIO Sector Code'], 0),
        axis=1,
    )
    commodity_long['FlowAmount'] = commodity_long['Emissions (kg)']

    # Recalculate GWP-derived columns
    gwp_col = 'AR5-100 GWP'
    if gwp_col in commodity_long.columns:
        commodity_long['Emissions (kgCO2e)'] = commodity_long['Emissions (kg)'] * commodity_long[gwp_col]
        commodity_long['Emissions (MTCO2e)'] = commodity_long['Emissions (kgCO2e)'] / 1_000_000

    # Set NAICS Sector Code to None (not meaningful for commodity form)
    commodity_long['NAICS Sector Code'] = None

    # Enrich with USEEIO Sector Names
    commodity_long['USEEIO Sector Name'] = commodity_long['USEEIO Sector Code'].map(sector_code_to_name)

    # ----- Step 8b: Second pass — CO2e-only gases (e.g. HFCs/PFCs reported only in kg CO2e) -----
    # These rows have a valid kgCO2e intensity but no kg intensity (Emissions (kg) was null).
    co2e_only_src_mask = (
        df_normalized[kgco2e_intensity_col].notna()
        & df_normalized[emissions_intensity_col].isna()
    )
    df_co2e_only = df_normalized[co2e_only_src_mask].copy()

    if not df_co2e_only.empty:
        print(f"  Second pass: {len(df_co2e_only):,} CO2e-only industry records → commodity form...")

        # Re-use the same group dimensions
        co2e_group_cols = [col for col in group_cols if col in df_co2e_only.columns]

        co2e_agg_df = (
            df_co2e_only
            .groupby(co2e_group_cols + ['USEEIO Sector Code'], dropna=False)
            .agg({kgco2e_intensity_col: 'sum'})
            .reset_index()
        )

        co2e_group_keys = co2e_agg_df[co2e_group_cols].drop_duplicates().reset_index(drop=True)
        co2e_group_keys['_flow_id'] = range(len(co2e_group_keys))
        co2e_agg_df = co2e_agg_df.merge(co2e_group_keys, on=co2e_group_cols, how='left')

        co2e_intensity_industry = co2e_agg_df.pivot_table(
            index='_flow_id',
            columns='USEEIO Sector Code',
            values=kgco2e_intensity_col,
            aggfunc='sum',
            fill_value=0.0,
        )

        co2e_common = co2e_intensity_industry.columns.intersection(market_share_matrix.index)
        co2e_I = co2e_intensity_industry.reindex(columns=co2e_common, fill_value=0.0)
        co2e_V = market_share_matrix.reindex(index=co2e_common, fill_value=0.0)

        co2e_commodity_matrix = co2e_I.values @ co2e_V.values
        co2e_commodity_df = pd.DataFrame(
            co2e_commodity_matrix,
            index=co2e_I.index,
            columns=co2e_V.columns,
        )
        co2e_commodity_df.index.name = '_flow_id'

        co2e_long = co2e_commodity_df.reset_index().melt(
            id_vars='_flow_id',
            var_name='USEEIO Sector Code',
            value_name=kgco2e_intensity_col,
        )
        co2e_long = co2e_long[co2e_long[kgco2e_intensity_col].abs() > 1e-20].copy()
        co2e_long = co2e_long.merge(co2e_group_keys, on='_flow_id', how='left')
        co2e_long.drop(columns='_flow_id', inplace=True)

        # Recalculate absolute quantities from commodity kgCO2e intensity × q_j
        co2e_long['Emissions (kgCO2e)'] = co2e_long.apply(
            lambda r: r[kgco2e_intensity_col] * commodity_output_dict.get(r['USEEIO Sector Code'], 0),
            axis=1,
        )
        co2e_long['Emissions (MTCO2e)'] = co2e_long['Emissions (kgCO2e)'] / 1_000_000
        co2e_long['Emissions (kg)'] = None   # no kg equivalent for CO2e-only gases
        co2e_long['FlowAmount'] = co2e_long['Emissions (kgCO2e)']
        co2e_long['NAICS Sector Code'] = None
        co2e_long['USEEIO Sector Name'] = co2e_long['USEEIO Sector Code'].map(sector_code_to_name)

        print(f"  CO2e-only second pass: {len(co2e_long):,} non-zero commodity records")
        commodity_long = pd.concat([commodity_long, co2e_long], ignore_index=True)

    # ----- Step 8c: Compute CO2e intensity columns for all commodity rows -----
    q_series = commodity_long['USEEIO Sector Code'].map(commodity_output_dict)
    valid_q = q_series.notna() & (q_series > 0) & commodity_long['Emissions (kgCO2e)'].notna()
    commodity_long[kgco2e_intensity_col] = None
    commodity_long[mtco2e_musd_intensity_col] = None
    commodity_long.loc[valid_q, kgco2e_intensity_col] = (
        commodity_long.loc[valid_q, 'Emissions (kgCO2e)'] / q_series[valid_q]
    )
    commodity_long.loc[valid_q, mtco2e_musd_intensity_col] = (
        commodity_long.loc[valid_q, kgco2e_intensity_col] * 1000
    )

    # kgCO2e conservation check
    commodity_total_kgco2e = commodity_long['Emissions (kgCO2e)'].sum()
    co2e_ratio = commodity_total_kgco2e / _industry_kgco2e_total if _industry_kgco2e_total > 0 else float('nan')
    print(f"  kgCO2e conservation — Industry: {_industry_kgco2e_total:,.0f}  "
          f"Commodity: {commodity_total_kgco2e:,.0f}  Ratio: {co2e_ratio:.4f}")

    # ----- Step 9: Contribution % by commodity sector -----
    print("  Calculating contribution percentages for commodity form...")
    commodity_long = calculate_contribution_by_sector(commodity_long)
    
    # ----- Step 10: Reorder columns -----
    column_order = [
        'USEEIO Sector Name',
        'USEEIO Sector Code',
        'NAICS Sector Code',
        'Activity Category',
        'IPCC/UNFCCC Category',
        'IPCC Category Code',
        'Activity Subcategory',
        'Activity Type',
        'Activity',
        'Fuel',
        'Gas Category',
        'Gas',
        'Emissions (kg)',
        get_emissions_intensity_col(),
        'AR5-100 GWP',
        'Emissions (kgCO2e)',
        get_emissions_intensity_kgco2e_col(),
        'Emissions (MTCO2e)',
        get_emissions_intensity_mtco2e_musd_col(),
        "Contribution to USEEIO Sector's Scope 1 (%)",
        'US GHGI Chapter',
        'US GHGI Table ID',
        'US GHGI Table Name',
        'Attribution Sources',
    ]
    final_columns = [col for col in column_order if col in commodity_long.columns]
    commodity_long = commodity_long[final_columns]
    
    # ----- Conservation check (informational) -----
    original_total_kg = df_to_transform['Emissions (kg)'].sum()
    commodity_total_kg = commodity_long['Emissions (kg)'].sum()
    ratio = commodity_total_kg / original_total_kg if original_total_kg > 0 else float('nan')
    
    print(f"[SUCCESS] Commodity transform complete:")
    print(f"  Industry form: {original_total_kg:,.0f} kg")
    print(f"  Commodity form: {commodity_total_kg:,.0f} kg")
    print(f"  Commodity/Industry ratio: {ratio:.4f} (CPI-adjusted denominators; not expected to be 1.0)")
    
    return commodity_long