# USEEIO GHG Sources Disaggregation

This repository provides a reproducible workflow to disaggregate USEEIO sector emissions into their underlying greenhouse gas (GHG) sources. It enriches EPA's greenhouse gas inventory (GHGI) data with detailed metadata, breaking down each sector's emissions by:

- **GHG Sources**: Activity categories (combustion, processes, fugitives), subcategories, and specific activities
- **Greenhouse Gases**: CO2, CH4, N2O, HFCs, PFCs, SF6, NF3, and other fluorinated gases
- **Fuel Types**: Natural gas, coal, petroleum products, etc. (when applicable)
- **IPCC Categories**: Energy, Industrial Processes, Agriculture, Waste, etc.

The main outputs are Excel workbooks, CSVs, Parquet files, and JSON-LD with absolute emissions (kg, kgCO2e, MTCO2e) and relative contributions by source.

## Just here for the data? (no coding required)

### Interactive visual

- Try the interactive sunburst visualization: https://decarbnexus.github.io/Flowsa_extract_GHG_sources/
- Pick a sector and explore Activity Categories → Subcategories → GHG Sources → Gases using Relative Contribution values

### Data tables

Download the latest files from the `outputs/` folder:

- **Excel** (all-in-one workbook): `outputs/industry/GHG_national_2022_m2_DecarbNexus_industry.xlsx`
- **CSV** (flat tables): `outputs/industry/`
  - Main emissions: `GHG_national_2022_m2_DecarbNexus_industry.csv`
  - Baseline FlowBySector: `GHG_national_2022_m2_DecarbNexus_industry_baseline.csv`
- **Parquet** (columnar, data science): `outputs/industry/GHG_national_2022_m2_DecarbNexus_industry.parquet`
- **JSON** (hierarchical): `outputs/industry/GHG_national_2022_m2_DecarbNexus_industry_sunburst.json`
- **JSON-LD** (RDF-ready): `outputs/industry/GHG_national_2022_m2_DecarbNexus_industry.jsonld`

Open Excel files in your spreadsheet tool or explore the enriched data with full GHG source metadata.

#### Format guide

- **Excel/CSV**: Flat tables, best for spreadsheet users and simple imports
- **Parquet**: Snappy-compressed columnar format; optimized for pandas, Polars, DuckDB, Apache Spark. ~10× faster reads than CSV
- **JSON**: Nested hierarchy (sector > category > gas); ideal for web APIs, JavaScript/Python data science pipelines
- **JSON-LD**: RDF-ready with `@context` vocabulary; can be ingested into triple stores (Apache Jena, RDF4J) or converted to Turtle/N-Triples for knowledge graphs

What's inside (high level):
- Emissions by sector show how each USEEIO sector's emissions break down by GHG source, activity, and gas
- "Absolute" columns are emissions in kg, kgCO2e, or MTCO2e for the specified model year (typically 2022)
- "Relative contribution" shows the percentage split across all GHG sources for a given sector (sums to 100%)
- "Emissions Intensity" shows kgCO2e per USD of sector output for the specified IO year
- The baseline CSV provides the original FlowBySector data for quality checks

### Use cases

This dataset helps you:
- Identify emission hotspots by GHG source within each economic sector
- Separate combustion vs. process vs. fugitive emissions for better targeting
- Connect sector-level emissions to specific activities (e.g., "Natural Gas Combustion" vs "Aluminum Production")
- Map emissions to IPCC categories for international reporting
- Calculate emissions intensities (kgCO2e per USD of economic output)
- Conduct hybrid EEIO accounting under the GHG Protocol

## Quick start (to reproduce the data)

1) Install Python (≥ 3.9, ≤ 3.11) and ensure pip is available. **NOT Python 3.12+** (FlowSA v2.0.3 requires Python 3.9-3.11)
2) Clone or download this repository
3) Edit `config.py` (see below) if you want to change the model year or configuration options
4) Run the analysis:
   - Option A – script (recommended):
     ```bash
     python scripts/run_extraction.py
     ```
     This runs the full pipeline end-to-end, writing Excel/CSVs to `outputs/`
   - Option B – interactive: run the main enrichment script directly:
     ```bash
     python scripts/enrich_fbs_with_meta.py
     ```

5) Optional: First-time setup requires extracting EPA GHGI metadata:
   ```bash
   python scripts/extract_meta_from_EPA_GHGI.py
   ```
   (The `run_extraction.py` script handles this automatically)

Artifacts will be saved under `outputs/industry/` and can be committed to the repo so non-technical users can download them directly.

## Requirements

This workflow installs packages on first run. At minimum, you'll need:

- Internet access (to download FlowSA data and install packages)
- Python 3.9-3.11 (NOT 3.12+) for FlowSA v2.0.3 compatibility
- Python packages: pandas, ruamel.yaml, pyarrow, openpyxl, flowsa
- FlowSA v2.0.3 (install via: `python scripts/install_flowsa_2.0.3.py`)

The scripts will download EPA GHGI data from FlowSA's AWS server on first run (~500 MB cached data).

## Configuration (`config.py`)

Example in `config.py`:

```python
MODELNAME = "GHG_national_2022_m2_DecarbNexus"
MODEL_YEAR = 2022
FILE_NAME_PARQUET = "GHG_national_2022_m2_v2.0.3_1cb504c.parquet"

# Export options
EXPORT_INDUSTRY = True   # Export industry/sector-based outputs
EXPORT_COMMODITY = True  # Export commodity-based outputs (requires additional data)
INCLUDE_BASELINE_TAB = True  # Include original FlowBySector as "Baseline" tab in Excel
EXPORT_BASELINE_CSV = True   # Export baseline as separate CSV

# Quality control
EXCLUDE_QC_COLUMNS = False  # Set to True to exclude QC columns from final output
```

- `MODELNAME`: FlowSA model to process (e.g., "GHG_national_2022_m2_DecarbNexus")
- `MODEL_YEAR`: Year for emissions intensity column naming
- `EXPORT_INDUSTRY`: Whether to export industry/sector-based perspective
- `EXPORT_COMMODITY`: Whether to export commodity-based perspective (requires Use and Make tables)
- `INCLUDE_BASELINE_TAB`: Whether to include baseline FlowBySector data in Excel output
- `EXPORT_BASELINE_CSV`: Whether to export baseline as separate CSV file

## Project structure

- `scripts/enrich_fbs_with_meta.py` – Main enrichment script; loads FlowBySector data, applies enrichments, and exports outputs
- `scripts/extract_meta_from_EPA_GHGI.py` – Extracts EPA GHGI table metadata from FlowSA YAML
- `scripts/run_extraction.py` – Run the full pipeline (extract metadata + enrich data)
- `scripts/clear_flowsa_cache.py` – Clear cached FlowByActivity files if data mismatch occurs
- `scripts/install_flowsa_2.0.3.py` – Install the correct FlowSA version for reproducibility
- `config.py` – User configuration (model, year, export options). Edit this
- `terminology.py` – Terminology and column mapping definitions
- `data/` – Lookup tables for fuel types, sector classifications, GWP factors, etc.
- `outputs/industry/` – Generated outputs (Excel/CSV/Parquet/JSON) ready for end users
- `outputs/commodity/` – Commodity-form outputs (if enabled and data available)
- `local/` – Your scratch area; ignored by Git

## How to use the outputs (practical guide)

1) Open the Excel file in `outputs/industry/`
2) Explore the enriched data with columns like:
   - `USEEIO Sector Name`: Human-readable sector name (e.g., "Oilseed farming")
   - `Activity Category`: High-level GHG source type (e.g., "Stationary Combustion")
   - `Activity`: Specific emission source (e.g., "Natural Gas Combustion")
   - `Gas`: Greenhouse gas species (e.g., "Carbon dioxide", "Methane")
   - `Emissions (MTCO2e)`: Emissions in metric tons CO2 equivalent
   - `Contribution to USEEIO Sector's Scope 1 (%)`: Percentage of sector's total emissions
3) Use "Relative Contribution" to disaggregate your sector emissions: multiply your sector's total emissions by the "Contribution to USEEIO Sector's Scope 1 (%)" values to identify the largest emission sources
4) Use the "Activity Category" field to distinguish combustion vs. process vs. fugitive emissions
5) Use the "IPCC/UNFCCC Category" field for international reporting categories
6) Check the "Baseline" tab (or baseline CSV) for the original FlowBySector data used as input

Deeper dive (optional columns):
- `Fuel Consumed`: Type of fuel (when applicable)
- `AR5-100 GWP`: IPCC AR5 100-year Global Warming Potential
- `US GHGI Table ID`: EPA GHGI source table
- `Attribution Sources`: How emissions were allocated to sectors

Additional reading and context:
- EPA's Supply Chain Emission Factors: https://www.epa.gov/climateleadership/supply-chain-emission-factors
- FlowSA documentation: https://github.com/USEPA/flowsa
- EPA GHGI: https://www.epa.gov/ghgemissions/inventory-us-greenhouse-gas-emissions-and-sinks

## Limitations & planned development

1) **FlowSA version dependency**
   - This workflow requires FlowSA v2.0.3 for reproducibility (matches Supply Chain Emission Factors v1.3.0)
   - Using different FlowSA versions may produce different results (different row counts, missing sources)
   - Cached FlowByActivity files from other versions can cause data mismatches. Run `python scripts/clear_flowsa_cache.py --activity-only` to fix

2) **Model scope and data availability**
   - Coverage varies by enrichment layer (97.6% for EPA GHGI metadata, 84.4% for PrimaryActivity, 28.3% for fuel types)
   - Some enrichment layers only apply to specific emission types (e.g., fuel extraction only for combustion sources)
   - Commodity-form transformation requires additional input-output data (Use and Make tables)

3) **Sector mapping differences**
   - NAICS-to-USEEIO mapping uses the crosswalk from Supply Chain Emission Factors
   - Some sectors may not have direct USEEIO equivalents
   - Sector names come from USEEIO sector classification (99.4% coverage)

4) **Planned features**
   - Modular code structure for easier maintenance and testing (see `docs/REFACTORING_PLAN.md`)
   - Additional visualization options
   - Support for custom aggregation hierarchies

Advanced users can extend the enrichment pipeline by modifying `scripts/enrich_fbs_with_meta.py` or adding new lookup tables in `data/`.

We welcome feedback on which features to prioritize for future releases. Please open a thread in the repository's Discussions to share your thoughts on what would be most useful.

## Beginner setup: getting Python running (no prior coding experience)

Windows (recommended simplest path):
1) Install Python 3.11: https://www.python.org/downloads/ (NOT 3.12+)
   - During installation, check "Add Python to PATH"
2) Download/clone this repository
3) Open PowerShell or Command Prompt in the repository folder
4) Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
5) Install FlowSA v2.0.3:
   ```bash
   python scripts/install_flowsa_2.0.3.py
   ```
6) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
7) Run the pipeline:
   ```bash
   python scripts/run_extraction.py
   ```

macOS/Linux:
1) Install Python 3.11: https://www.python.org/downloads/
2) Open Terminal in the repository folder
3) Create a virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```
4) Install FlowSA v2.0.3:
   ```bash
   python scripts/install_flowsa_2.0.3.py
   ```
5) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6) Run the pipeline:
   ```bash
   python scripts/run_extraction.py
   ```

If you don't want to install anything, you can still download the pre-built files directly from the `outputs/` folder on GitHub.

## Troubleshooting

- **Data mismatch (wrong row counts)**: Clear cached FlowByActivity files: `python scripts/clear_flowsa_cache.py --activity-only` then re-run
- **ModuleNotFoundError: No module named 'flowsa'**: Install FlowSA: `python scripts/install_flowsa_2.0.3.py`
- **Permission error saving Excel**: Close the Excel file and run again
- **Wrong Python version**: See `docs/PYTHON_VERSION_FIX.md` for how to install Python 3.11
- **Network/timeout errors**: Check connectivity and re-run (FlowSA downloads data from AWS)
- **Package install issues**: Ensure pip is up to date: `python -m pip install --upgrade pip`

## Feedback, questions, and feature requests

We're learning with you. Please use the repository's Discussions tab to ask questions, request features, or share how you're using the data.

Peer review status: We aim to have this workflow and its outputs peer-reviewed over the next few months. If you're interested in participating in the review or testing the methods on your data, please open a Discussion or contact us via the repository.

## License

- Code: MIT License. See `LICENSE`
- Data (files under `outputs/` and data attached to GitHub releases): CC BY 4.0. See https://creativecommons.org/licenses/by/4.0/

## Credits and acknowledgement

Huge thanks to the USEPA teams whose work powers this project:
- FlowSA: https://github.com/USEPA/flowsa
- Supply Chain Emission Factors: https://github.com/USEPA/supply-chain-factors
- USEEIO: https://github.com/USEPA/useeior

Project by Damien Lieber @ [DecarbNexus LLC](https://decarbnexus.com)

## Pair this with sector disaggregation

This project focuses on disaggregating sector emissions into GHG sources. You can combine it with a companion workflow that disaggregates Scope 3 emissions by USEEIO sectors and tiers:

- Companion repository: https://github.com/DecarbNexus/useeio_sectors_disaggregation
- Data foundation: Both workflows leverage USEPA's data ecosystem (FlowSA, USEEIO, Supply Chain Emission Factors)
- Pairing the two lets you go from "which sectors contribute to my Scope 3?" to "which GHG sources within those sectors?"

When used together, you can organize Scope 3 in the intuitive language of Scope 1 & 2 - by sector, tier, and source.

**Last Updated:** November 24, 2025  
**Repository:** https://github.com/DecarbNexus/useeio_ghg_sources_disaggregation
