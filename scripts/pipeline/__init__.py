"""
FlowSA GHG Sources Enrichment Package

This package contains modular components for enriching FlowBySector data
with EPA GHGI metadata and calculating greenhouse gas emissions.

Modules:
--------
- loaders: Load all external data sources (parquet, CSV, YAML)
- enrichers: Apply enrichments (fuel, sector, activity, GWP, metadata)
- exporters: Export enriched data in multiple formats (Excel, CSV, Parquet, JSON-LD)
- validators: Validate data quality and compare with reference data
- utils: Shared utility functions

Design Philosophy:
------------------
- loaders: Pure I/O, no business logic
- enrichers: Core transformations, return new DataFrames (immutable)
- exporters: Output formatting, independent of enrichment logic
- validators: Data quality checks, separate from main workflow
- utils: Shared helpers used across modules

Usage:
------
from enrichment import loaders, enrichers, exporters

# Load data
metadata = loaders.load_metadata_mapping("path/to/meta.csv")

# Enrich
enriched = enrichers.enrich_with_metadata(df, metadata)

# Export
exporters.save_all_formats(enriched, config)
"""

__version__ = "1.0.0"

from .loaders import (
    load_parquet_data,
    load_generated_fbs_data,
    load_metadata_mapping,
    load_fuel_lookup,
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

from .enrichers import (
    enrich_with_metadata,
    enrich_with_fuel,
    enrich_with_useeio,
    enrich_with_useeio_sector_name,
    enrich_with_primary_activities,
    enrich_with_activity_sets,
    enrich_with_ghg_source_categories,
    enrich_with_gas_category,
    enrich_with_ar5_100_gwp,
)

from .exporters import (
    save_outputs,
    build_hierarchical_jsonld,
    build_ghg_source_classification_jsonld,
    build_ghg_source_classification_csv,
    build_emission_events_jsonld,
    build_d3_sunburst_hierarchy,
    export_event_based_outputs,
)

from .validators import (
    aggregate_to_reference_format,
    compare_with_reference,
    validate_data,
)

from .utils import (
    get_emissions_intensity_col,
    check_flowsa_version,
    validate_flowsa_version,
    filter_columns,
    rename_and_create_columns,
    generate_event_id,
    build_emission_event_full,
    _extract_meta_id,
    _deduplicate_and_simplify_activities,
    _parse_primary_activity_value,
)

from .transform import (
    calculate_contribution_by_sector,
    normalize_emissions_by_output,
    transform_to_commodity_form,
)



