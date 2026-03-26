"""
Configuration file for FlowSA GHG Sources Extraction

This file contains all the configurable parameters for the GHG sources extraction pipeline.
Modify the values here to customize the analysis for different models or years.
"""

# =============================================================================
# MODEL CONFIGURATION
# =============================================================================

# Primary model to process
MODELNAME = "GHG_national_2022_m2"

# Corresponding parquet file name (should match the model)
FILE_NAME_PARQUET = "GHG_national_2022_m2_v2.0.3_1cb504c.parquet"

# Model description (for documentation)
MODEL_DESCRIPTION = "2022 GHG National Model - Method 2"

# Model year
MODEL_YEAR = 2022

# =============================================================================
# FLOWSA VERSION REQUIREMENTS
# =============================================================================

# Required FlowSA version (to match reference parquet generation)
# This ensures reproducibility and consistency with baseline data
# Installing from GitHub release tag v2.0.3
REQUIRED_FLOWSA_VERSION = "2.0.3"
REQUIRED_FLOWSA_GIT_TAG = "v2.0.3"  # GitHub release tag
REQUIRED_FLOWSA_GIT_HASH = "1cb504c"  # For reference

# Whether to enforce strict version checking
STRICT_VERSION_CHECK = True

# =============================================================================
# FILE PATHS
# =============================================================================

# Path to FlowSA data directory (where parquet files are stored)
FLOWSA_DATA_PATH = r"C:\Users\DamienLieber\AppData\Local\flowsa"

# Subfolder containing FlowBySector files
FLOWBYSECTOR_SUBFOLDER = "FlowBySector"

# Output directory for results
OUTPUT_DIR = "outputs"

# EPA GHGI metadata file names
EPA_GHGI_META_CSV = "EPA_GHGI_meta_sources.csv"
EPA_GHGI_META_YAML = "EPA_GHGI_meta_sources.yaml"

# Fuel lookup files
FUEL_BY_TABLE_CSV = "data/ListOfFuelsByTable.csv"
FUEL_BY_TERM_CSV = "data/ListOfFuelsByTerm.csv"

# Activity sets lookup file
ACTIVITY_SETS_CSV = "data/ListOfActivitySets.csv"

# NAICS to USEEIO Crosswalk file
NAICS_TO_USEEIO_CSV = "data/NAICS_to_USEEIO_crosswalk.csv"

# Comprehensive activity categorization file (includes IPCC category, Activity Category, Subcategory, Type)
METASOURCE_TO_GHGSOURCE_CSV = "data/activity_categorization.csv"

# Flowable categorization file
FLOWABLE_CATEGORIZATION_CSV = "data/flowable_categorization.csv"

# IPCC AR5-100 GWP factors file
IPCC_AR5_100_PARQUET = "data/IPCC_v1.1.1_27ba917.parquet"

# USEEIO Sector classification file
SECTOR_CLASSIFICATION_CSV = "data/sector_classification.csv"

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

# Columns to keep in the final output (in order of preference)
KEEP_COLUMNS = [
    # Unique identifier
    "Row ID",                                      # Unique identifier for each row (1-based)
    
    # Primary identification columns
    "USEEIO Sector Name",                          # Human-readable sector name
    "USEEIO Sector Code",                          # USEEIO sector code from NAICS crosswalk
    "NAICS Sector Code",                           # Economic sector code producing the emissions
    
    # Category columns
    "Activity Category",                           # Enriched: Activity category from MetaSource mapping
    "IPCC/UNFCCC Category",                        # Enriched: IPCC/UNFCCC category from MetaSource mapping
    "Activity Subcategory",                        # Enriched: subcategory from EPA GHGI metadata
    "Activity Type",                               # Enriched: activity type from categorization mapping
    "Activity",                                    # Enriched: specific activity/source from YAML or ActivityProducedBy
    "Fuel Consumed",                               # Enriched: fuel type extracted from PrimaryActivity
    
    # Gas identification
    "Gas Category",                                # Enriched: gas category from flowable categorization
    "Gas",                                         # The greenhouse gas species (CO2, CH4, N2O, etc.)
    
    # Emissions data
    "Emissions (kg)",                              # Emissions in kg (when Unit != "kg CO2e")
    f"Emissions Intensity (kg/USD_{MODEL_YEAR})",  # Enriched: Emissions per dollar of sector output (kg/$)
    "AR5-100 GWP",                                 # Enriched: IPCC AR5 100-year Global Warming Potential
    "Emissions (kgCO2e)",                          # Emissions in kg CO2e (when Unit == "kg CO2e")
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