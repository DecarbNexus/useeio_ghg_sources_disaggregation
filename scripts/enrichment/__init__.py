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

# Make key functions available at package level
# NOTE: Only importing functions that have been migrated to modules
# Other functions remain in enrich_fbs_with_meta.py for now (incremental migration)

from .loaders import (
    load_parquet_data,
    load_metadata_mapping,
    load_fuel_lookup,
    # TODO: Add more as they are migrated:
    # load_naics_to_useeio_crosswalk,
    # load_metasource_to_ghgsource_mapping,
    # load_flowable_categorization,
    # load_ipcc_ar5_100_gwp,
    # load_sector_classification,
    # load_method_yaml,
    # load_industry_output,
    # load_market_share_matrix,
)

from .enrichers import (
    enrich_with_metadata,
    enrich_with_fuel,
    enrich_with_useeio,
    enrich_with_primary_activities,
    # TODO: Add more as they are migrated:
    # enrich_with_useeio_sector_name,
    # enrich_with_ghg_source_categories,
    # enrich_with_gas_category,
    # enrich_with_ar5_100_gwp,
    # calculate_contribution_by_sector,
    # rename_and_create_columns,
    # normalize_emissions_by_output,
    # transform_to_commodity_form,
)

from .exporters import (
    save_outputs,
    build_emission_events_jsonld,
    build_d3_sunburst_hierarchy,
    # TODO: Add more as they are migrated:
    # build_ghg_source_classification_jsonld,
)

from .validators import (
    compare_with_reference,
    validate_data,
    aggregate_to_reference_format,
)

from .utils import (
    check_flowsa_version,
    validate_flowsa_version,
    get_emissions_intensity_col,
    filter_columns,
)

__all__ = [
    # Loaders (migrated)
    'load_parquet_data',
    'load_metadata_mapping',
    'load_fuel_lookup',
    
    # Enrichers (migrated)
    'enrich_with_metadata',
    'enrich_with_fuel',
    'enrich_with_useeio',
    'enrich_with_primary_activities',
    
    # Exporters (migrated)
    'save_outputs',
    'build_emission_events_jsonld',
    'build_d3_sunburst_hierarchy',
    
    # Validators (migrated)
    'compare_with_reference',
    'validate_data',
    'aggregate_to_reference_format',
    
    # Utils (migrated)
    'check_flowsa_version',
    'validate_flowsa_version',
    'get_emissions_intensity_col',
    'filter_columns',
]

# TODO: Add to __all__ as functions are migrated:
# Loaders: load_naics_to_useeio_crosswalk, load_metasource_to_ghgsource_mapping,
#          load_flowable_categorization, load_ipcc_ar5_100_gwp, load_sector_classification,
#          load_method_yaml, load_industry_output, load_market_share_matrix
# Enrichers: enrich_with_useeio_sector_name, enrich_with_ghg_source_categories,
#           enrich_with_gas_category, enrich_with_ar5_100_gwp, calculate_contribution_by_sector,
#           rename_and_create_columns, normalize_emissions_by_output, transform_to_commodity_form
# Exporters: build_ghg_source_classification_jsonld

