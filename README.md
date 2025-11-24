# FlowSA GHG Sources Extraction

**A comprehensive tool for enriching EPA greenhouse gas emission data with supply chain metadata**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FlowSA 2.0.3](https://img.shields.io/badge/FlowSA-2.0.3-green.svg)](https://github.com/USEPA/flowsa)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**🎨 [Interactive Visualization](https://decarbnexus.github.io/Flowsa_extract_GHG_sources/)** - Explore the data with our D3.js sunburst chart *(coming soon)*

---

## ⚡ Quick Reference

```
┌──────────────────────────────────────────────────────────────┐
│ INPUT:   8,772 EPA GHGI emission records (GHG 2022 m2)      │
│ OUTPUT:  25 enriched columns + 6 output formats             │
│ TIME:    2-3 minutes processing                             │
│ RESULT:  6.29 billion MTCO2e with full supply chain context │
│ FORMATS: Excel, CSV, Parquet, JSON, JSON-LD, Sunburst       │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎯 What This Tool Does

Transforms raw EPA greenhouse gas data into a rich, analysis-ready dataset with:

✅ **11 layers of enrichment** covering emissions, sectors, activities, and sources  
✅ **IPCC AR5-100 Global Warming Potentials** for CO2 equivalent calculations  
✅ **USEEIO sector mapping** for supply chain analysis  
✅ **Contribution percentages** showing each source's share within a sector  
✅ **100% coverage** on most enrichment layers  
✅ **Interactive sunburst visualization** for exploring sector emissions  

**Input:** EPA GHGI emissions data from FlowSA (8,772 records for GHG_national_2022_m2)  
**Output:** 
- Enriched dataset in 6 formats (Excel, CSV, Parquet, JSON, JSON-LD, Sunburst JSON)
- 21+ metadata columns ready for analysis
- Interactive web visualization

---

## 📚 Documentation

### For Everyone
- **[User Guide](docs/USER_GUIDE.md)** - Comprehensive guide for non-coders and coders
  - Non-coder friendly quick start
  - Understanding the output
  - Configuration options
  - Troubleshooting

### For Developers
- **[Technical Reference](docs/TECHNICAL_REFERENCE.md)** - Developer documentation
  - Code architecture
  - Function reference
  - Enrichment algorithms
  - Performance optimization
  - Extending the pipeline

### Quick Links
- [Installation](#-quick-start)
- [What the Output Contains](#-what-the-output-contains)
- [Data Enrichment Layers](#-data-enrichment-overview)
- [Troubleshooting](#-troubleshooting)

---

## 🚀 Quick Start

### Prerequisites

**CRITICAL REQUIREMENTS:**
1. **Python 3.9-3.11** (NOT 3.12+) - FlowSA v2.0.3 and pandas 2.0.3 require Python 3.9, 3.10, or 3.11
2. **FlowSA v2.0.3** for reproducibility (matches the reference data used in Supply Chain Emission Factors v1.3.0)

⚠️ **If you have Python 3.12+**: See `PYTHON_VERSION_FIX.md` for how to install Python 3.11

### Installation Steps

```bash
# 1. Clone repository
# GitHub URL will be added when repository is published
git clone https://github.com/DecarbNexus/Flowsa_extract_GHG_sources.git
cd Flowsa_extract_GHG_sources

# 2. Create virtual environment (Python 3.9-3.11 required!)
python -m venv .venv

# 3. Activate
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# 4. Install FlowSA v2.0.3
python install_flowsa_2.0.3.py

# 5. Install dependencies
pip install -r requirements.txt

# 6. Verify installation
python -c "import flowsa; print('FlowSA version:', flowsa.__version__)"
# Should output: FlowSA version: 2.0.3

# 7. Extract EPA GHGI metadata (first time only)
python scripts/extract_meta_from_EPA_GHGI.py
```

**Disk space requirements:** ~500 MB for FlowSA installation and cached data

### Running the Enrichment

```bash
# Activate environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Run enrichment pipeline
python scripts/enrich_fbs_with_meta.py

# Wait 2-3 minutes...
# Find your results in outputs/GHG_national_2022_m2_DecarbNexus_with_meta.xlsx
```

**When prompted about sanity check differences:** Type `yes` to continue (7 extra rows is a known issue)

---

## 📊 What the Output Contains

The enriched dataset includes 8,772 emission records with 25 columns across multiple output formats:

### Output Formats

#### 1. **Tabular Data** (Excel, CSV, Parquet)
Traditional flat table format for analysis and data science workflows.

#### 2. **Hierarchical JSON-LD** (Legacy)
Single nested hierarchy: Sector → Category → Subcategory → Activity → Gas
- `*_industry.jsonld` - Full detail with all metadata
- `*_industry_sunburst.jsonld` - Aggregated for visualization
- `*_ghg_source_classification.jsonld` - GHG taxonomy without sectors

#### 3. **Event-Based JSON-LD**
Multi-dimensional emission events suitable for:
- **Knowledge graphs** & RDF triple stores
- **D3.js sunburst** with dynamic filtering
- **SPARQL queries** & semantic analysis

**Files:**
- `GHG_national_2022_m2_DecarbNexus_emission_events.jsonld` - Full RDF structure with semantic relationships
- `GHG_national_2022_m2_DecarbNexus_emission_events_sunburst.json` - Optimized D3.js hierarchy

*Note: Replace `2022_m2_DecarbNexus` with your configured model name*

### Essential Analysis Columns
| Column | Description | Example |
|--------|-------------|---------|
| `USEEIO Sector Name` | Human-readable sector name | "Oilseed farming" |
| `USEEIO Sector Code` | Economic sector code | "1111A0" |
| `NAICS Sector Code` | NAICS industry code | "311111" |
| `Gas` | Greenhouse gas species | "Carbon dioxide", "Methane" |
| `Gas Category` | Gas type grouping | "Carbon dioxide", "F-Gases" |
| `Emissions (kg)` | Emissions in kilograms (non-CO2e) | 1,234,567 |
| `Emissions (kgCO2e)` | Emissions in kg CO2e (pre-converted) | 5,678,901 |
| `Emissions (MTCO2e)` | Metric tons CO2 equivalent | 773,666.61 |
| `Contribution to USEEIO Sector's Scope 1 (%)` | % of sector total | 90.76% |
| `Activity` | Detailed emission source | "Natural Gas Combustion" |
| `Activity Set` | Activity category | "Stationary Combustion" |
| `IPCC/UNFCCC Category` | International category | "Energy", "Industrial Processes" |
| `Activity Category` | Source type | "Fuels Combustion" |

### Quality Control Columns (Can be Hidden)
Set `EXCLUDE_QC_COLUMNS = True` in `config.py` to remove these:
- `MetaSources`, `ActivityProducedBy`, `FlowUUID`, `FlowAmount`, `FlowAmount Unit`

### File Sizes (GHG_national_2022_m2 model)
- **Excel**: ~3.5 MB
- **Parquet**: ~450 KB  
- **CSV**: ~4.2 MB
- **JSON-LD (industry)**: ~12 MB
- **Sunburst JSON**: ~2 MB

### Sample Output
```
Sector: Oilseed farming (USEEIO 1111A0)
├── CO2 from Natural Gas: 773,667 MTCO2e (90.8% of sector)
├── HFC-134a from Refrigeration: 1,512 MTCO2e (0.18%)
├── Methane from Wastewater: 496 MTCO2e (0.06%)
└── ... 11 more sources
    Total: 852,474 MTCO2e (100%)

Sorted by: USEEIO Code → NAICS Code → Contribution % (desc)
```

### Event-Based Structure Example

Each emission becomes a semantic event with explicit relationships:

```json
{
  "@id": "emission_event:331313_aluminum_production_hexafluoroethane_none",
  "@type": "EmissionEvent",
  
  "hasCategory": {
    "name": "Process & Fugitive Gases",
    "subcategory": "Industrial Production Processes",
    "subSubcategory": "PFCs from aluminum production"
  },
  
  "fromActivity": {
    "activitySet": "PFCs from aluminum production",
    "activity": "Aluminum Production"
  },
  
  "consumesFuel": {"name": null},
  
  "emitsGas": {
    "gasCategory": "Fluorinated gases (F-Gases)",
    "gas": "Hexafluoroethane",
    "co2eGWP": "AR5-100yr",
    "gwpAR5_100": 11100
  },
  
  "mapsToIPCC": {
    "category": "Industrial Processes and Product Use"
  },
  
  "inSector": {
    "useeioCode": "331313",
    "naicsCodes": ["331313"]
  },
  
  "hasEmission": {
    "contributionToSectorScope1Percent": 0.023000239
  },
  
  "derivedFrom": {
    "publication": "Inventory of U.S. Greenhouse Gas Emissions and Sinks: 1990-2022",
    "tableId": "EPA_GHGI_T_4_103",
    "year": 2022,
    "location": "US"
  }
}
```

**Benefits:**
- Multi-dimensional filtering (by sector, gas, activity, fuel)
- Semantic queries (SPARQL)
- D3.js visualization with dynamic faceting
- RDF knowledge graph integration

---

## 🔍 Data Enrichment Overview

The tool adds 13 layers of enrichment (coverage rates shown for GHG_national_2022_m2 model, may vary by model):

1. **EPA GHGI Metadata** (97.6% coverage) - Report chapter, table ID, descriptions
2. **Primary Activity** (84.4%) - Detailed activity descriptions from YAML
3. **Fossil Fuel Type** (28.3%) - Coal, Natural Gas, Petroleum, etc.
4. **Activity Set** (100%) - Activity categorization
5. **USEEIO Sector Codes** (100%) - NAICS to USEEIO mapping
6. **IPCC/UNFCCC Category** (100%) - International reporting categories
7. **Activity Category/Subcategory/Type** (100%) - Process emissions, combustion, fuel types, etc.
8. **Gas Category** (100%) - CO2, Methane, Nitrous oxide, F-Gases
9. **AR5-100 GWP** (100%) - IPCC global warming potentials
10. **Emissions (MTCO2e)** (100%) - CO2 equivalent calculations
11. **Contribution (%)** (100%) - Share of sector total
12. **USEEIO Sector Names** (99.4%) - Human-readable sector names
13. **Emissions (kg) & (kgCO2e)** (100%) - Original emissions by unit type

**Total Emissions:** 6.29 billion metric tons CO2e

See **[User Guide - Data Enrichment Layers](docs/USER_GUIDE.md#data-enrichment-layers)** for detailed documentation of each layer.

---

## ⚙️ Configuration

All settings in `config.py`:

### Change the Model
```python
MODELNAME = "GHG_national_2022_m2_DecarbNexus"
MODEL_YEAR = 2022

# Available alternatives:
# - GHG_national_2023_m1
# - GHG_national_2023_m2
```

### IPCC GWP Settings
```python
IPCC_INDICATOR = "AR5-100"      # Options: AR4-100, AR5-100, AR6-100, etc.
IPCC_CONTEXT = "emission/air"   # Filter for atmospheric emissions
```

### Hide Quality Control Columns
```python
EXCLUDE_QC_COLUMNS = True  # Removes FlowUUID, SectorProducedBy, etc. from output
```

---

## 🔧 Troubleshooting

### Common Issues

**❌ Permission Error saving Excel**
```
PermissionError: [Errno 13] Permission denied: '..._with_meta.xlsx'
```
**✅ Solution:** Close the Excel file and run again

**❌ Data Mismatch (Wrong row counts)**
```
WARNING: Sanity check detected differences!
```
**✅ Solution:** Clear cached FlowByActivity files (these may be from different FlowSA versions)
```bash
python scripts/clear_flowsa_cache.py --activity-only  # Only clears FlowByActivity cache
python scripts/enrich_fbs_with_meta.py
```

**Why this happens**: FlowSA caches downloaded FlowByActivity files in `C:\Users\<you>\AppData\Local\flowsa\`. If you've used different FlowSA versions, old cached files may be used instead of generating fresh ones with your current version.

**What the script does**:
- `--activity-only`: Only deletes FlowByActivity cache (keeps your downloaded FlowBySector reference files)
- `--dry-run`: Preview what would be deleted
- `--keep-fbs`: Clear everything except FlowBySector files

**❌ ModuleNotFoundError: No module named 'flowsa'**  
**✅ Solution:**
```bash
.venv\Scripts\activate
python install_flowsa_2.0.3.py
```

**❌ Wrong Python version**  
**✅ Solution:** See `PYTHON_VERSION_FIX.md` to install Python 3.11

### Coverage Issues

**Expected coverage rates (for GHG_national_2022_m2 model):**
- ✅ 100%: Activity Set, USEEIO, GHG Categories, GWP, MTCO2e, Contribution %
- ✅ 97.6%: EPA GHGI Metadata
- ✅ 84.4%: PrimaryActivity
- ✅ 28.3%: Fossil Fuel (only combustion sources)

*Note: Coverage percentages may vary for different model years/methods*

If coverage is significantly lower than expected, check:
1. All CSV files present in `data\` folder
2. FlowSA version is 2.0.3: `python -c "import flowsa; print(flowsa.__version__)"`
3. Clear cache: `python scripts/clear_flowsa_cache.py --activity-only`
4. Regenerate: `python scripts\enrich_fbs_with_meta.py`

---

## 🛠️ For Developers

### Code Structure (2,364 lines)

Current: Single file `scripts/enrich_fbs_with_meta.py`

**Recommended refactoring for teams:**
```
scripts/
├── enrich_fbs_with_meta.py     # Orchestration (200 lines)
└── modules/
    ├── data_loading.py         # Load FlowSA data
    ├── enrichment_ghgi.py      # EPA GHGI enrichment
    ├── enrichment_sectors.py   # Activity sets & USEEIO
    ├── enrichment_gwp.py       # GWP & contribution
    └── validation.py           # Data quality checks
```

**When to refactor:**
- ✅ Multiple developers
- ✅ Frequent modifications
- ✅ Need automated testing

**When single file is fine:**
- ✅ Single user/researcher
- ✅ Stable pipeline
- ✅ Works well as-is

See **[Technical Reference - Code Architecture](docs/TECHNICAL_REFERENCE.md#code-architecture)** for details.

### Performance Optimization

**Current:** 2-3 minutes for 8,772 rows

**Optimization opportunities:**
- Vectorize row-by-row operations (10-50x speedup)
- Cache regex operations
- Parallel processing for >100K rows

See **[Technical Reference - Performance](docs/TECHNICAL_REFERENCE.md#performance-optimization)**

### Adding New Enrichments

Example: Add "Climate Zone" enrichment

1. Create `data/USEEIO_to_ClimateZone.csv`
2. Add config entry
3. Write loader and enrichment functions
4. Integrate into workflow
5. Validate

See **[Technical Reference - Extending the Pipeline](docs/TECHNICAL_REFERENCE.md#extending-the-pipeline)**

---

## 🔗 Integration with USEEIO

This tool prepares data for supply chain analysis:

1. **Direct emissions** - Scope 1 emission factors by sector
2. **Supply chain intensities** - Scope 3 upstream analysis
3. **Sector mappings** - Link to BEA economic accounts
4. **Impact categories** - Connect to LCA methods

### Related Projects
- **[flowsa](https://github.com/USEPA/flowsa)** - Source data
- **[useeior](https://github.com/USEPA/useeior)** - R package for USEEIO modeling
- **[USEEIO Sectors Disaggregation](https://github.com/DecarbNexus/useeio_sectors_disaggregation/)** - Supply chain analysis

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 📖 Citation

If you use this tool in research, please cite:
- FlowSA library (v2.0.3)
- EPA GHGI report (2022 edition)
- IPCC Fifth Assessment Report

---

## 🤝 Contributing

Contributions welcome! Please:
1. File issues for bugs or feature requests
2. Use GitHub Discussions for questions
3. Submit pull requests for improvements

---

**Last Updated:** November 24, 2025  
**Version:** 1.0.0

## 🗂️ Key Files

### Core Scripts
- `scripts/extract_meta_from_EPA_GHGI.py` — Extracts EPA GHGI table metadata into structured CSV/YAML
- `scripts/enrich_fbs_with_meta.py` — **Main script** - Generates and enriches FlowBySector data

### Configuration  
- `config.py` — **Central configuration file** - Modify this to change models, file paths, and settings

### Outputs (Generated)
- `outputs/EPA_GHGI_meta_sources.csv` — EPA GHGI table metadata  
- `outputs/EPA_GHGI_meta_sources.yaml` — Same metadata in YAML format
- `outputs/GHG_national_XXXX_baseline.xlsx` — Raw FlowBySector data
- `outputs/GHG_national_XXXX_with_meta.xlsx` — **Final enriched data** with IPCC categories

## 🚀 Quick Start

### Prerequisites

**CRITICAL REQUIREMENTS:**
1. **Python 3.9-3.11** (NOT 3.12+) - FlowSA v2.0.3 and pandas 2.0.3 require Python 3.9, 3.10, or 3.11
2. **FlowSA v2.0.3** for reproducibility (matches the reference data used in Supply Chain Emission Factors v1.3.0)

⚠️ **If you have Python 3.12+**: See `PYTHON_VERSION_FIX.md` for how to install Python 3.11

Using the wrong versions will produce different results (fewer rows, missing sources).

### Installation Steps

1. **Clone or download this repository**
   ```bash
   # GitHub URL will be added when repository is published
   git clone https://github.com/DecarbNexus/Flowsa_extract_GHG_sources.git
   cd Flowsa_extract_GHG_sources
   ```

2. **Set up Python environment** (Python 3.9-3.11 required!)
   ```bash
   # Check your Python version first
   python --version
   # Should show Python 3.9.x, 3.10.x, or 3.11.x
   
   # If you have Python 3.12+, see PYTHON_VERSION_FIX.md
   # Create venv with Python 3.11 (recommended)
   py -3.11 -m venv .venv  # Windows with multiple Python versions
   # or: python -m venv .venv  # If Python 3.9-3.11 is your default
   
   # Activate
   .venv\Scripts\activate  # Windows
   # or: source .venv/bin/activate  # Linux/Mac
   ```

3. **Install FlowSA v2.0.3 (CRITICAL - for reproducibility)**
   
   **Option A - Use installation script (recommended):**
   ```bash
   python scripts/install_flowsa_2.0.3.py
   ```
   
   **Option B - Manual installation:**
   ```bash
   pip uninstall flowsa
   pip install git+https://github.com/USEPA/flowsa.git@1cb504c0e7a656ec8d9f2bf00b479df855838c43
   ```

4. **Install remaining dependencies**
   ```bash
   pip install pandas ruamel.yaml pyarrow openpyxl
   ```

# 5. Verify installation
python -c "import flowsa; print('FlowSA version:', flowsa.__version__)"

### Running the Extraction

### Option A: Super Simple (Recommended for Beginners)
```bash
python run_extraction.py
```
This runs everything automatically with helpful output and error checking!

### Option B: Step by Step 

#### 1. Configure Your Model
Edit `config.py` to specify the model you want to process:

```python
# Change these lines to process different models
MODELNAME = "GHG_national_2022_m2"  
FILE_NAME_PARQUET = "GHG_national_2022_m2_v2.0.3_1cb504c.parquet"
MODEL_YEAR = 2022
```

#### 2. Extract EPA GHGI Metadata (First Time Only)
```bash
python scripts/extract_meta_from_EPA_GHGI.py
```

#### 3. Generate Enriched Emission Factors
```bash
python scripts/enrich_fbs_with_meta.py
```

#### 4. Check Your Results
Look in the `outputs/` directory for:
- `GHG_national_XXXX_with_meta.xlsx` — Your final enriched dataset
- Quality validation results in the console output

### ⚠️ Troubleshooting: Data Mismatch Issues

If your generated data doesn't match the reference (wrong row counts, missing sources), it's likely due to **cached FlowByActivity files from different FlowSA versions**:

```bash
# Clear cached FlowByActivity files (most common fix)
python clear_flowsa_cache.py --activity-only

# Then regenerate
python scripts/enrich_fbs_with_meta.py
```

**Why this happens**: FlowSA caches downloaded FlowByActivity files in `C:\Users\<you>\AppData\Local\flowsa\`. If you've used different FlowSA versions, old cached files may be used instead of generating fresh ones with your current version.

**What the script does**:
- `--activity-only`: Only deletes FlowByActivity cache (keeps your downloaded FlowBySector reference files)
- `--dry-run`: Preview what would be deleted
- `--keep-fbs`: Clear everything except FlowBySector files

## 📊 What the Output Contains

The final enriched dataset includes emission factors broken down by:

- **Economic Sectors** (`SectorProducedBy`) - NAICS-like codes (e.g., "221100" = Electric Power)
- **GHG Species** (`Flowable`) - CO2, CH4, N2O, SF6, HFCs, etc.  
- **Emission Amounts** (`FlowAmount`) - Typically kg CO2e per dollar of economic output
- **IPCC Categories** - Energy, Industrial Processes, Agriculture, etc.
- **EPA GHGI Sources** (`MetaSources`) - Which EPA GHGI tables provided the data
- **Attribution Methods** (`AttributionSources`) - How emissions were allocated to sectors

### Sample Output Structure
| Flowable | SectorProducedBy | FlowAmount | IPCC_Category | Subcategory |
|----------|------------------|------------|---------------|-------------|
| CO2      | 221100          | 0.000523   | Energy        | Electric Power |
| CH4      | 111100          | 0.000012   | Agriculture   | Enteric Fermentation |
| N2O      | 325110          | 0.000089   | Industrial Processes | Chemical Production |

## 💡 Common Workflows

### Analyzing Specific Sectors
**Goal:** Analyze electricity sector emissions
```python
import pandas as pd
df = pd.read_excel('outputs/GHG_national_2022_m2_DecarbNexus_industry.xlsx')
electricity = df[df['USEEIO Sector Code'] == '221100']
print(f"Total electricity emissions: {electricity['Emissions (MTCO2e)'].sum():.0f} MTCO2e")
```

### Finding All Methane Sources
**Goal:** See all methane emission sources
```python
import pandas as pd
df = pd.read_excel('outputs/GHG_national_2022_m2_DecarbNexus_industry.xlsx')
methane = df[df['Gas'] == 'Methane'].sort_values('Emissions (MTCO2e)', ascending=False)
print(methane[['USEEIO Sector Name', 'Activity', 'Emissions (MTCO2e)']].head(10))
```

### Analyzing by IPCC Category
**Goal:** Break down emissions by international reporting categories
```python
import pandas as pd
df = pd.read_excel('outputs/GHG_national_2022_m2_DecarbNexus_industry.xlsx')
ipcc_summary = df.groupby('IPCC/UNFCCC Category')['Emissions (MTCO2e)'].sum().sort_values(ascending=False)
print(ipcc_summary)
```

### File Size Expectations
- **Excel (.xlsx)**: ~3.5 MB (full dataset with all enrichments)
- **Parquet (.parquet)**: ~450 KB (compressed, optimized for pandas)
- **CSV (.csv)**: ~4.2 MB (plain text, maximum compatibility)
- **JSON-LD (.jsonld)**: ~12 MB (hierarchical, semantic web ready)
- **Total disk space needed**: ~500 MB (including FlowSA installation and cache)

---

## 🔧 Configuration Options

The `config.py` file contains all settings you can customize:

### Available Models
```python
ALTERNATIVE_MODELS = {
    "GHG_national_2022_m2": "2022 Model - Method 2 (Current default)",
    "GHG_national_2023_m1": "2023 Model - Method 1", 
    "GHG_national_2023_m2": "2023 Model - Method 2",
    # Add more as needed
}
```

To switch models, just update the `MODELNAME` and `FILE_NAME_PARQUET` in `config.py`.

### Key Settings You Can Change
- `FLOWSA_DATA_PATH` - Where your FlowSA data is stored
- `KEEP_COLUMNS` - Which columns to include in the output
- `ENABLE_VALIDATION` - Turn data quality checks on/off
- `VERBOSE_LOGGING` - Control amount of output detail

## 📋 Requirements

- **Python 3.9-3.11** (NOT 3.12+)
- **FlowSA v2.0.3** (installed via `python scripts/install_flowsa_2.0.3.py`)
- **Dependencies**: pandas, pyarrow, ruamel.yaml, openpyxl (see `requirements.txt`)

## 🔍 Understanding the EPA GHGI Metadata

The EPA GHGI metadata extraction creates structured information from EPA's Inventory tables:

| Field | Description | Example |
|-------|-------------|---------|
| `meta_id` | Standardized table ID | `EPA_GHGI_T_3_68` |
| `chapter` | EPA GHGI chapter | `Chapter 3 - Energy` |
| `IPCC_Category` | Top-level emission category | `Energy` |
| `Subcategory` | Specific emission source | `Stationary Combustion` |

## 🔧 Advanced Usage

### Customizing EPA GHGI Categories
You can override default category assignments using a CSV mapping file:

```csv
table_id,label
3-68,Custom Electricity Label
4-55,Custom Industry Label  
```

Then run: `python scripts/extract_meta_from_EPA_GHGI.py --label-map your_overrides.csv`

### Processing Multiple Models
To process different years or methods, update `config.py` and rerun the enrichment script.

## 📁 Integration with USEEIO

This tool prepares data for supply chain analysis workflows:
1. **Direct emissions by sector** - Use for Scope 1 emission factors
2. **Supply chain intensities** - Use for Scope 3 upstream analysis  
3. **Sector mappings** - Link to BEA economic accounts
4. **Impact categories** - Connect to life cycle impact methods

## 🔍 Technical Details

### How EPA GHGI Processing Works

### 1) Deriving `meta_id`
- Table IDs (e.g., `3-68`, `A-9`) are converted to `EPA_GHGI_T_3_68` or `EPA_GHGI_T_A_9` respectively.

### 2) Parsing and cleaning `desc` into `Subcategory`
The script splits the YAML `desc` into a table reference and a description, and then normalizes the description to form `Subcategory`. The normalization removes or adjusts:
- Leading patterns like `CO2 Emissions from `, `CH4 Emissions from `, or comma/and-separated gas lists (e.g., `CO2, CH4, and N2O Emissions from `)
- `Emissions of HFCs, PFCs, SF6, and NF3 from `
- `Emissions of HFCs, PFCs, and CO2 from `
- `Production of `
- Trailing qualifiers like `End-Use Sector`, `by Fuel Type`, and `Consumption by Fuel and Vehicle Type`
- Leading `2023 Adjusted ` and leading `Adjusted ` (any year)
- Normalizes `Stationary Fossil Fuel Combustion` → `Stationary Combustion`
- Collapses `ODS Substitutes (MMT CO2 Eq.) by Sector` → `ODS Substitutes`
- Removes the `Chapter 2` rollup line entirely (i.e., Subcategory is blank for `2-1`)

Note: The original `desc` is preserved in the CSV column `desc` for transparency and traceability.

### 3) Computing `IPCC_Category` from `chapter`
- For chapters in the form `Chapter N - Name`:
  - If `N = 2`: set `IPCC_Category` to blank (intentionally excluded)
  - Otherwise: `IPCC_Category = Name` (the part after the dash)
- Annex special cases:
  - `Annex 2` → `Energy`
  - `Annex 3` → context-based overrides from `desc`:
    - If `desc` contains `HFC Emissions from Transportation Sources` → `Industrial Processes and Product Use`
    - If `desc` contains `Fuel Consumption by Fuel and Vehicle Type` → `Energy`
    - Otherwise: keep the chapter label as-is (e.g., `Annex 3`)

## Customize labels via CSV

You can override the computed `Subcategory` using a simple CSV file (label map):

Accepted columns:
- `table_id,label` (e.g., `3-68,My Custom Label`)
- or `meta_id,label` (e.g., `EPA_GHGI_T_3_68,My Custom Label`)

Also accepted alternative header names: `Subcategory` / `subcategory` as the label column.

Pass your file when running the extractor:

```powershell
# Windows PowerShell
& "C:/Users/YourUser/Path/To/.venv/Scripts/python.exe" `
  "c:/Users/YourUser/Path/To/Flowsa_extract_GHG_sources/extract_meta_from_EPA_GHGI.py" `
  --label-map "c:/Users/YourUser/Path/To/label_overrides.csv"
```

Any row with a matching `meta_id` or `table_id` will replace the `Subcategory` for that table in the outputs.

## Running the extractor

Default inputs/outputs are already configured. You can also specify paths:

```powershell
# Windows PowerShell
& "C:/Users/YourUser/Path/To/.venv/Scripts/python.exe" `
  "c:/Users/YourUser/Path/To/Flowsa_extract_GHG_sources/extract_meta_from_EPA_GHGI.py" `
  --input "C:/.../flowsa/methods/flowbyactivitymethods/EPA_GHGI.yaml" `
  --csv-out "outputs/EPA_GHGI_meta_sources.csv" `
  --yaml-out "outputs/EPA_GHGI_meta_sources.yaml"
```

## Integrating with FBS outputs

See `scripts/enrich_fbs_with_meta.py` (or run `python -m scripts.enrich_fbs_with_meta`) for an example of merging the generated CSV into a FlowBySector parquet export:
- Extract the `meta_id` from `fbs.MetaSources` (portion before the first dot)
- Join with `outputs/EPA_GHGI_meta_sources.csv` on `meta_id`
- Append the columns (e.g., `IPCC_Category`, `Subcategory`, `desc`)
- Export the enriched file (e.g., `outputs/GHG_national_2023_m2_with_meta.xlsx`)

## Adjusting the rules programmatically

If you want to change the cleaning behavior globally, edit the `CUSTOM_DESC_TRANSFORMS` list in `scripts/extract_meta_from_EPA_GHGI.py` (regular expressions applied in order). That’s useful for adding new phrases or adjusting terminology.

---

Questions or ideas for new mappings (e.g., more Annex patterns)? Open an issue or suggest a PR with the rule and the target category.

## 🛠️ Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'flowsa'"**
- Install flowsa: `pip install flowsa>=2.1.0`

**"EPA GHGI YAML not found"**
- Ensure flowsa is properly installed with: `pip show flowsa`
- The script will automatically search common installation locations

**"Metadata file not found"**  
- Run `python scripts/extract_meta_from_EPA_GHGI.py` first to create the metadata

**"No records with metadata coverage"**
- Check that your FlowSA model generates `MetaSources` columns
- Verify the EPA GHGI metadata extraction completed successfully

### Getting Help
1. Check the console output for detailed error messages
2. Review the data validation results for quality issues  
3. Ensure all files in `outputs/` directory were created successfully

## 🔗 Related Projects

This tool integrates with the broader USEEIO ecosystem:

- **[flowsa](https://github.com/USEPA/flowsa)** — Source data and FlowBySector generation
- **[useeior](https://github.com/USEPA/useeior)** — R package for USEEIO modeling  
- **[USEEIO Sectors Disaggregation](https://github.com/DecarbNexus/useeio_sectors_disaggregation/)** — Supply chain analysis (Damien's other repo)

### Typical Workflow
1. **Supply chain factors** → Sector-level Scope 3 emissions (R/USEEIO)
2. **This tool** → Detailed GHG source breakdown (Python/FlowSA)  
3. **Combined analysis** → Complete supply chain emission factors by source

## 📄 License

MIT License - See `LICENSE` file for details.
