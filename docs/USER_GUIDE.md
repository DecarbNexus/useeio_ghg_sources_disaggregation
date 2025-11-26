# FlowSA GHG Sources Extraction - User Guide

**A comprehensive tool for enriching EPA greenhouse gas emission data with supply chain metadata**

---

## 📚 Table of Contents

- [Overview](#overview)
- [For Non-Coders](#for-non-coders)
  - [What Does This Tool Do?](#what-does-this-tool-do)
  - [Quick Start](#quick-start)
  - [Understanding the Output](#understanding-the-output)
- [For Coders](#for-coders)
  - [Installation](#installation)
  - [Architecture Overview](#architecture-overview)
  - [Configuration](#configuration)
  - [Running the Pipeline](#running-the-pipeline)
- [Data Enrichment Layers](#data-enrichment-layers)
- [Configuration Reference](#configuration-reference)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

This tool processes EPA greenhouse gas (GHG) emission data from the FlowSA library and enriches it with detailed metadata to create comprehensive supply chain emission factors. The enriched data can be used with USEEIO (U.S. Environmentally-Extended Input-Output) models for supply chain analysis.

**Key Features:**
- ✅ Enriches GHG data with 11 layers of metadata
- ✅ Converts emissions to CO2 equivalents using IPCC AR5-100 global warming potentials
- ✅ Maps emissions to USEEIO economic sectors
- ✅ Calculates contribution percentages for each emission source
- ✅ Provides detailed source categorization (fossil fuels, process emissions, etc.)
- ✅ 100% coverage on most enrichment layers

**Output:** Excel file with 23 enrichment columns covering 8,772 emission records across 527 economic sectors

---

## For Non-Coders

### What Does This Tool Do?

Imagine you want to know the carbon footprint of different products or industries. This tool takes raw EPA greenhouse gas data and transforms it into a rich dataset that answers questions like:

- **Which greenhouse gases** are emitted? (CO2, methane, etc.)
- **Which economic sectors** produce them? (manufacturing, agriculture, etc.)
- **What activities** cause the emissions? (combustion, refrigeration, etc.)
- **How much** do they contribute in CO2 equivalent terms?
- **What percentage** of a sector's emissions come from each source?

**Example Result:**
```
Sector: Food Manufacturing (USEEIO code 311111)
├── Carbon dioxide: 773,667 metric tons CO2e (90.8% of sector total)
│   └─ From: Natural Gas Combustion
├── HFC-134a refrigerant: 1,512 metric tons CO2e (0.18%)
│   └─ From: Commercial Refrigeration
└── Methane: 496 metric tons CO2e (0.06%)
    └─ From: Wastewater Treatment
```

### Quick Start

**For Windows Users:**

1. **Double-click** `EASY_SETUP.bat` to install everything automatically
2. **Wait** for installation to complete (5-10 minutes)
3. **Run** the extraction:
   ```
   .venv\Scripts\python.exe .\scripts\enrich_fbs_with_meta.py
   ```
4. **Find your results** in the `outputs/` folder:
   - `GHG_national_2022_m2_DecarbNexus_with_meta.xlsx` (enriched data)

**What to Expect:**
- The script will run for 2-3 minutes
- You'll see progress messages for each enrichment step
- Final output shows 8,772 records with 25 columns of data

### Understanding the Output

The Excel file contains one row per emission record with these key columns:

**Sector Information:**
- `USEEIO Sector Name`: Human-readable name (e.g., "Oilseed farming")
- `USEEIO Sector Code`: Industry code for supply chain analysis (e.g., "1111A0")
- `NAICS Sector Code`: North American Industry Classification code

**Emission Source Classification:**
- `Activity Category`: Broad source type (e.g., "Fossil Fuels Combustion")
- `IPCC/UNFCCC Category`: International category (e.g., "Energy", "Agriculture")
- `Activity Subcategory`: Detailed subcategory (e.g., "Stationary Combustion - Coal")
- `Activity Type`: Activity grouping (e.g., "Stationary Combustion")
- `Activity`: Specific activity (e.g., "Coal Electric Power", "Passenger Cars Gasoline On-Road")
- `Fuel Consumed`: Type of fossil fuel if applicable (Coal, Natural Gas, Petroleum)

**Gas Information:**
- `Gas Category`: Gas family (Carbon dioxide, Methane, Nitrous oxide, F-Gases)
- `Gas`: Specific greenhouse gas (e.g., "Carbon dioxide", "HFC-134a")

**Emissions Data:**
- `Emissions (kg)`: Original emissions in kilograms (for non-CO2e units)
- `Emissions (kgCO2e)`: Emissions already in kg CO2 equivalent (pre-converted data)
- `AR5-100 GWP`: IPCC AR5 100-year Global Warming Potential factor
- `Emissions (MTCO2e)`: Emissions in metric tons CO2 equivalent (calculated)
- `Contribution to USEEIO Sector's Scope 1 (%)`: Fraction of sector's total (0-1 scale, where 1 = 100%)

**Example**: If a source contributes 50% to its sector, the value is `0.5`, not `50`

**Source Documentation:**
- `US GHGI Chapter`, `US GHGI Table ID`, `US GHGI Table Name`: EPA GHGI references
- `Attribution Sources`: Data sources used

**Quality Control Columns** (optional, can be hidden in config):
- `MetaSources`, `ActivityProducedBy`, `FlowUUID`, `FlowAmount`, `FlowAmount Unit`

**Data is sorted by**: 
1. `USEEIO Sector Code` (ascending)
2. `NAICS Sector Code` (ascending)
3. `Contribution to USEEIO Sector's Scope 1 (%)` (descending)

This makes it easy to view all sources within a sector, with the largest contributors listed first.

---

## For Coders

### Installation

**Prerequisites:**
- Python 3.9 or higher
- Windows, macOS, or Linux

**Method 1: Automated (Windows)**
```bash
.\EASY_SETUP.bat
```

**Method 2: Manual**
```bash
# Create virtual environment
python -m venv .venv

# Activate environment
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install FlowSA v2.0.3
python install_flowsa_2.0.3.py
```

### Architecture Overview

**Pipeline Structure:**

```
┌─────────────────────────────────────────────────────────┐
│                   DATA LOADING (Steps 1-2)               │
│  ┌──────────────┐    ┌────────────────────────────┐    │
│  │ FlowSA Cache │───→│ GHG_national_2022_m2_      │    │
│  │ (Parquet)    │    │ DecarbNexus (8,772 rows)   │    │
│  └──────────────┘    └────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│               METADATA LOADING (Steps 4-5)               │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • EPA GHGI metadata (45 tables)                  │  │
│  │ • Fossil fuel lookups (24 mappings)              │  │
│  │ • Activity sets (75 mappings)                    │  │
│  │ • NAICS→USEEIO crosswalk (2,206 mappings)       │  │
│  │ • GHG source categories (159 mappings)           │  │
│  │ • Flowable→Gas category (18 mappings)            │  │
│  │ • IPCC AR5-100 GWPs (196 factors)                │  │
│  │ • Method YAML (80 activity mappings)             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│             ENRICHMENT PIPELINE (Steps 6-7.13)           │
│                                                          │
│  Step 6:    EPA GHGI Metadata → 8,562 records (97.6%)  │
│  Step 7:    PrimaryActivity → 7,401 records (84.4%)    │
│  Step 7.5:  Fossil Fuel Type → 2,484 records (28.3%)   │
│  Step 7.6:  Activity Set → 8,772 records (100%)        │
│  Step 7.7:  USEEIO Sectors → 8,772 records (100%)      │
│  Step 7.8:  GHG Categories → 8,772 records (100%)      │
│  Step 7.9:  Gas Category → 8,772 records (100%)        │
│  Step 7.10: AR5-100 GWP & MTCO2e → 8,772 (100%)        │
│  Step 7.11: Contribution % → 8,772 records (100%)      │
│  Step 7.12: USEEIO Sector Names → 8,722 (99.4%)        │
│  Step 7.13: Rename columns & create kg/kgCO2e cols     │
│                                                          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              OUTPUT (Steps 9-10)                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ GHG_national_2022_m2_DecarbNexus_with_meta.xlsx │  │
│  │ • 8,772 rows × 23 columns                        │  │
│  │ • 6.29 billion metric tons CO2e total            │  │
│  │ • 527 unique USEEIO sectors                      │  │
│  │ • 18 greenhouse gases                            │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Configuration

All settings are in `config.py`:

**Key Configuration Options:**

```python
# Model Selection
MODELNAME = "GHG_national_2022_m2_DecarbNexus"
MODEL_YEAR = 2022

# IPCC Global Warming Potential Settings
IPCC_INDICATOR = "AR5-100"      # Options: AR4-100, AR5-100, AR6-100, etc.
IPCC_CONTEXT = "emission/air"   # Filter for atmospheric emissions

# Column Filtering
EXCLUDE_QC_COLUMNS = False  # Set True to remove quality control columns
```

**Quality Control Columns:**
These columns are useful for validation but can be excluded from final output by setting `EXCLUDE_QC_COLUMNS = True`:
- `FlowUUID` - Used for GWP lookup
- `SectorProducedBy` - Raw NAICS code (replaced by USEEIO)
- `FlowAmount` - Raw emission amount (replaced by MTCO2e)
- `Unit` - Raw unit (kg or kg CO2e)
- `AR5-100 GWP` - Conversion factor
- `MetaSources` - EPA table references
- `ActivityProducedBy` - Activity codes

### Running the Pipeline

**Basic Execution:**
```bash
python scripts/enrich_fbs_with_meta.py
```

**Expected Runtime:** 2-3 minutes

**Interactive Prompts:**
- Sanity check comparison: Type `yes` to continue if minor differences detected
  - Known issue: 7 extra rows from EPA_GHGI_T_4_64 table

**Output Files (6 formats):**

All files: `outputs/GHG_national_2022_m2_DecarbNexus.*`

1. **Excel** (`.xlsx`) - Manual analysis, charts, pivot tables
2. **CSV** (`.csv`) - Universal data interchange, human-readable
3. **Parquet** (`.parquet`) - Data science workflows (pandas, DuckDB, Polars)
4. **JSON** (`.json`) - Hierarchical processing, JavaScript applications
5. **JSON-LD** (`.jsonld`) - RDF knowledge graphs, semantic web (convertible to Turtle)
6. **Sunburst JSON** (`_sunburst.json`) - D3.js visualization (lightweight, aggregated)

---

## Data Enrichment Layers

The tool adds 11 layers of enrichment to the raw EPA data:

### 1. EPA GHGI Metadata (97.6% coverage)
**Source:** `outputs/EPA_GHGI_meta_sources.csv` (45 tables)

Adds EPA Greenhouse Gas Inventory report references:
- `chapter` - Report chapter number
- `table_id` - Table identifier (e.g., "EPA_GHGI_T_3_8")
- `desc` - Table description
- `IPCC_Category` - IPCC classification
- `Subcategory` - Detailed subcategory

### 2. Primary Activity (84.4% coverage)
**Source:** FlowSA method YAML files

Extracts detailed activity descriptions:
- **Direct attribution:** Uses `ActivityProducedBy` field directly
- **YAML mapping:** Looks up activities from method definitions
- **Special case:** Semiconductors use YAML values even with direct attribution

**Example:**
```
MetaSource: EPA_GHGI_T_3_8.residential
→ PrimaryActivity: "Fuel Oil Residential | Coal Residential | Natural Gas Residential | Wood Residential"
```

### 3. Fuel Consumed (28.3% coverage)
**Sources:** 
- `data/ListOfFossilFuelsByTable.csv` (9 entries)
- `data/ListOfFossilFuelsByTerm.csv` (15 entries)

Two-step matching:
1. **Table reference:** Direct lookup by EPA GHGI table
2. **Term matching:** Search for keywords in `PrimaryActivity`

**Values:** Coal, Natural Gas, Petroleum, Peat, Wood

### 4. Activity Set (100% coverage)
**Source:** `data/ListOfActivitySets.csv` (75 mappings)

Activity categorization with special logic:
- **Direct attribution cases:** If `MetaSources` contains `.direct` or `.direct_attribution`, uses `PrimaryActivity` as activity set
- **Otherwise:** Looks up in CSV mapping

### 5. USEEIO Sector Codes (100% coverage)
**Source:** `data/NAICS_to_USEEIO_crosswalk.csv` (2,206 mappings)

Maps NAICS codes to USEEIO economic sectors:
```
NAICS 311111 → USEEIO 311111 (Dog and cat food manufacturing)
NAICS 325110 → USEEIO 325110 (Petrochemical manufacturing)
```

### 6. IPCC/UNFCCC Category (100% coverage)
**Source:** `data/MetaSource_to_GHGSourceCategory_mapping.csv` (159 mappings)

International reporting categories with hierarchical fallback:
1. Try exact match on `MetaSources` + `ActivityProducedBy`
2. If no match, strip activity set suffix and retry

**Categories:**
- Industrial Processes and Product Use (5,106 records)
- Energy (3,527 records)
- Agriculture (85 records)
- Waste (5 records)

### 7. Activity Category (100% coverage)
**Source:** Same as IPCC/UNFCCC Category mapping

**Categories:**
- Process & Fugitive Gases (5,196 records)
- Fossil Fuels Combustion (3,516 records)
- Electric Power Generation (11 records)

### 8. Gas Category (100% coverage)
**Source:** `data/flowable_categorization.csv` (18 mappings)

Groups greenhouse gases into broad categories:
- **Carbon dioxide** (2,304 records, 5.03 billion MTCO2e)
- **Methane** (1,078 records, 700 million MTCO2e)
- **Nitrous oxide** (1,130 records, 388 million MTCO2e)
- **Fluorinated gases (F-Gases)** (4,260 records, 169 million MTCO2e)

### 9. AR5-100 GWP (100% coverage)
**Source:** `data/IPCC_v1.1.1_27ba917.parquet` (196 factors)

IPCC Fifth Assessment Report 100-year Global Warming Potentials:
- Filters for `Indicator = "AR5-100"` and `Context = "emission/air"`
- Matches by `FlowUUID`

**Special handling:**
- Records with `Unit = "kg CO2e"`: GWP = 1.0 (already converted)
- Records with `Unit = "kg"`: Lookup GWP factor by UUID

**Example GWPs:**
- Carbon dioxide: 1
- Methane: 28
- Nitrous oxide: 265
- HFC-134a: 1,300

### 10. Emissions (MTCO2e) (100% coverage)
Converts all emissions to metric tons of CO2 equivalent:

**Formula:**
```python
if Unit == "kg CO2e":
    MTCO2e = FlowAmount / 1000
else:  # Unit == "kg"
    MTCO2e = (FlowAmount × AR5-100 GWP) / 1000
```

**Total:** 6.29 billion metric tons CO2e

### 11. Contribution Percentage (100% coverage)
Calculates each record's share of its USEEIO sector's total emissions:

**Formula:**
```python
Contribution (%) = (Record MTCO2e / Sector Total MTCO2e) × 100
```

**Statistics:**
- Min: 0.000000%
- Max: 100.00%
- Mean: 4.38%
- Median: 0.07%

**Use Cases:**
- Identify dominant emission sources within a sector
- Filter to major contributors (e.g., >10% contribution)
- Understand emission source diversity

---

## Configuration Reference

### File Paths
```python
# Lookup files (data/ directory)
FOSSIL_FUEL_BY_TABLE_CSV = "data/ListOfFossilFuelsByTable.csv"
FOSSIL_FUEL_BY_TERM_CSV = "data/ListOfFossilFuelsByTerm.csv"
ACTIVITY_SETS_CSV = "data/ListOfActivitySets.csv"
NAICS_TO_USEEIO_CSV = "data/NAICS_to_USEEIO_crosswalk.csv"
METASOURCE_TO_GHGSOURCE_CSV = "data/MetaSource_to_GHGSourceCategory_mapping.csv"
FLOWABLE_CATEGORIZATION_CSV = "data/flowable_categorization.csv"
IPCC_AR5_100_PARQUET = "data/IPCC_v1.1.1_27ba917.parquet"
```

### Column Order
```python
KEEP_COLUMNS = [
    "Flowable",           # Gas species
    "FlowUUID",           # QC: UUID for GWP lookup
    "Gas category",       # Enriched gas grouping
    "SectorProducedBy",   # QC: Raw NAICS code
    "USEEIO",             # Enriched sector code
    "FlowAmount",         # QC: Raw amount
    "Unit",               # QC: Raw unit
    "AR5-100 GWP",        # QC: Conversion factor
    "Emissions (MTCO2e)", # Enriched emissions
    "Contribution (%)",   # Enriched percentage
    "MetaSources",        # QC: Table references
    "ActivityProducedBy", # QC: Activity codes
    "AttributionSources", # Source attribution
    "PrimaryActivity",    # Enriched activity details
    "Activity Set",       # Enriched activity category
    "Fossil Fuel",        # Enriched fuel type
    "IPCC/UNFCCC Category",  # Enriched IPCC category
    "Activity Category",   # Enriched source category
    "chapter",            # EPA metadata
    "table_id",           # EPA metadata
    "desc",               # EPA metadata
    "IPCC_Category",      # EPA metadata
    "Subcategory",        # EPA metadata
]
```

### Alternative Models
```python
ALTERNATIVE_MODELS = {
    "GHG_national_2023_m1": {
        "parquet_file": "GHG_national_2023_m1_v2.1.0.parquet",
        "description": "2023 GHG National Model - Method 1",
        "year": 2023
    },
    # ... more models
}
```

To switch models, update `MODELNAME` and `FILE_NAME_PARQUET` in config.py

---

## Troubleshooting

### Common Issues

**1. Permission Error when saving Excel**
```
PermissionError: [Errno 13] Permission denied: 'outputs\..._with_meta.xlsx'
```
**Solution:** Close the Excel file and run again

**2. FlowSA version mismatch**
```
WARNING: Sanity check detected differences!
```
**Solution:** 
```bash
python clear_flowsa_cache.py --activity-only
```
This clears cached data from different FlowSA versions

**3. Missing lookup files**
```
Warning: ... file not found at data/...
```
**Solution:** Ensure all CSV files are in the `data/` directory. Check the repository for missing files.

**4. Import errors**
```
ModuleNotFoundError: No module named 'flowsa'
```
**Solution:**
```bash
.venv\Scripts\activate  # Windows
python install_flowsa_2.0.3.py
```

### Coverage Issues

**Expected coverage rates:**
- ✅ 100%: Activity Set, USEEIO, GHG Categories, Gas Category, GWP, MTCO2e, Contribution %
- ✅ 97.6%: EPA GHGI Metadata
- ✅ 84.4%: PrimaryActivity (some direct attribution cases don't have YAML mappings)
- ✅ 28.3%: Fossil Fuel (only applicable to combustion sources)

**If coverage is significantly lower:**
1. Check that all lookup CSV files are present
2. Verify FlowSA version is 2.0.3
3. Clear cache and regenerate: `python clear_flowsa_cache.py`

### Performance

**Slow execution:**
- First run: 5-10 minutes (downloads source data)
- Subsequent runs: 2-3 minutes (uses cached data)
- Large datasets: Consider filtering by sector or year

---

## Best Practices

### For Non-Coders

1. **Don't modify the scripts** - Use `config.py` for all settings
2. **Keep backups** - Copy output files before re-running
3. **Check coverage statistics** - Review the processing summary
4. **Start simple** - Use default settings first, customize later
5. **Ask for help** - File GitHub issues with error messages and output logs

### For Coders

1. **Version control** - Commit config changes before running
2. **Test with small datasets** - Filter to single sector for development
3. **Validate outputs** - Use the verification scripts in `local/`
4. **Document customizations** - Comment config changes clearly
5. **Cache management** - Clear cache when switching FlowSA versions

### Data Analysis

1. **Filter by contribution** - Focus on sources >1% for major contributors
2. **Group by sector** - Aggregate MTCO2e by USEEIO code
3. **Compare gas categories** - Different gases have different reduction strategies
4. **Track fossil fuels** - Identify combustion vs process emissions
5. **Use Activity Set** - Group related emission sources

### Code Maintenance

**Current structure:** Single 2,364-line script (`enrich_fbs_with_meta.py`)

**Recommended refactoring for teams:**

```
scripts/
├── enrich_fbs_with_meta.py       # Main orchestration (200 lines)
├── modules/
│   ├── data_loading.py           # Steps 1-5: Load data & metadata
│   ├── enrichment_ghgi.py        # Step 6-7: EPA GHGI enrichment
│   ├── enrichment_sectors.py     # Step 7.6-7.7: Activity sets & USEEIO
│   ├── enrichment_categories.py  # Step 7.8-7.9: GHG & gas categories
│   ├── enrichment_gwp.py         # Step 7.10-7.11: GWP & contribution
│   ├── validation.py             # Step 8: Data quality checks
│   └── output.py                 # Steps 9-10: Filtering & saving
└── utils/
    ├── yaml_parser.py            # YAML extraction utilities
    ├── lookup_helpers.py         # Hierarchical matching logic
    └── column_filters.py         # Column management
```

**Benefits of refactoring:**
- ✅ Easier testing (unit tests per module)
- ✅ Better code reuse (import enrichment functions)
- ✅ Clearer organization (logical separation)
- ✅ Easier onboarding (smaller files to understand)

**When to refactor:**
- Multiple developers working on the code
- Adding new enrichment layers frequently
- Maintaining multiple model versions
- Need for automated testing

**When current structure is fine:**
- Single user/researcher
- Stable enrichment pipeline
- Infrequent modifications
- Works well as-is

---

## Working with Output Formats

### Excel (`.xlsx`)
**Best for:** Manual analysis, charts, pivot tables, sharing with non-technical users

**Usage:**
- Open directly in Excel, LibreOffice Calc, or Google Sheets
- Create pivot tables to analyze by sector, gas, or source
- Generate charts and visualizations
- Filter and sort data interactively

### CSV (`.csv`)
**Best for:** Universal data interchange, simple imports, human-readable format

**Usage:**
```python
import pandas as pd
df = pd.read_csv('outputs/GHG_national_2022_m2_DecarbNexus.csv')
```

**Advantages:**
- Text format (easy to inspect, version control)
- Compatible with any tool (Python, R, Excel, databases)
- Simple and widely supported

**Limitations:**
- Larger file size than Parquet
- No type preservation (everything read as strings)
- Slower for large datasets

### Parquet (`.parquet`)
**Best for:** Data science workflows, analytics, large datasets

**Why Parquet:**
- **Columnar storage:** 10-100x faster for analytical queries
- **Compression:** Smaller files (typically 60-80% reduction)
- **Type preservation:** Maintains int/float/date types
- **Native support:** pandas, Polars, DuckDB, Apache Arrow, Spark

**Usage Examples:**

```python
# pandas (most common)
import pandas as pd
df = pd.read_parquet('outputs/GHG_national_2022_m2_DecarbNexus.parquet')

# DuckDB (SQL on Parquet)
import duckdb
result = duckdb.query("""
    SELECT "USEEIO Sector Name", SUM("Emissions (MTCO2e)") as total
    FROM 'outputs/GHG_national_2022_m2_DecarbNexus.parquet'
    WHERE "Contribution to USEEIO Sector's Scope 1 (%)" > 0.1
    GROUP BY "USEEIO Sector Name"
    ORDER BY total DESC
    LIMIT 10
""").df()

# Polars (fastest DataFrame library)
import polars as pl
df = pl.read_parquet('outputs/GHG_national_2022_m2_DecarbNexus.parquet')
top_sources = df.filter(pl.col("Contribution to USEEIO Sector's Scope 1 (%)") > 0.1)
```

**Performance comparison (typical 8,772 row file):**
- CSV read: ~200ms
- Parquet read: ~20ms (10x faster)
- File size: CSV 2.5 MB, Parquet 600 KB

### JSON (`.json`)
**Best for:** Hierarchical processing, JavaScript applications, web APIs

**Structure:** Array of records (one object per row)
```json
[
  {
    "USEEIO Sector Code": "111120",
    "USEEIO Sector Name": "Oilseed farming",
    "NAICS Sector Code": "111120",
    "Emissions (MTCO2e)": 12.34,
    "Contribution to USEEIO Sector's Scope 1 (%)": 0.45,
    ...
  },
  ...
]
```

**Usage:**
```python
import json
with open('outputs/GHG_national_2022_m2_DecarbNexus.json') as f:
    data = json.load(f)

# Group by USEEIO sector
from collections import defaultdict
by_sector = defaultdict(list)
for record in data:
    by_sector[record['USEEIO Sector Code']].append(record)

# Find top contributors per sector
for sector, sources in by_sector.items():
    top_sources = sorted(sources, key=lambda x: x['Contribution to USEEIO Sector\'s Scope 1 (%)'], reverse=True)[:3]
    print(f"{sector}: {len(sources)} sources, top contributor: {top_sources[0]['Contribution to USEEIO Sector\'s Scope 1 (%)']:.1%}")
```

**JavaScript:**
```javascript
fetch('outputs/GHG_national_2022_m2_DecarbNexus.json')
  .then(response => response.json())
  .then(data => {
    // Group by sector
    const bySector = data.reduce((acc, record) => {
      const sector = record['USEEIO Sector Code'];
      if (!acc[sector]) acc[sector] = [];
      acc[sector].push(record);
      return acc;
    }, {});
  });
```

### JSON-LD (`.jsonld`)
**Best for:** RDF knowledge graphs, semantic web, Turtle conversion

**What is JSON-LD:**
- JSON for Linked Data (W3C standard)
- Adds `@context` for semantic meaning
- Can be converted to RDF formats (Turtle, N-Triples, RDF/XML)
- Enables SPARQL queries, reasoning, ontology integration

**Structure:**
```json
{
  "@context": {
    "@vocab": "http://example.org/ghg#",
    "useeio": "http://useeio.org/sectors/",
    "naics": "http://naics.org/sectors/",
    "ipcc": "http://ipcc.org/categories/",
    "gas": "http://example.org/gases/",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "Emissions (MTCO2e)": {"@type": "xsd:decimal"},
    "Contribution to USEEIO Sector's Scope 1 (%)": {"@type": "xsd:decimal"},
    "AR5-100 GWP": {"@type": "xsd:decimal"}
  },
  "@graph": [ ... records ... ]
}
```

**Convert to Turtle for RDF:**
```python
from rdflib import Graph

# Load JSON-LD
g = Graph()
g.parse('outputs/GHG_national_2022_m2_DecarbNexus.jsonld', format='json-ld')

# Serialize to Turtle
g.serialize('outputs/GHG_national_2022_m2_DecarbNexus.ttl', format='turtle')

# Query with SPARQL
query = """
PREFIX ghg: <http://example.org/ghg#>
PREFIX useeio: <http://useeio.org/sectors/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?sector ?emission
WHERE {
  ?record ghg:USEEIO_Sector_Code ?sector .
  ?record ghg:Emissions_(MTCO2e) ?emission .
  FILTER (?emission > 100.0)
}
ORDER BY DESC(?emission)
LIMIT 10
"""
results = g.query(query)
for row in results:
    print(f"{row.sector}: {row.emission} MTCO2e")
```

**Integration with knowledge graphs:**
- Import into Apache Jena, GraphDB, Stardog
- Link to other datasets (EPA ontologies, NAICS URIs, GHG vocabularies)
- Enable reasoning (e.g., infer indirect emissions)
- Query across multiple data sources with SPARQL federation

**Turtle output example:**
```turtle
@prefix ghg: <http://example.org/ghg#> .
@prefix useeio: <http://useeio.org/sectors/> .
@prefix naics: <http://naics.org/sectors/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

[] a ghg:EmissionRecord ;
   ghg:USEEIO_Sector_Code "111120" ;
   ghg:USEEIO_Sector_Name "Oilseed farming" ;
   ghg:NAICS_Sector_Code naics:111120 ;
   ghg:Emissions_(MTCO2e) "12.34"^^xsd:decimal ;
   ghg:Contribution_to_USEEIO_Sector's_Scope_1_(%) "0.45"^^xsd:decimal .
```

### Sunburst JSON (`_sunburst.json`)
**Best for:** D3.js sunburst charts, interactive hierarchical visualization

**What is it:**
- Lightweight aggregated dataset (8,772 → ~3,901 records)
- Only 5 columns: hierarchy dimensions + contribution value
- Contributions summed/rolled up to unique combinations
- Optimized for fast filtering and rendering

**Structure:**
```json
[
  {
    "USEEIO Sector Code": "111120",
    "Activity Category": "Fossil Fuels Combustion",
    "Activity Set": "Natural Gas",
    "Gas Category": "Carbon dioxide",
    "Contribution to USEEIO Sector's Scope 1 (%)": 0.234
  },
  ...
]
```

**D3.js Usage:**

```javascript
// Load data
d3.json('outputs/GHG_national_2022_m2_DecarbNexus_sunburst.json')
  .then(data => {
    // Filter to specific sector
    const sectorCode = "111120"; // Oilseed farming
    const sectorData = data.filter(d => d['USEEIO Sector Code'] === sectorCode);
    
    // Build hierarchy for sunburst
    const hierarchy = {
      name: sectorCode,
      children: d3.groups(sectorData, 
        d => d['Activity Category'])
        .map(([category, items]) => ({
          name: category,
          children: d3.groups(items, d => d['Activity Set'])
            .map(([activity, items2]) => ({
              name: activity,
              children: items2.map(d => ({
                name: d['Gas category'],
                value: d['Contribution to USEEIO Sector\'s Scope 1 (%)']
              }))
            }))
        }))
    };
    
    // Create sunburst chart
    const root = d3.hierarchy(hierarchy)
      .sum(d => d.value)
      .sort((a, b) => b.value - a.value);
    
    // ... render with d3.partition()
  });
```

**Interactive sector selector:**
```javascript
// Get unique sectors for dropdown
const sectors = [...new Set(data.map(d => d['USEEIO Sector Code']))];

// Create dropdown
const select = d3.select('#sector-select')
  .selectAll('option')
  .data(sectors)
  .enter()
  .append('option')
  .text(d => d);

// Update chart on selection
select.on('change', function() {
  const selectedSector = this.value;
  const filtered = data.filter(d => d['USEEIO Sector Code'] === selectedSector);
  updateSunburst(filtered);
});
```

**Performance benefits:**
- File size: ~500 KB (vs 25+ MB for full dataset)
- Load time: <50ms (vs 500+ ms)
- Render time: Instant (pre-aggregated)
- Memory usage: Minimal (only 5 fields per record)

**Hierarchical levels:**
1. **USEEIO Sector Code** (outer ring) - 384 unique sectors
2. **Activity Category** (second ring) - Energy, Industrial Processes, etc.
3. **Activity Set** (third ring) - Specific activities within category
4. **Gas category** (inner ring) - CO2, Methane, etc.
5. **Contribution** (size) - Fraction of sector's total (0-1 scale)

### Format Selection Guide

| Use Case | Recommended Format | Reason |
|----------|-------------------|--------|
| Manual analysis, charts | **Excel** | Familiar interface, built-in visualizations |
| Data import to any tool | **CSV** | Universal compatibility |
| Analytical queries (pandas/SQL) | **Parquet** | 10-100x faster, compression |
| Web applications | **JSON** | Native JavaScript support |
| Knowledge graphs, SPARQL | **JSON-LD** | RDF-ready, semantic web |
| D3.js sunburst chart | **Sunburst JSON** | Lightweight, pre-aggregated, fast |
| Large-scale analytics (Spark) | **Parquet** | Distributed processing |
| Version control tracking | **CSV** | Text diffs visible in Git |
| Database import | **CSV** or **Parquet** | Standard import formats |
| Hierarchical transformations | **JSON** | Easy nested structure building |
| Ontology integration | **JSON-LD → Turtle** | OWL reasoning, SPARQL |

---

## Additional Resources

**Documentation:**
- [EPA GHGI Reports](https://www.epa.gov/ghgemissions/inventory-us-greenhouse-gas-emissions-and-sinks)
- [FlowSA Documentation](https://github.com/USEPA/flowsa)
- [USEEIO Models](https://www.epa.gov/land-research/us-environmentally-extended-input-output-useeio-models)
- [IPCC AR5 Report](https://www.ipcc.ch/report/ar5/)

**Support:**
- GitHub Issues: Report bugs or request features
- Discussions: Ask questions about usage

**Citation:**
If you use this tool in research, please cite:
- FlowSA library (v2.0.3)
- EPA GHGI report (2022 edition)
- IPCC Fifth Assessment Report

---

**Last Updated:** November 7, 2025  
**Version:** 1.0.0  
**Maintained by:** [Your Name/Organization]
