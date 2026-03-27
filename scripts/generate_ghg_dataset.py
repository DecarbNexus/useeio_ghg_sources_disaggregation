#!/usr/bin/env python3
"""
FlowSA GHG Sources Extraction - Simple Runner

This script provides an easy way to run the complete GHG sources extraction workflow.
It handles the full pipeline:
1. Extract EPA GHGI metadata from FlowSA YAML
2. Generate FlowBySector data using FlowSA (with interactive prompt to use cached data)
3. Enrich data with metadata (fuel types, activities, sectors, etc.)
4. Export enriched data in multiple formats

The script automatically filters out sector F01000 (used goods) from all outputs
as it does not produce emissions.

Usage:
    python generate_ghg_dataset.py              # Run with prompts (recommended)
    python generate_ghg_dataset.py --help       # Show all options
    python generate_ghg_dataset.py --skip-fbs-generation  # Use cached FlowBySector data
    python generate_ghg_dataset.py --force-fbs-generation # Generate new without prompt
"""

import os
import sys
import re
import subprocess
import pandas as pd
import numpy as np
import argparse
import flowsa
from pathlib import Path
from ruamel.yaml import YAML

# Add parent directory to path for imports (config.py is at root)
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))  # Add project root for config.py and terminology.py
sys.path.append(str(current_dir))  # Add scripts/ so 'pipeline' package is importable

# Import configuration settings and terminology
import config
from terminology import TERMINOLOGY, get_jsonld_property

# Import modularized enrichment functions
from pipeline.utils import (
    get_emissions_intensity_col,
    check_flowsa_version,
    validate_flowsa_version,
    filter_columns,
    rename_and_create_columns,
    _extract_meta_id,
    count_unique_valid,
)
from pipeline.validators import (
    aggregate_to_reference_format,
    compare_with_reference,
    validate_data
)
from pipeline.loaders import (
    load_parquet_data,
    load_metadata_mapping,
    load_fuel_lookup,
    load_generated_fbs_data,
    load_activity_sets_lookup,
    load_naics_to_useeio_crosswalk,
    load_metasource_to_ghgsource_mapping,
    load_flowable_categorization,
    load_sector_classification,
    load_ipcc_ar5_100_gwp,
    load_method_yaml,
    extract_primary_activities_mapping,
    load_industry_output,
    load_commodity_output,
    load_market_share_matrix,
    load_naics_bea_allocation,
    load_adjusted_output,
    load_b_matrix,
)
from pipeline.enrichers import (
    enrich_with_fuel,
    enrich_with_useeio,
    enrich_with_primary_activities,
    enrich_with_metadata,
    enrich_with_useeio_sector_name,
    enrich_with_activity_sets,
    enrich_with_ghg_source_categories,
    enrich_with_gas_category,
    enrich_with_ar5_100_gwp,
)
from pipeline.exporters import (
    build_emission_events_jsonld,
    build_d3_sunburst_hierarchy,
    save_outputs
)
from pipeline.transform import (
    calculate_contribution_by_sector,
    normalize_emissions_by_output,
    transform_to_commodity_form,
)

def print_banner():
    """Print a nice banner for the tool."""
    print("="*80)
    print("FLOWSA GHG SOURCES EXTRACTION")
    print("Generating supply chain emission factors from EPA data")
    print("="*80)


def check_requirements():
    """Check if required packages are installed and versions match."""
    import config
    
    print("Checking requirements...")
    
    required_packages = ['pandas', 'flowsa', 'ruamel.yaml', 'pyarrow']
    missing_packages = []
    
    for package in required_packages:
        try:
            mod = __import__(package)
            print(f"  [OK] {package}")
            
            # Special check for FlowSA version
            if package == 'flowsa' and config.STRICT_VERSION_CHECK:
                try:
                    import importlib.metadata
                    version = importlib.metadata.version('flowsa')
                except:
                    try:
                        version = mod.__version__
                    except:
                        version = "unknown"
                
                # Handle both single version string and list
                required_versions = config.REQUIRED_FLOWSA_VERSION
                if isinstance(required_versions, str):
                    required_versions = [required_versions]
                
                print(f"       FlowSA version: {version}")
                print(f"       Required: {' or '.join(required_versions)} (tag: {config.REQUIRED_FLOWSA_GIT_TAG})")
                
                if version not in required_versions:
                    print(f"       [WARNING] Version mismatch detected!")
                    print(f"       To install correct version:")
                    print(f"         python install_flowsa_2.0.3.py")
                    
        except ImportError:
            missing_packages.append(package)
            print(f"  [MISSING] {package}")
    
    if missing_packages:
        print(f"\nMISSING PACKAGES: {', '.join(missing_packages)}")
        print("Please install with: pip install " + " ".join(missing_packages))
        return False
    
    print("SUCCESS: All requirements satisfied!")
    return True


def run_metadata_extraction():
    """Run EPA GHGI metadata extraction."""
    print("\nStep 1: Extracting EPA GHGI metadata...")
    
    try:
        from tools.extract_metadata import main as extract_main
        extract_main()
        print("SUCCESS: Metadata extraction completed!")
        return True
    except Exception as e:
        print(f"ERROR: Metadata extraction failed: {e}")
        return False


def generate_flowbysector_data(modelname):
    """
    Generate FlowBySector data using FlowSA.
    
    This function generates fresh FBS data each time it's called.
    FlowSA will download FlowByActivity source data and cache it locally.
    
    Parameters:
    -----------
    modelname : str
        FlowSA model name (e.g., 'GHG_national_2022_m2')
        
    Returns:
    --------
    pandas.DataFrame
        Generated FlowBySector data with activity columns retained
    """
    import flowsa
    import pandas as pd
    
    print("\nGenerating FlowBySector data using FlowSA...")
    print("This downloads FlowByActivity data and generates FBS...")
    print("This may take several minutes...")
    
    # Generate FlowBySector data using FlowSA
    # Constants (not configurable - required for this workflow):
    #   - download_sources_ok=True: Download FlowByActivity source data
    #   - retain_activity_columns=True: Preserve activity details for enrichment
    #   - append_sector_names=False: We add USEEIO names during enrichment
    fbs_data = pd.DataFrame(flowsa.flowbysector.FlowBySector.generateFlowBySector(
        modelname,
        download_sources_ok=True,
        retain_activity_columns=True,
        append_sector_names=False
    ))
    
    print(f"[OK] Generated {len(fbs_data):,} records using FlowSA")
    
    return fbs_data


def run_fbs_generation(skip_generation=False, force_generation=False):
    """Generate FlowBySector data with activity details retained.
    
    Parameters:
    -----------
    skip_generation : bool
        If True, skip generation and use cached data
    force_generation : bool
        If True, force new generation without prompting
    """
    import config
    import pandas as pd
    
    print("\nStep 2: FlowBySector Data Generation")
    print("="*60)
    
    # Check if cached FBS data exists
    cache_dir = Path.home() / "AppData" / "Local" / "flowsa" / "FlowBySector"
    cached_files = list(cache_dir.glob(f"{config.MODELNAME}*.parquet")) if cache_dir.exists() else []
    
    if cached_files:
        print(f"Found {len(cached_files)} cached FBS file(s) for {config.MODELNAME}")
        for file in cached_files[:3]:  # Show first 3
            file_size = file.stat().st_size / (1024*1024)  # MB
            print(f"  - {file.name} ({file_size:.1f} MB)")
        if len(cached_files) > 3:
            print(f"  ... and {len(cached_files) - 3} more")
    else:
        print(f"No cached FBS data found for {config.MODELNAME}")
    
    # Handle command-line flags
    if force_generation:
        print("\n--force-fbs-generation flag set, generating new data...")
        should_generate = True
    elif skip_generation:
        print("\n--skip-fbs-generation flag set, using cached data...")
        should_generate = False
    else:
        # Interactive prompt
        print("\nGenerate new FlowBySector data?")
        print("  YES: Download fresh data and generate new FBS (may take several minutes)")
        print("  NO:  Use existing cached FBS data (if available)")
        
        while True:
            response = input("\nGenerate new FBS? [y/N]: ").strip().lower()
            
            if response in ['y', 'yes']:
                should_generate = True
                break
            elif response in ['n', 'no', '']:
                should_generate = False
                break
            else:
                print("Please answer 'y' (yes) or 'n' (no)")
                continue
    
    # Generate or load based on decision
    if should_generate:
        print("\nGenerating new FlowBySector data...")
        print("This will download FlowByActivity source data and generate FBS...")
        print("This may take several minutes...")
        
        try:
            fbs_data = generate_flowbysector_data(config.MODELNAME)
            print(f"[OK] Generated {len(fbs_data):,} FBS records!")
            return fbs_data
        except Exception as e:
            print(f"ERROR: FBS generation failed: {e}")
            return None
    else:
        # Try to load cached data
        print("\nUsing cached FBS data...")
        
        if not cached_files:
            print("ERROR: No cached FBS data found!")
            print("Please run again with --force-fbs-generation or answer 'yes' to the prompt")
            return None
        
        # Use the most recent cached file
        latest_file = max(cached_files, key=lambda f: f.stat().st_mtime)
        print(f"Loading cached file: {latest_file.name}")
        
        try:
            fbs_data = pd.read_parquet(latest_file)
            # Format Location column to match generated format
            fbs_data.Location = fbs_data.Location.apply('="{}"'.format)
            print(f"[OK] Loaded {len(fbs_data):,} FBS records from cache")
            return fbs_data
        except Exception as e:
            print(f"ERROR: Failed to load cached data: {e}")
            return None


def _load_pipeline_inputs(config_dict):
    """Load all reference data needed by the enrichment pipeline.

    Returns a dict with keys: meta_map, fuel_by_table, fuel_by_term,
    naics_to_useeio_dict, metasource_to_ghgsource_mapping, flowable_to_gas_dict,
    uuid_to_gwp_dict, sector_code_to_name, primary_activity_mapping.
    """
    print("\n--- Loading pipeline inputs ---")

    meta_map = load_metadata_mapping(os.path.join(config_dict["output_dir"], config.EPA_GHGI_META_CSV))
    fuel_by_table = load_fuel_lookup(config.FUEL_BY_TABLE_CSV)
    fuel_by_term = load_fuel_lookup(config.FUEL_BY_TERM_CSV)
    naics_to_useeio_dict = load_naics_to_useeio_crosswalk(config.NAICS_TO_USEEIO_CSV)
    allocation_dict = load_naics_bea_allocation(config.NAICS_BEA_ALLOCATION_CSV)
    metasource_to_ghgsource_mapping = load_metasource_to_ghgsource_mapping(config.METASOURCE_TO_GHGSOURCE_CSV)
    flowable_to_gas_dict = load_flowable_categorization(config.FLOWABLE_CATEGORIZATION_CSV)
    uuid_to_gwp_dict = load_ipcc_ar5_100_gwp(config.IPCC_AR5_100_PARQUET)
    sector_code_to_name = load_sector_classification(config.SECTOR_CLASSIFICATION_CSV)

    method_yaml_path = os.path.join(
        os.path.dirname(config_dict["input_path"]),
        "Python workspace", "Flowsa_extract_GHG_sources", ".venv",
        "Lib", "site-packages", "flowsa", "methods",
        "flowbysectormethods", "GHG_national_m2_common_DecarbNexus.yaml"
    )
    if not os.path.exists(method_yaml_path):
        method_yaml_path = os.path.join(
            os.getcwd(), ".venv", "Lib", "site-packages",
            "flowsa", "methods", "flowbysectormethods",
            "GHG_national_m2_common_DecarbNexus.yaml"
        )
    yaml_content = load_method_yaml(method_yaml_path)
    primary_activity_mapping = extract_primary_activities_mapping(yaml_content) if yaml_content else {}

    return {
        "meta_map": meta_map,
        "fuel_by_table": fuel_by_table,
        "fuel_by_term": fuel_by_term,
        "naics_to_useeio_dict": naics_to_useeio_dict,
        "allocation_dict": allocation_dict,
        "metasource_to_ghgsource_mapping": metasource_to_ghgsource_mapping,
        "flowable_to_gas_dict": flowable_to_gas_dict,
        "uuid_to_gwp_dict": uuid_to_gwp_dict,
        "sector_code_to_name": sector_code_to_name,
        "primary_activity_mapping": primary_activity_mapping,
    }


def _run_enrichment_pipeline(fbs_filtered, inputs):
    """Apply the full enrichment chain to FBS data.

    Runs: metadata → USEEIO codes+names → PrimaryActivity → fuel →
    GHG categorization → gas category → AR5-100 GWP → contribution % → column rename.
    Returns enriched_data DataFrame.
    """
    print("\n--- Enrichment pipeline ---")

    # EPA GHGI metadata
    if inputs["meta_map"] is not None and "MetaSources" in fbs_filtered.columns:
        print("  Enriching with EPA GHGI metadata...")
        enriched_data = enrich_with_metadata(fbs_filtered, inputs["meta_map"])
    else:
        print("  Skipping metadata enrichment (metadata not available or no MetaSources column)")
        enriched_data = fbs_filtered.copy()

    # USEEIO sector codes and names (combined into one step)
    print("  Enriching with USEEIO sector codes and names...")
    enriched_data = enrich_with_useeio(enriched_data, inputs["naics_to_useeio_dict"], inputs.get("allocation_dict"))
    enriched_data = enrich_with_useeio_sector_name(enriched_data, inputs["sector_code_to_name"])

    # PrimaryActivity
    print("  Enriching with PrimaryActivity information...")
    enriched_data = enrich_with_primary_activities(enriched_data, inputs["primary_activity_mapping"])

    # Fuel type
    print("  Enriching with fuel type...")
    enriched_data = enrich_with_fuel(enriched_data, inputs["fuel_by_table"], inputs["fuel_by_term"])

    # GHG source categorization
    print("  Enriching with GHG source categorization...")
    enriched_data = enrich_with_ghg_source_categories(enriched_data, inputs["metasource_to_ghgsource_mapping"])

    # Gas category
    print("  Enriching with gas category...")
    enriched_data = enrich_with_gas_category(enriched_data, inputs["flowable_to_gas_dict"])

    # AR5-100 GWP → Emissions (MTCO2e)
    print("  Enriching with AR5-100 GWP and calculating MTCO2e...")
    enriched_data = enrich_with_ar5_100_gwp(enriched_data, inputs["uuid_to_gwp_dict"])

    # Contribution % by USEEIO sector
    print("  Calculating contribution % by USEEIO sector...")
    enriched_data = calculate_contribution_by_sector(enriched_data)

    # Rename/create columns
    print("  Renaming columns and creating emission columns...")
    enriched_data = rename_and_create_columns(enriched_data)

    return enriched_data


def _run_commodity_transformation(enriched_data, inputs):
    """Transform industry-form emissions to commodity-form using economic data files.

    Uses CPI-adjusted industry output (adjusted_output.csv), commodity output (q.csv),
    and the V_n market-share matrix via matrix multiply (B_industry @ V_n).

    Returns (commodity_data, enriched_data). enriched_data is returned because
    normalize_emissions_by_output adds an intensity column to it.
    commodity_data is None if any economic data file is missing.
    """
    print("\n--- Industry-to-commodity transformation ---")

    adjusted_output_path = os.path.join(parent_dir, 'data', 'adjusted_output.csv')
    v_n_csv_path = os.path.join(parent_dir, 'data', 'V_n.csv')
    adj_commodity_path = os.path.join(parent_dir, 'data', 'adjusted_commodity_output.csv')

    missing = [p for p in [adjusted_output_path, v_n_csv_path, adj_commodity_path] if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"  Warning: Economic data file not found: {p}")
        print("  Skipping commodity transformation — only industry form will be exported")
        print("  Run 'Rscript scripts/setup/export_reference_data.R' to generate missing files")
        return None, enriched_data

    adjusted_output_dict = load_adjusted_output(adjusted_output_path)
    commodity_output_dict = load_commodity_output(adj_commodity_path)
    market_share_matrix = load_market_share_matrix(v_n_csv_path)

    # Normalize emissions by CPI-adjusted industry output (also adds intensity column)
    enriched_data = normalize_emissions_by_output(enriched_data, adjusted_output_dict)

    # Transform to commodity form using V_n market-share matrix
    commodity_data = transform_to_commodity_form(
        enriched_data, market_share_matrix, commodity_output_dict, inputs["sector_code_to_name"]
    )

    # Sort commodity data: USEEIO Sector Code → Contribution % desc
    sort_cols, sort_asc = [], []
    if "USEEIO Sector Code" in commodity_data.columns:
        sort_cols.append("USEEIO Sector Code"); sort_asc.append(True)
    if "Contribution to USEEIO Sector's Scope 1 (%)" in commodity_data.columns:
        sort_cols.append("Contribution to USEEIO Sector's Scope 1 (%)"); sort_asc.append(False)
    if sort_cols:
        commodity_data = commodity_data.sort_values(by=sort_cols, ascending=sort_asc, na_position='last')

    print(f"[SUCCESS] Industry form: {len(enriched_data):,} records | Commodity form: {len(commodity_data):,} records")
    return commodity_data, enriched_data


def _finalize_and_export(enriched_data, commodity_data, fbs_parquet, fbs_filtered, config_dict):
    """Validate quality, sort, assign Row IDs, and save all outputs.

    This is the single consolidated point where F01000 (Used/Secondhand Goods)
    is excluded from enriched outputs. F01000 is a final demand sector that does
    not produce emissions and is excluded from all USEEIO modeling.

    Returns (enriched_data, commodity_data) after finalization.
    """
    print("\n--- Finalize and export ---")

    # Consolidated F01000 exclusion
    if 'USEEIO Sector Code' in enriched_data.columns:
        before = len(enriched_data)
        enriched_data = enriched_data[enriched_data['USEEIO Sector Code'] != 'F01000'].copy()
        removed = before - len(enriched_data)
        if removed > 0:
            print(f"  Excluded F01000 (Used/Secondhand Goods): {removed} rows removed from industry form")
    if commodity_data is not None and 'USEEIO Sector Code' in commodity_data.columns:
        commodity_data = commodity_data[commodity_data['USEEIO Sector Code'] != 'F01000'].copy()

    # Validate data quality
    print("  Validating data quality...")
    validate_data(enriched_data, config_dict["modelname"])

    # Reorder to KEEP_COLUMNS and sort: USEEIO → NAICS → Contribution% desc
    print("  Reordering columns and sorting...")
    final_columns = [col for col in config.KEEP_COLUMNS if col in enriched_data.columns]
    enriched_data = enriched_data[final_columns]

    sort_cols, sort_asc = [], []
    if "USEEIO Sector Code" in enriched_data.columns:
        sort_cols.append("USEEIO Sector Code"); sort_asc.append(True)
    if "NAICS Sector Code" in enriched_data.columns:
        sort_cols.append("NAICS Sector Code"); sort_asc.append(True)
    if "Contribution to USEEIO Sector's Scope 1 (%)" in enriched_data.columns:
        sort_cols.append("Contribution to USEEIO Sector's Scope 1 (%)"); sort_asc.append(False)
    if sort_cols:
        enriched_data = enriched_data.sort_values(by=sort_cols, ascending=sort_asc, na_position='last')
        print(f"  Sorted {len(enriched_data):,} records by: {' → '.join(sort_cols)}")

    # Add 1-based Row IDs (after sorting so IDs reflect final order)
    print("  Adding Row IDs...")
    enriched_data.insert(0, 'Row ID', range(1, len(enriched_data) + 1))
    if commodity_data is not None:
        commodity_data.insert(0, 'Row ID', range(1, len(commodity_data) + 1))

    # Optionally drop QC-only columns
    if config.EXCLUDE_QC_COLUMNS and config.QC_ONLY_COLUMNS:
        qc_to_remove = [col for col in config.QC_ONLY_COLUMNS if col in enriched_data.columns]
        if qc_to_remove:
            enriched_data = enriched_data.drop(columns=qc_to_remove)
    print(f"  [SUCCESS] Final output: {len(enriched_data):,} rows, {len(enriched_data.columns)} columns")

    # Filter baseline for export
    fbs_filtered_final = filter_columns(
        fbs_filtered, config.KEEP_COLUMNS,
        exclude_qc=config.EXCLUDE_QC_COLUMNS, qc_cols=config.QC_ONLY_COLUMNS
    )

    # Save outputs
    print("  Saving outputs...")
    save_outputs(fbs_parquet, fbs_filtered_final, enriched_data, config_dict, commodity_data=commodity_data)

    return enriched_data, commodity_data


def _generate_qcqa_workbook(commodity_data, output_dir):
    """Compare commodity-form intensity against the B matrix and write QC/QA workbook.

    Writes outputs/QCQA.xlsx with sheets:
      - Comparison: Full (USEEIO Code, Gas, Our Intensity, B Value, Abs Error, Rel Error)
      - Summary: Per-gas aggregate stats
      - Flagged: Pairs where relative error exceeds threshold
      - Contribution Check: Per commodity sector sum of Contribution %
    """
    b_matrix_path = os.path.join(parent_dir, 'data', 'B_matrix.csv')
    if not os.path.exists(b_matrix_path):
        print("  Skipping QC/QA — B_matrix.csv not found. Run the R export script first.")
        return

    if commodity_data is None or commodity_data.empty:
        print("  Skipping QC/QA — no commodity data available.")
        return

    from pipeline.loaders import load_b_matrix

    print("\n--- QC/QA: Comparing commodity intensity against B matrix ---")

    b_matrix = load_b_matrix(b_matrix_path)
    if b_matrix.empty:
        return

    emissions_intensity_col = get_emissions_intensity_col()
    rel_error_threshold = 0.001  # 0.1%

    # --- Build our intensity lookup: (flow_id, commodity_code) → intensity ---
    # B matrix rows are like "Carbon dioxide/emission/air" — we need to match our Gas column
    # Our commodity data has Gas column; B matrix row names are "Flowable/Context" identifiers
    # We'll aggregate our data to (Gas, USEEIO Sector Code) → sum of intensity
    our = (
        commodity_data
        .groupby(['Gas', 'USEEIO Sector Code'], dropna=False)
        .agg({emissions_intensity_col: 'sum'})
        .reset_index()
    )

    # Build comparison rows
    comparison_rows = []
    for _, row in our.iterrows():
        gas = row['Gas']
        sector = row['USEEIO Sector Code']
        our_val = row[emissions_intensity_col]

        if pd.isna(gas) or pd.isna(sector):
            continue

        # Find matching B matrix row(s) — B row names are "Flowable/context/..."
        # Use exact prefix match (gas + "/") to avoid substring collisions
        # e.g. "HFC-23/" must NOT match "HFC-236fa/emission/air/kg"
        gas_prefix = str(gas) + "/"
        matching_rows = b_matrix.index[b_matrix.index.str.startswith(gas_prefix)]
        if len(matching_rows) == 0:
            continue

        # Sum across all matching B rows for this gas and sector
        b_val = 0.0
        for b_row in matching_rows:
            if sector in b_matrix.columns:
                b_val += b_matrix.loc[b_row, sector]

        abs_error = abs(our_val - b_val)
        rel_error = abs_error / abs(b_val) if abs(b_val) > 1e-20 else float('nan')

        comparison_rows.append({
            'USEEIO Sector Code': sector,
            'Gas': gas,
            'Our Intensity': our_val,
            'B Matrix Value': b_val,
            'Abs Error': abs_error,
            'Rel Error': rel_error,
        })

    if not comparison_rows:
        print("  No matching (Gas, Sector) pairs found for comparison.")
        return

    comparison_df = pd.DataFrame(comparison_rows)

    # --- Summary sheet: per-gas stats ---
    summary_df = (
        comparison_df
        .groupby('Gas')
        .agg(
            Count=('Rel Error', 'size'),
            Max_Abs_Error=('Abs Error', 'max'),
            Mean_Rel_Error=('Rel Error', 'mean'),
            Max_Rel_Error=('Rel Error', 'max'),
        )
        .reset_index()
    )

    # --- Flagged sheet: pairs exceeding threshold ---
    flagged_df = comparison_df[comparison_df['Rel Error'] > rel_error_threshold].copy()

    # --- Contribution Check sheet ---
    contrib_col = "Contribution to USEEIO Sector's Scope 1 (%)"
    if contrib_col in commodity_data.columns:
        contrib_check = (
            commodity_data
            .groupby('USEEIO Sector Code', dropna=False)
            .agg({contrib_col: 'sum'})
            .reset_index()
            .rename(columns={contrib_col: 'Sum of Contribution %'})
        )
        contrib_check['Expected'] = 1.0
        contrib_check['Deviation'] = abs(contrib_check['Sum of Contribution %'] - 1.0)
    else:
        contrib_check = pd.DataFrame(columns=['USEEIO Sector Code', 'Sum of Contribution %', 'Expected', 'Deviation'])

    # --- Write workbook ---
    qcqa_path = os.path.join(output_dir, 'QCQA.xlsx')
    os.makedirs(output_dir, exist_ok=True)
    with pd.ExcelWriter(qcqa_path, engine='openpyxl') as writer:
        comparison_df.to_excel(writer, sheet_name='Comparison', index=False)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        flagged_df.to_excel(writer, sheet_name='Flagged', index=False)
        contrib_check.to_excel(writer, sheet_name='Contribution Check', index=False)

    print(f"[SUCCESS] QC/QA workbook written: {qcqa_path}")
    print(f"  Comparison: {len(comparison_df):,} (Gas, Sector) pairs")
    print(f"  Flagged: {len(flagged_df):,} pairs with rel error > {rel_error_threshold*100:.1f}%")
    if len(flagged_df) == 0:
        print("  All commodity intensities match B matrix within tolerance!")


def _print_enrichment_summary(enriched_data, commodity_data, config_dict):
    """Print the completion banner, enrichment dimension counts, and output file locations."""
    combination_cols = [
        'Activity Category', 'Activity Subcategory', 'Activity Type', 'Activity',
        'Gas Category', 'Gas', 'Fuel Consumed'
    ]

    # Completion banner
    print("=" * 80)
    print("PROCESSING COMPLETE!")
    print("=" * 80)
    print(f"[SUCCESS] Model processed: {config_dict['modelname']}")
    print(f"  Industry form: {len(enriched_data):,} records, {len(enriched_data.columns)} columns")
    if commodity_data is not None:
        print(f"  Commodity form: {len(commodity_data):,} records, {len(commodity_data.columns)} columns")

    # Enrichment dimension counts
    print("\n" + "=" * 80)
    print("ENRICHMENT SUMMARY - Unique Categories")
    print("=" * 80)

    # F01000 is already excluded from enriched_data, but guard defensively
    stats_df = (
        enriched_data[enriched_data['USEEIO Sector Code'] != 'F01000'].copy()
        if 'USEEIO Sector Code' in enriched_data.columns else enriched_data
    )

    print("\nIndustry Form:")
    print("-" * 40)
    print(f"  USEEIO Sectors:          {count_unique_valid(stats_df, 'USEEIO Sector Code'):,}")
    print(f"  NAICS Sectors:           {count_unique_valid(stats_df, 'NAICS Sector Code'):,}")
    print(f"\n  Activity Categories:     {count_unique_valid(stats_df, 'Activity Category'):,}")
    print(f"  Activity Subcategories:  {count_unique_valid(stats_df, 'Activity Subcategory'):,}")
    print(f"  Activity Types:          {count_unique_valid(stats_df, 'Activity Type'):,}")
    print(f"  Activities:              {count_unique_valid(stats_df, 'Activity'):,}")
    print(f"\n  Gas Categories:          {count_unique_valid(stats_df, 'Gas Category'):,}")
    print(f"  Gases:                   {count_unique_valid(stats_df, 'Gas'):,}")

    n = count_unique_valid(stats_df, 'Fuel Consumed')
    if n: print(f"\n  Fuel Types:              {n:,}")
    n = count_unique_valid(stats_df, 'IPCC/UNFCCC Category')
    if n: print(f"  IPCC Categories:         {n:,}")
    n = count_unique_valid(stats_df, 'US GHGI Table ID')
    if n: print(f"  EPA GHGI Tables:         {n:,}")

    if 'Emissions (MTCO2e)' in stats_df.columns:
        combo_df = stats_df[stats_df['Emissions (MTCO2e)'].notna() & (stats_df['Emissions (MTCO2e)'] != 0)]
        print(f"\n  Unique Combinations (Activity + Gas + Fuel): {len(combo_df[combination_cols].drop_duplicates()):,}")

    if commodity_data is not None:
        print("\n" + "-" * 40)
        print("Commodity Form:")
        print("-" * 40)
        for label, col in [
            ("USEEIO Sectors",          "USEEIO Sector Code"),
            ("Activity Categories",     "Activity Category"),
            ("Activity Subcategories",  "Activity Subcategory"),
            ("Activity Types",          "Activity Type"),
            ("Activities",              "Activity"),
            ("Gas Categories",          "Gas Category"),
            ("Gases",                   "Gas"),
            ("Fuel Types",              "Fuel Consumed"),
        ]:
            n = count_unique_valid(commodity_data, col)
            if n: print(f"  {label + ':':<25} {n:,}")

        if 'Emissions (MTCO2e)' in commodity_data.columns:
            comm_combo_df = commodity_data[
                commodity_data['Emissions (MTCO2e)'].notna() & (commodity_data['Emissions (MTCO2e)'] != 0)
            ]
            print(f"\n  Unique Combinations (Activity + Gas + Fuel): {len(comm_combo_df[combination_cols].drop_duplicates()):,}")

    print("=" * 80)

    # Output file locations
    print("\nSUCCESS! Your GHG emission factors are ready!")
    print("Check these output files:")
    industry_dir = os.path.join(config.OUTPUT_DIR, config.INDUSTRY_OUTPUT_SUBDIR)
    industry_basename = config.MODELNAME + "_industry"
    output_files = [
        (f"{config.OUTPUT_DIR}/metadata/EPA_GHGI_meta_sources.csv", "EPA GHGI metadata"),
        (f"{industry_dir}/{industry_basename}.xlsx",    "*** FINAL ENRICHED DATA (Excel) ***"),
        (f"{industry_dir}/{industry_basename}.parquet", "Final data (Parquet)"),
        (f"{industry_dir}/{industry_basename}.jsonld",  "Emission events (JSON-LD)"),
    ]
    for file_path, description in output_files:
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            print(f"  [OK] {file_path}")
            print(f"       {description} ({file_size:.1f} MB)")
        else:
            print(f"  [MISSING] {file_path}")

    print(f"\nNext steps:")
    print(f"  1. Review output files in '{config_dict['output_dir']}/'")
    print("  2. Use industry form for direct emission analysis by producing sector")
    if commodity_data is not None:
        print("  3. Use commodity form for USEEIO supply chain analysis (emissions by product)")
    else:
        print("  3. Run 'Rscript scripts/setup/export_reference_data.R' to enable commodity form")
    print("  4. Check data quality validation results above")
    print("\nFor questions or issues, refer to the project documentation.")
    print("=" * 80)


def run_data_enrichment(fbs_data):
    """
    Orchestrate the full FlowBySector enrichment and export workflow.

    Steps:
    1. Validate FlowSA version and build config dict
    2. Load or download baseline parquet (for sanity check and baseline export)
    3. Verify and sanity-check provided FBS data against baseline
    4. Load all reference inputs (lookups, crosswalks, YAML)
    5. Run enrichment pipeline (metadata → USEEIO → fuel → GHG → GWP → contribution)
    6. Transform to commodity form (industry output × V_n market-share matrix)
    7. Finalize: validate, sort, assign row IDs, export
    8. Print summary
    """
    print("\nStep 3: Enriching FlowBySector data with metadata...")
    print("=" * 80)
    print("FlowSA GHG SOURCES EXTRACTION - DATA ENRICHMENT")
    print("=" * 80)
    print(f"Processing model: {config.MODELNAME}")
    print(f"Model year:       {config.MODEL_YEAR}")
    print(f"Description:      {config.MODEL_DESCRIPTION}")
    print("=" * 80)

    # Step 1: Validate FlowSA version and build config dict
    validate_flowsa_version()
    config_dict = {
        "input_path": config.FLOWSA_DATA_PATH,
        "subfolder": config.FLOWBYSECTOR_SUBFOLDER,
        "file_name_parquet": config.FILE_NAME_PARQUET,
        "modelname": config.MODELNAME,
        "output_dir": config.OUTPUT_DIR,
    }
    os.makedirs(config_dict["output_dir"], exist_ok=True)

    # Step 2: Load baseline parquet (reference FBS without activity columns)
    fbs_parquet = None
    parquet_path = os.path.join(
        config_dict["input_path"], config_dict["subfolder"], config_dict["file_name_parquet"]
    )
    print(f"\nStep 2: Checking for baseline parquet data...")
    print(f"  Path:        {parquet_path}")
    print(f"  File exists: {os.path.exists(parquet_path)}")

    if os.path.exists(parquet_path):
        fbs_parquet = load_parquet_data(
            config_dict["input_path"], config_dict["subfolder"], config_dict["file_name_parquet"]
        )
    else:
        print(f"\n  WARNING: Baseline file missing ({config_dict['file_name_parquet']})")
        print("  Needed for: sanity check comparison, baseline export tab in Excel")
        try:
            user_input = input("\nDownload baseline from FlowSA? (yes/no) [default: no]: ").strip().lower() or 'no'
        except EOFError:
            user_input = 'no'
            print("  Non-interactive mode: defaulting to 'no'")
        if user_input in ['yes', 'y']:
            try:
                fbs_parquet = flowsa.getFlowBySector(config_dict['modelname'])
                print(f"  [SUCCESS] Downloaded {len(fbs_parquet):,} records")
                fbs_folder = os.path.join(config_dict["input_path"], config_dict["subfolder"])
                os.makedirs(fbs_folder, exist_ok=True)
                fbs_parquet.to_parquet(parquet_path, engine='pyarrow', compression='snappy')
                fbs_parquet.Location = fbs_parquet.Location.apply('="{}"'.format)
            except Exception as e:
                print(f"  Warning: Download failed ({e}) — continuing without baseline")
                fbs_parquet = None
        else:
            print("  Continuing without baseline (sanity check and baseline export skipped)")

    # Remove F01000 from baseline (not a producing sector)
    if fbs_parquet is not None and 'SectorProducedBy' in fbs_parquet.columns:
        before = len(fbs_parquet)
        fbs_parquet = fbs_parquet[fbs_parquet['SectorProducedBy'] != 'F01000'].copy()
        removed = before - len(fbs_parquet)
        if removed > 0:
            print(f"  Excluded F01000 from baseline: {removed} rows removed")

    # Step 3: Verify input and prepare working copy
    if fbs_data is None:
        raise ValueError("FlowBySector data must be provided. Run run_fbs_generation() first.")
    print(f"\nStep 3: FlowBySector input: {len(fbs_data):,} records")
    fbs_filtered = fbs_data.copy()

    # Sanity check against baseline
    if fbs_parquet is not None:
        print("  Running sanity check against baseline parquet...")
        fbs_agg = aggregate_to_reference_format(fbs_filtered)
        comparison = compare_with_reference(fbs_agg, fbs_parquet)
        if not (comparison["row_count_match"] and comparison["data_match"]):
            print("  WARNING: Sanity check detected differences!")
            if config.STRICT_VERSION_CHECK:
                try:
                    user_input = input("\nContinue anyway? (yes/no) [default: yes]: ").strip().lower() or 'yes'
                except EOFError:
                    user_input = 'yes'
                    print("  Non-interactive mode: defaulting to 'yes'")
                if user_input not in ['yes', 'y']:
                    print("Aborted by user.")
                    return False

    # Step 4: Load all reference inputs
    print("\nStep 4: Loading reference inputs...")
    inputs = _load_pipeline_inputs(config_dict)

    # Step 5: Run enrichment pipeline
    print("\nStep 5: Running enrichment pipeline...")
    enriched_data = _run_enrichment_pipeline(fbs_filtered, inputs)

    # Step 6: Industry-to-commodity transformation
    print("\nStep 6: Running industry-to-commodity transformation...")
    commodity_data, enriched_data = _run_commodity_transformation(enriched_data, inputs)

    # Step 6b: QC/QA — compare commodity intensities against B matrix
    if commodity_data is not None:
        _generate_qcqa_workbook(commodity_data, config.OUTPUT_DIR)

    # Step 7: Validate, sort, add Row IDs, export
    print("\nStep 7: Finalizing and exporting...")
    enriched_data, commodity_data = _finalize_and_export(
        enriched_data, commodity_data, fbs_parquet, fbs_filtered, config_dict
    )

    # Step 8: Print summary
    _print_enrichment_summary(enriched_data, commodity_data, config_dict)

    return True


def main():
    """Main function to run the complete workflow."""
    parser = argparse.ArgumentParser(
        description="FlowSA GHG Sources Extraction - Simple Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_ghg_dataset.py                     # Run with prompts (recommended)
  python generate_ghg_dataset.py --skip-metadata     # Skip metadata extraction
  python generate_ghg_dataset.py --skip-fbs-generation    # Use cached FBS data
  python generate_ghg_dataset.py --force-fbs-generation   # Generate new FBS without prompt
  python generate_ghg_dataset.py --check-only        # Just check requirements

To switch models/years, edit MODELNAME in config.py
        """
    )
    
    parser.add_argument(
        "--skip-metadata", 
        action="store_true",
        help="Skip EPA GHGI metadata extraction (if already done)"
    )
    parser.add_argument(
        "--skip-fbs-generation",
        action="store_true",
        help="Skip FBS generation, use cached data (if available)"
    )
    parser.add_argument(
        "--force-fbs-generation",
        action="store_true",
        help="Force new FBS generation without prompting"
    )
    parser.add_argument(
        "--check-only", 
        action="store_true",
        help="Only check requirements, don't run extraction"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check requirements first
    if not check_requirements():
        return 1
    
    if args.check_only:
        print("SUCCESS: Requirements check complete. Ready to run extraction!")
        return 0
    
    # Load and show current config
    try:
        import config
        print(f"\nCurrent configuration:")
        print(f"   Model: {config.MODELNAME}")
        print(f"   Year: {config.MODEL_YEAR}")
        print(f"   Description: {config.MODEL_DESCRIPTION}")
    except Exception as e:
        print(f"ERROR: Error loading config: {e}")
        return 1
    
    # Run the workflow
    success = True
    
    # Step 1: Extract metadata (unless skipped)
    if not args.skip_metadata:
        success &= run_metadata_extraction()
    else:
        print("\nStep 1: Skipping metadata extraction (--skip-metadata)")
        
        # Check if metadata file exists
        metadata_path = os.path.join(config.OUTPUT_DIR, "metadata", config.EPA_GHGI_META_CSV)
        if not os.path.exists(metadata_path):
            print(f"WARNING: Metadata file not found at {metadata_path}")
            print("   Consider running without --skip-metadata flag")
    
    # Step 2: Generate FlowBySector data
    fbs_data = None
    if success:
        fbs_data = run_fbs_generation(
            skip_generation=args.skip_fbs_generation,
            force_generation=args.force_fbs_generation
        )
        success = fbs_data is not None
    
    # Step 3: Enrich data with metadata
    if success and fbs_data is not None:
        success &= run_data_enrichment(fbs_data)

    if success:
        print("\nCOMPLETE! Happy analyzing!")
        return 0
    else:
        print("\nERROR: Extraction failed. Check error messages above.")
        print("TROUBLESHOOTING TIPS:")
        print("   - Ensure FlowSA is properly installed")
        print("   - Check that you have internet connection for data downloads")
        print("   - Verify your model name in config.py")
        return 1


if __name__ == "__main__":
    exit(main())
