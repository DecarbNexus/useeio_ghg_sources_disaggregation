"""
Configuration file for FlowSA GHG Sources Extraction

This file contains all the configurable parameters for the GHG sources extraction pipeline.
Modify the values here to customize the analysis for different models or years.
"""

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# ── Set this ONE value to switch Supply Chain Emission Factor releases ────────
SEF_VERSION = "v1.4.0"  # Options: "v1.3.0", "v1.4.0"
# ─────────────────────────────────────────────────────────────────────────────

# Version specs lookup — add a new entry here when a new SEF release is published.
# Keep in sync with the SEF_SPECS list in scripts/setup/export_reference_data.R.
_SEF_SPECS = {
    "v1.3.0": dict(
        github_org      = "cornerstone-data",
        useeior_tag     = "v1.5.3",
        useeior_ver     = "1.5.3",
        model_spec_name = "USEEIOv2.2.22-GHG",
        model_year      = 2022,
        flowsa_tag      = "v2.0.3",
        flowsa_ver      = "2.0.3",
        flowsa_hash     = "1cb504c",
        parquet_file    = "GHG_national_2022_m2_v2.0.3_1cb504c.parquet",
        modelname       = "GHG_national_2022_m2",
        model_desc      = "2022 GHG National Model - Method 2",
    ),
    "v1.4.0": dict(
        github_org      = "cornerstone-data",
        useeior_tag     = "SEFv1.4",
        useeior_ver     = "1.8.0",
        model_spec_name = "USEEIOv2.6.0-phoebe-23",
        model_year      = 2023,
        flowsa_tag      = "v2.1.0",
        flowsa_ver      = "2.1.0",
        flowsa_hash     = "c25c206",
        parquet_file    = "GHG_national_2023_m2_v2.1.0_c25c206.parquet",
        modelname       = "GHG_national_2023_m2",
        model_desc      = "2023 GHG National Model - Method 2",
    ),
}

if SEF_VERSION not in _SEF_SPECS:
    raise ValueError(
        f"SEF_VERSION {SEF_VERSION!r} is not defined. "
        f"Known versions: {list(_SEF_SPECS)}"
    )
_s = _SEF_SPECS[SEF_VERSION]

# All constants below are auto-derived — change SEF_VERSION above, not these.
GITHUB_ORG           = _s["github_org"]
MODELNAME            = _s["modelname"]
FILE_NAME_PARQUET    = _s["parquet_file"]
MODEL_DESCRIPTION    = _s["model_desc"]
MODEL_YEAR           = _s["model_year"]
USEEIOR_TAG          = _s["useeior_tag"]
USEEIOR_VER          = _s["useeior_ver"]
MODEL_SPEC_NAME      = _s["model_spec_name"]

# =============================================================================
# FLOWSA VERSION REQUIREMENTS
# =============================================================================

REQUIRED_FLOWSA_VERSION  = _s["flowsa_ver"]
REQUIRED_FLOWSA_GIT_TAG  = _s["flowsa_tag"]   # GitHub release tag
REQUIRED_FLOWSA_GIT_HASH = _s["flowsa_hash"]  # For reference

# Whether to enforce strict version checking
STRICT_VERSION_CHECK = True

# =============================================================================
# FILE PATHS
# =============================================================================

# Path to FlowSA data directory (where parquet files are stored)
from appdirs import user_data_dir as _user_data_dir
FLOWSA_DATA_PATH = _user_data_dir("flowsa")

# Subfolder containing FlowBySector files
FLOWBYSECTOR_SUBFOLDER = "FlowBySector"

# Output directory for results — version-stamped so runs for different SEF
# versions land in outputs/SEF_v1.3.0/, outputs/SEF_v1.4.0/, etc.
OUTPUT_DIR = f"outputs/SEF_{SEF_VERSION}"

# EPA GHGI metadata file names
EPA_GHGI_META_CSV = "EPA_GHGI_meta_sources.csv"
EPA_GHGI_META_YAML = "EPA_GHGI_meta_sources.yaml"

# Fuel lookup files
FUEL_BY_TERM_CSV = "data/ListOfFuelsByTerm.csv"

# Activity sets lookup file
ACTIVITY_SETS_CSV = "data/ListOfActivitySets.csv"

# R-generated data files — stored in a version-stamped subfolder so multiple
# SEF versions can coexist without overwriting each other.
# Written by scripts/setup/export_reference_data.R
_r_data = f"data/SEF_{SEF_VERSION}"
NAICS_BEA_ALLOCATION_CSV      = f"{_r_data}/naics_bea_allocation.csv"
ADJUSTED_OUTPUT_CSV           = f"{_r_data}/cpi_adjusted_industry_output.csv"
ADJUSTED_COMMODITY_OUTPUT_CSV = f"{_r_data}/cpi_adjusted_commodity_output.csv"
B_MATRIX_CSV                  = f"{_r_data}/B_matrix.csv"
V_N_CSV                       = f"{_r_data}/V_n.csv"
NAICS_TO_USEEIO_CSV           = f"{_r_data}/naics_to_useeio_crosswalk.csv"
SECTOR_CLASSIFICATION_CSV     = f"{_r_data}/sector_classification.csv"
FUEL_BY_TABLE_CSV             = f"{_r_data}/ListOfFuelsByMetaSource.csv"

# Comprehensive activity categorization file (includes IPCC category, Activity Category, Subcategory, Type)
METASOURCE_TO_GHGSOURCE_CSV   = f"{_r_data}/activity_categorization.csv"

# Flowable categorization file
FLOWABLE_CATEGORIZATION_CSV = "data/flowable_categorization.csv"

# IPCC AR5-100 GWP factors file
IPCC_AR5_100_PARQUET = "data/IPCC_v1.1.1_27ba917.parquet"

# IPCC GWP parameters
IPCC_INDICATOR = "AR5-100"  # Options: AR4-100, AR4-20, AR4-500, AR5-100, AR5-20, AR6-100, AR6-20, AR6-500
IPCC_CONTEXT = "emission/air"  # Context for GWP lookup

# =============================================================================
# FLOWSA PROCESSING OPTIONS
# =============================================================================

# Note: FlowBySector generation parameters are now constants in the code:
#   - download_sources_ok=True (always download FlowByActivity data)
#   - retain_activity_columns=True (preserve activity details for enrichment)
#   - append_sector_names=False (we add USEEIO names during enrichment)

# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================

def _build_keep_columns(year):
    """Build the ordered list of output columns, with the year-tagged intensity column."""
    return [
        # Unique identifier
        "Row ID",                                      # Unique identifier for each row (1-based)
        "GHG Source ID",                               # Stable 8-char hash key linking to ghg_source_classification table

        # Primary identification columns
        "USEEIO Sector Name",                          # Human-readable sector name
        "USEEIO Sector Code",                          # USEEIO sector code from NAICS crosswalk
        "NAICS Sector Code",                           # Economic sector code producing the emissions

        # Category columns
        "Activity Category",                           # Enriched: Activity category from MetaSource mapping
        "IPCC/UNFCCC Category",                        # Enriched: IPCC/UNFCCC category from MetaSource mapping
        "IPCC Category Code",                            # Enriched: IPCC alphanumeric category code (e.g. 1A1, 2B3)
        "Activity Subcategory",                        # Enriched: subcategory from EPA GHGI metadata
        "Activity Type",                               # Enriched: activity type from categorization mapping
        "Activity",                                    # Enriched: specific activity/source from YAML or ActivityProducedBy
        "Fuel",                                        # Enriched: fuel type extracted from PrimaryActivity

        # Gas identification
        "Gas Category",                                # Enriched: gas category from flowable categorization
        "Gas",                                         # The greenhouse gas species (CO2, CH4, N2O, etc.)

        # Emissions data
        "Emissions (kg)",                              # Emissions in kg (when Unit != "kg CO2e")
        f"Emissions Intensity (kg/USD_{year})",        # Enriched: Emissions per dollar of sector output (kg/$)
        "AR5-100 GWP",                                 # Enriched: IPCC AR5 100-year Global Warming Potential
        "Emissions (kgCO2e)",                          # Emissions in kg CO2e (when Unit == "kg CO2e" or kg × GWP)
        f"Emissions Intensity (kgCO2e/USD_{year})",    # Enriched: kgCO2e per dollar of sector output
        f"Emissions Intensity (MTCO2e/million_USD_{year})",  # Enriched: MTCO2e per million USD of sector output
        "Emissions (MTCO2e)",                          # Enriched: Emissions in metric tons CO2 equivalent
        "Contribution to USEEIO Sector's Scope 1 (%)", # Enriched: Percentage contribution to USEEIO sector total

        # Source metadata
        "US GHGI Chapter",                             # EPA GHGI chapter
        "US GHGI Table ID",                            # EPA GHGI table ID
        "US GHGI Table Name",                          # EPA GHGI table description
        "Attribution Sources",                         # Data sources used for sector attribution

        # Quality control columns (optionally excluded based on EXCLUDE_QC_COLUMNS flag)
        "MetaSources",                                 # EPA GHGI table sources
        "ActivityProducedBy",                          # Specific activity generating emissions
        "FlowUUID",                                    # Unique identifier for the flow (for IPCC GWP lookups)
        "FlowAmount",                                  # Raw emission amount (kg or kg CO2e per dollar)
        "FlowAmount Unit",                             # Unit of measurement for FlowAmount
    ]


# Columns to keep in the final output (in order of preference)
KEEP_COLUMNS = _build_keep_columns(MODEL_YEAR)

# Columns to exclude from final analysis (useful for quality checks but not needed in final output)
# Set EXCLUDE_QC_COLUMNS = True to remove these columns from the final output
EXCLUDE_QC_COLUMNS = False  # Set to True to exclude quality control columns

QC_ONLY_COLUMNS = [
    "MetaSources",           # EPA GHGI source references - metadata added via enrichment
    "ActivityProducedBy",    # Activity code - replaced by Activity and Activity Set
    "FlowUUID",              # Used for GWP lookup - not needed after enrichment
    "FlowAmount",            # Raw flow amount - replaced by Emissions columns
    "FlowAmount Unit",       # Unit of raw flow - not needed after conversion to MTCO2e
]

# USEEIO sector codes excluded from all outputs and QCQA.
# These are bookkeeping sectors that do not represent real production activity:
#   F01000 — Used/Secondhand Goods (final demand, no direct emissions)
#   S00401 — Scrap (residual/waste bookkeeping sector)
#   S00900 — Rest of the world adjustment (trade balance adjustment sector)
EXCLUDED_SECTOR_CODES = ['F01000', 'S00401', 'S00900']

# Output export toggles
EXPORT_INDUSTRY = True   # Export industry/sector-based outputs to outputs/industry/
EXPORT_COMMODITY = True  # Export commodity-based outputs to outputs/commodity/ (future feature)

# Quality control output options
INCLUDE_BASELINE_TAB = True  # Include original FlowBySector data as "Baseline" tab in Excel
EXPORT_BASELINE_CSV = False  # Export baseline as separate CSV (requires INCLUDE_BASELINE_TAB=True)

# =============================================================================
# OUTPUT FORMAT OPTIONS
# =============================================================================

# Output subdirectories for different perspectives
INDUSTRY_OUTPUT_SUBDIR = "industry"    # Sector/industry-based perspective
COMMODITY_OUTPUT_SUBDIR = "commodity"  # Commodity-based perspective (future)

# Note: To switch models/years, edit MODELNAME and FILE_NAME_PARQUET at top of this file

# =============================================================================
# VALIDATION SETTINGS
# =============================================================================

# Whether to perform data validation
ENABLE_VALIDATION = True

# Minimum flow amount to consider valid (very small positive number)
MIN_FLOW_AMOUNT = 1e-12

# Whether to flag negative flow amounts as potential errors
FLAG_NEGATIVE_FLOWS = True

# Whether to create detailed logging
VERBOSE_LOGGING = True

# =============================================================================
# VERSION SWITCHING (CLI override)
# =============================================================================

def apply_version(ver):
    """Re-derive all version-dependent constants for a different SEF version.

    Call this in main() when --sef-version overrides config.SEF_VERSION.
    All pipeline functions read config.X at call time, so the update is
    immediately visible to everything that runs after this call.

    Example:
        import config
        config.apply_version("v1.4.0")  # override before pipeline starts
    """
    if ver not in _SEF_SPECS:
        raise ValueError(
            f"SEF version {ver!r} is not defined. "
            f"Known versions: {list(_SEF_SPECS)}"
        )
    import sys
    s  = _SEF_SPECS[ver]
    m  = sys.modules[__name__]
    _r = f"data/SEF_{ver}"
    m.SEF_VERSION                   = ver
    m.GITHUB_ORG                    = s["github_org"]
    m.MODELNAME                     = s["modelname"]
    m.FILE_NAME_PARQUET             = s["parquet_file"]
    m.MODEL_DESCRIPTION             = s["model_desc"]
    m.MODEL_YEAR                    = s["model_year"]
    m.USEEIOR_TAG                   = s["useeior_tag"]
    m.USEEIOR_VER                   = s["useeior_ver"]
    m.MODEL_SPEC_NAME               = s["model_spec_name"]
    m.REQUIRED_FLOWSA_VERSION       = s["flowsa_ver"]
    m.REQUIRED_FLOWSA_GIT_TAG       = s["flowsa_tag"]
    m.REQUIRED_FLOWSA_GIT_HASH      = s["flowsa_hash"]
    m.OUTPUT_DIR                    = f"outputs/SEF_{ver}"
    m.NAICS_BEA_ALLOCATION_CSV      = f"{_r}/naics_bea_allocation.csv"
    m.ADJUSTED_OUTPUT_CSV           = f"{_r}/cpi_adjusted_industry_output.csv"
    m.ADJUSTED_COMMODITY_OUTPUT_CSV = f"{_r}/cpi_adjusted_commodity_output.csv"
    m.B_MATRIX_CSV                  = f"{_r}/B_matrix.csv"
    m.V_N_CSV                       = f"{_r}/V_n.csv"
    m.NAICS_TO_USEEIO_CSV           = f"{_r}/naics_to_useeio_crosswalk.csv"
    m.SECTOR_CLASSIFICATION_CSV     = f"{_r}/sector_classification.csv"
    m.FUEL_BY_TABLE_CSV             = f"{_r}/ListOfFuelsByMetaSource.csv"
    m.METASOURCE_TO_GHGSOURCE_CSV   = f"{_r}/activity_categorization.csv"
    m.KEEP_COLUMNS                  = _build_keep_columns(s["model_year"])