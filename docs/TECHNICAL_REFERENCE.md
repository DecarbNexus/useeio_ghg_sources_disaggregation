# FlowSA GHG Enrichment - Technical Reference

**Developer documentation for the enrichment pipeline**

---

## Table of Contents

- [Code Architecture](#code-architecture)
- [Function Reference](#function-reference)
- [Enrichment Algorithms](#enrichment-algorithms)
- [Data Structures](#data-structures)
- [Testing & Validation](#testing--validation)
- [Performance Optimization](#performance-optimization)
- [Extending the Pipeline](#extending-the-pipeline)

---

## Code Architecture

### File Organization

```
Flowsa_extract_GHG_sources/
├── config.py                  # Central configuration
├── scripts/
│   └── enrich_fbs_with_meta.py   # Main enrichment pipeline (2,364 lines)
├── data/                      # Lookup tables (CSV/Parquet)
│   ├── ListOfFossilFuelsByTable.csv
│   ├── ListOfFossilFuelsByTerm.csv
│   ├── ListOfActivitySets.csv
│   ├── NAICS_to_USEEIO_crosswalk.csv
│   ├── MetaSource_to_GHGSourceCategory_mapping.csv
│   ├── flowable_categorization.csv
│   └── IPCC_v1.1.1_27ba917.parquet
├── outputs/                   # Generated files
├── local/                     # Verification scripts
└── docs/                      # Documentation

```

### Module Structure (Current: Single File)

The `enrich_fbs_with_meta.py` script follows a linear pipeline pattern:

1. **Setup (Lines 1-150)**: Imports, version checking
2. **Utility Functions (Lines 150-400)**: Data loading, filtering
3. **Enrichment Functions (Lines 400-1200)**: Individual enrichment layers
4. **Main Workflow (Lines 1900-2300)**: Orchestration logic
5. **Entry Point (Lines 2300+)**: Command-line execution

### Recommended Refactoring

For team environments or extensive customization, consider modularizing:

```python
# scripts/enrich_fbs_with_meta.py (orchestration only)
from modules.data_loading import load_fbs_data, load_all_lookups
from modules.enrichment_ghgi import enrich_with_metadata, enrich_with_primary_activities
from modules.enrichment_gwp import enrich_with_ar5_100_gwp, calculate_contribution
from modules.output import filter_columns, save_outputs

def main():
    # Step 1-5: Load data
    fbs_data = load_fbs_data(config.MODELNAME)
    lookups = load_all_lookups()
    
    # Step 6-11: Enrich
    enriched = fbs_data
    enriched = enrich_with_metadata(enriched, lookups['ghgi'])
    enriched = enrich_with_primary_activities(enriched, lookups['yaml'])
    # ... etc
    
    # Step 12-13: Output
    save_outputs(enriched, config_dict)
```

**Benefits:**
- Easier unit testing
- Parallel development
- Code reuse across models
- Clearer dependencies

**Trade-offs:**
- More files to navigate
- Import management
- Overhead for single-user projects

---

## Function Reference

### Data Loading Functions

#### `load_generated_fbs_data(modelname, output_dir)`
Loads pre-generated FlowBySector data from FlowSA cache.

**Parameters:**
- `modelname` (str): Model identifier (e.g., "GHG_national_2022_m2_DecarbNexus")
- `output_dir` (str): Backup directory to check

**Returns:**
- `pandas.DataFrame`: FlowBySector data (8,772 rows × 30 columns)

**Raises:**
- `FileNotFoundError`: If model not found in cache or backup

**Example:**
```python
fbs = load_generated_fbs_data("GHG_national_2022_m2_DecarbNexus", "outputs")
# Returns DataFrame with columns: Flowable, FlowAmount, FlowUUID, SectorProducedBy, ...
```

#### `load_metadata_mapping(mapping_csv_path)`
Loads EPA GHGI metadata table mapping.

**Parameters:**
- `mapping_csv_path` (str): Path to EPA_GHGI_meta_sources.csv

**Returns:**
- `dict`: {table_id: {chapter, desc, IPCC_Category, Subcategory}}

**Example:**
```python
meta_map = load_metadata_mapping("outputs/EPA_GHGI_meta_sources.csv")
# meta_map["EPA_GHGI_T_3_8"] = {
#     "chapter": "Chapter 3",
#     "table_id": "EPA_GHGI_T_3_8",
#     "desc": "CO2 Emissions from Stationary Combustion",
#     "IPCC_Category": "1A - Fuel Combustion Activities",
#     "Subcategory": "Stationary Combustion"
# }
```

### Enrichment Functions

#### `enrich_with_metadata(fbs_data, meta_map)`
Enriches FlowBySector data with EPA GHGI metadata.

**Algorithm:**
1. Extract EPA GHGI table reference from `MetaSources` column
2. Use regex pattern: `EPA_GHGI_T_\d+_\d+(?:_.*)?`
3. Strip activity set suffix (e.g., `.direct_gasoline`)
4. Look up in metadata dictionary
5. Add columns: chapter, table_id, desc, IPCC_Category, Subcategory

**Parameters:**
- `fbs_data` (DataFrame): Input FlowBySector data
- `meta_map` (dict): Metadata lookup dictionary

**Returns:**
- `DataFrame`: Enhanced data with 5 new columns

**Coverage:** 97.6% (8,562/8,772 records)

**Example:**
```python
# Input row:
# MetaSources = "EPA_GHGI_T_3_8.residential"

enriched = enrich_with_metadata(fbs_data, meta_map)

# Output adds:
# chapter = "Chapter 3"
# table_id = "EPA_GHGI_T_3_8"
# desc = "CO2 Emissions from Stationary Combustion"
# IPCC_Category = "1A - Fuel Combustion Activities"
# Subcategory = "Stationary Combustion"
```

#### `enrich_with_ar5_100_gwp(fbs_data, uuid_to_gwp_dict)`
Enriches with IPCC AR5-100 Global Warming Potentials and calculates CO2e emissions.

**Algorithm:**
```python
for each row:
    if Unit == "kg CO2e":
        GWP = 1.0  # Already in CO2 equivalent
        MTCO2e = FlowAmount / 1000
    else:  # Unit == "kg"
        GWP = lookup(FlowUUID in uuid_to_gwp_dict)
        MTCO2e = (FlowAmount × GWP) / 1000
```

**Parameters:**
- `fbs_data` (DataFrame): Input data with FlowUUID, FlowAmount, Unit columns
- `uuid_to_gwp_dict` (dict): {FlowUUID: GWP factor}

**Returns:**
- `DataFrame`: Enhanced with AR5-100 GWP and Emissions (MTCO2e) columns

**Coverage:** 100% (8,772/8,772 records)

**Special Cases:**
- `FlowUUID = "n.a."`: For aggregated gases like "HFCs and PFCs, unspecified"
  - Assumes already in CO2e (GWP = 1.0)
- Missing UUID: Logs warning but continues

**Example:**
```python
# Input row 1:
# Flowable = "Methane"
# FlowUUID = "aab83476-ec6c-3742-af85-15d320b7ce80"
# FlowAmount = 1000 (kg)
# Unit = "kg"

enriched = enrich_with_ar5_100_gwp(fbs_data, gwp_dict)

# Output adds:
# AR5-100 GWP = 28
# Emissions (MTCO2e) = (1000 × 28) / 1000 = 28.0

# Input row 2:
# Flowable = "HFCs and PFCs, unspecified"
# FlowUUID = "n.a."
# FlowAmount = 5000000 (kg CO2e)
# Unit = "kg CO2e"

# Output adds:
# AR5-100 GWP = 1.0
# Emissions (MTCO2e) = 5000000 / 1000 = 5000.0
```

#### `calculate_contribution_by_sector(fbs_data)`
Calculates percentage contribution to USEEIO sector total emissions.

**Algorithm:**
```python
# Step 1: Calculate sector totals
sector_totals = fbs_data.groupby('USEEIO')['Emissions (MTCO2e)'].sum()

# Step 2: Calculate contribution for each record
for each row:
    useeio_sector = row['USEEIO']
    mtco2e = row['Emissions (MTCO2e)']
    sector_total = sector_totals[useeio_sector]
    
    Contribution (%) = (mtco2e / sector_total) × 100
```

**Parameters:**
- `fbs_data` (DataFrame): Input with USEEIO and Emissions (MTCO2e) columns

**Returns:**
- `DataFrame`: Enhanced with Contribution (%) column

**Properties:**
- Contributions within a sector sum to 100%
- Min: 0.000000% (negligible sources)
- Max: 100.00% (single source sectors)
- Mean: 4.38%
- Median: 0.07%

**Example:**
```python
# Sector 311111 (Food manufacturing) has 14 records:
# Record 1: 773,666.61 MTCO2e
# Record 2: 15,370.07 MTCO2e
# ... 12 more records
# Sector total: 852,473.78 MTCO2e

enriched = calculate_contribution_by_sector(fbs_data)

# Record 1 Contribution (%) = (773,666.61 / 852,473.78) × 100 = 90.76%
# Record 2 Contribution (%) = (15,370.07 / 852,473.78) × 100 = 1.80%
# ... etc
# Sum = 100.00%
```

### Utility Functions

#### `filter_columns(df, keep_cols, exclude_qc=False, qc_cols=None)`
Filters DataFrame to specified columns, optionally excluding QC columns.

**Parameters:**
- `df` (DataFrame): Input data
- `keep_cols` (list): Columns to retain
- `exclude_qc` (bool): Whether to exclude quality control columns
- `qc_cols` (list): QC columns to exclude if exclude_qc=True

**Returns:**
- `DataFrame`: Filtered data

**Example:**
```python
# With QC columns (default)
filtered = filter_columns(df, config.KEEP_COLUMNS)
# Returns 23 columns

# Without QC columns (for final analysis)
filtered = filter_columns(
    df, 
    config.KEEP_COLUMNS,
    exclude_qc=True,
    qc_cols=config.QC_ONLY_COLUMNS
)
# Returns 16 columns (excludes FlowUUID, SectorProducedBy, etc.)
```

---

## Enrichment Algorithms

### Hierarchical Matching (GHG Source Categories)

Many enrichments use a fallback strategy to maximize coverage:

```python
def enrich_with_ghg_source_categories(fbs_data, mapping_df):
    for each row:
        meta_source = row['MetaSources']
        activity = row['ActivityProducedBy']
        
        # Step 1: Try exact match
        match = mapping_df[
            (mapping_df['MetaSources'] == meta_source) &
            (mapping_df['ActivityProducedBy'] == activity)
        ]
        
        if match found:
            return match
        
        # Step 2: Strip activity set suffix and retry
        base_source = meta_source.split('.')[0]  # EPA_GHGI_T_A_89.mobile_ac → EPA_GHGI_T_A_89
        
        match = mapping_df[
            (mapping_df['MetaSources'] == base_source) &
            (mapping_df['ActivityProducedBy'] == activity)
        ]
        
        if match found:
            return match
        
        # Step 3: Try with empty activity
        match = mapping_df[
            (mapping_df['MetaSources'] == meta_source) &
            (mapping_df['ActivityProducedBy'].isna() | mapping_df['ActivityProducedBy'] == '')
        ]
        
        return match or None
```

**Rationale:**
- EPA GHGI tables have multiple activity sets (e.g., `.mobile_ac`, `.stationary`)
- Lookup CSVs may only have base table references
- This achieves 100% coverage vs 99.4% with exact matching only

### YAML Anchor Dereferencing

FlowSA method YAMLs use YAML anchors for code reuse. We dereference these:

```python
def extract_primary_activities_mapping(yaml_content):
    # Step 1: Find anchor definitions
    anchors = {}
    for match in re.finditer(r'&(\w+)', yaml_content):
        anchor_name = match.group(1)
        # Extract activities defined at this anchor
        anchors[anchor_name] = extract_activities_at_position(match.start())
    
    # Step 2: Find anchor references
    for match in re.finditer(r'\*(\w+)', yaml_content):
        anchor_name = match.group(1)
        if anchor_name in anchors:
            # Copy activities from anchor definition to reference location
            copy_activities(from=anchors[anchor_name], to=match.start())
    
    return mapping
```

**Example:**
```yaml
# Anchor definition
EPA_GHGI_T_3_73: &natgas
  PrimaryActivity:
    - Distribution
    - Post-Meter
    - Exploration
    ...

# Anchor reference
EPA_GHGI_T_3_75: *natgas  # Copies all activities from T_3_73
```

**Result:**
```python
mapping["EPA_GHGI_T_3_75"] = "Distribution | Post-Meter | Exploration | ..."
```

### Semiconductors Special Case

```python
def enrich_with_primary_activities(fbs_data, primary_activity_mapping):
    for each row:
        attribution = row['AttributionSources']
        activity = row['ActivityProducedBy']
        meta_source = row['MetaSources']
        
        # Special case: Semiconductors with direct attribution
        if attribution == 'direct' and activity.lower() == 'semiconductors':
            # Override: Use YAML mapping instead of direct ActivityProducedBy
            # Reason: YAML has richer "Electronics Industry | Semiconductors | PV | MEMS"
            # vs ActivityProducedBy which only says "Semiconductors"
            if meta_source in primary_activity_mapping:
                PrimaryActivity = primary_activity_mapping[meta_source]
        
        # Normal direct attribution
        elif attribution == 'direct':
            PrimaryActivity = activity
        
        # YAML lookup
        else:
            PrimaryActivity = primary_activity_mapping.get(meta_source)
```

---

## Data Structures

### FlowBySector Schema (Input)

```python
{
    'Flowable': str,              # "Carbon dioxide", "Methane", etc.
    'Class': str,                 # "Chemicals", "Energy", etc.
    'SectorProducedBy': str,      # NAICS code (e.g., "311111")
    'SectorConsumedBy': str,      # Usually empty for emissions
    'FlowAmount': float,          # Emission amount (kg or kg CO2e)
    'Unit': str,                  # "kg" or "kg CO2e"
    'FlowType': str,              # "ELEMENTARY_FLOW"
    'FlowUUID': str,              # UUID or "n.a."
    'Year': int,                  # 2022
    'MetaSources': str,           # "EPA_GHGI_T_3_8.residential"
    'ActivityProducedBy': str,    # Activity code or description
    'AttributionSources': str,    # "direct", "industry_allocation", etc.
    'Context': str,               # "emission/air", etc.
    # ... 18 more columns
}
```

### Enriched Output Schema (23 columns)

```python
{
    # Original columns
    'Flowable': str,
    'FlowUUID': str,              # QC only
    'SectorProducedBy': str,      # QC only
    'FlowAmount': float,          # QC only
    'Unit': str,                  # QC only
    'MetaSources': str,           # QC only
    'ActivityProducedBy': str,    # QC only
    'AttributionSources': str,
    
    # Enriched columns
    'Gas Category': str,          # "Carbon dioxide", "Methane", etc.
    'USEEIO': str,                # "311111", "325110", etc.
    'AR5-100 GWP': float,         # QC only: 1, 28, 265, 1300, etc.
    'Emissions (MTCO2e)': float,  # Metric tons CO2 equivalent
    'Contribution (%)': float,    # 0.0 - 100.0
    'Activity': str,              # "Fuel Oil Residential | Coal Residential | ..."
    'Activity Type': str,         # "Stationary Combustion", "Mobile Sources", etc.
    'Fuel Consumed': str,         # "Coal", "Natural Gas", "Petroleum", etc.
    'IPCC/UNFCCC Category': str,  # "Energy", "Industrial Processes", etc.
    'Activity Category': str,     # "Fossil Fuels Combustion", "Process & Fugitive", etc.
    
    # EPA GHGI metadata
    'chapter': str,               # "Chapter 3"
    'table_id': str,              # "EPA_GHGI_T_3_8"
    'desc': str,                  # "CO2 Emissions from Stationary Combustion"
    'IPCC_Category': str,         # "1A - Fuel Combustion Activities"
    'Subcategory': str,           # "Stationary Combustion"
}
```

### Lookup Table Schemas

**NAICS_to_USEEIO_crosswalk.csv:**
```csv
NAICS,USEEIO
111110,111110
111120,111120
...
```

**MetaSource_to_GHGSourceCategory_mapping.csv:**
```csv
MetaSources,ActivityProducedBy,IPCC/UNFCCC Category,Activity Category
EPA_GHGI_T_2_1,electric_power,Energy,Fossil Fuels Combustion
EPA_GHGI_T_4_109,,Industrial Processes and Product Use,Process & Fugitive Gases
...
```

**flowable_categorization.csv:**
```csv
Flowable,Gas Category
Carbon dioxide,Carbon dioxide
Methane,Methane
HFC-134a,Fluorinated gases (F-Gases)
...
```

---

## Testing & Validation

### Verification Scripts

Located in `local/` directory:

**1. `verify_gwp.py`**
Validates GWP and MTCO2e calculations:
```bash
python local/verify_gwp.py
```
Checks:
- Calculation accuracy (FlowAmount × GWP / 1000)
- Unit handling (kg vs kg CO2e)
- Coverage statistics

**2. `verify_contribution.py`**
Validates contribution percentages:
```bash
python local/verify_contribution.py
```
Checks:
- Sector totals sum to 100%
- No negative contributions
- Distribution statistics

**3. `verify_gas_category.py`**
Validates gas categorization:
```bash
python local/verify_gas_category.py
```
Checks:
- All flowables categorized
- Category distribution
- MTCO2e totals by category

### Unit Tests (Recommended)

```python
# tests/test_enrichment.py
import unittest
import pandas as pd
from scripts.enrich_fbs_with_meta import enrich_with_ar5_100_gwp

class TestGWPEnrichment(unittest.TestCase):
    def setUp(self):
        self.test_data = pd.DataFrame({
            'Flowable': ['Carbon dioxide', 'Methane', 'HFCs and PFCs, unspecified'],
            'FlowUUID': ['b6f010fb-a764-3063-af2d-bcb8309a97b7', 
                         'aab83476-ec6c-3742-af85-15d320b7ce80',
                         'n.a.'],
            'FlowAmount': [1000.0, 1000.0, 1000.0],
            'Unit': ['kg', 'kg', 'kg CO2e']
        })
        self.gwp_dict = {
            'b6f010fb-a764-3063-af2d-bcb8309a97b7': 1.0,   # CO2
            'aab83476-ec6c-3742-af85-15d320b7ce80': 28.0   # CH4
        }
    
    def test_co2_conversion(self):
        result = enrich_with_ar5_100_gwp(self.test_data, self.gwp_dict)
        self.assertEqual(result.loc[0, 'AR5-100 GWP'], 1.0)
        self.assertEqual(result.loc[0, 'Emissions (MTCO2e)'], 1.0)
    
    def test_methane_conversion(self):
        result = enrich_with_ar5_100_gwp(self.test_data, self.gwp_dict)
        self.assertEqual(result.loc[1, 'AR5-100 GWP'], 28.0)
        self.assertEqual(result.loc[1, 'Emissions (MTCO2e)'], 28.0)
    
    def test_co2e_passthrough(self):
        result = enrich_with_ar5_100_gwp(self.test_data, self.gwp_dict)
        self.assertEqual(result.loc[2, 'AR5-100 GWP'], 1.0)
        self.assertEqual(result.loc[2, 'Emissions (MTCO2e)'], 1.0)
```

### Integration Tests

```python
# tests/test_pipeline.py
def test_full_pipeline():
    """Test complete enrichment pipeline end-to-end"""
    # Load test data (small subset)
    fbs_data = load_test_dataset()  # 100 rows
    
    # Run enrichment
    result = run_enrichment_pipeline(fbs_data)
    
    # Validate
    assert len(result) == 100
    assert 'Emissions (MTCO2e)' in result.columns
    assert result['Emissions (MTCO2e)'].notna().sum() == 100
    assert result.groupby('USEEIO')['Contribution (%)'].sum().round(2).eq(100.0).all()
```

---

## Performance Optimization

### Current Performance

**Baseline (8,772 rows):**
- First run: 5-10 minutes (data downloads)
- Subsequent: 2-3 minutes (cached data)

**Bottlenecks:**
1. Row-by-row iteration in enrichment functions (80% of time)
2. YAML parsing and regex matching (10%)
3. File I/O (10%)

### Optimization Strategies

**1. Vectorized Operations**

Current (slow):
```python
for idx, row in enriched_data.iterrows():
    useeio_sector = row.get('USEEIO', '')
    mtco2e = row.get('Emissions (MTCO2e)', 0)
    sector_total = sector_totals[useeio_sector]
    enriched_data.at[idx, 'Contribution (%)'] = (mtco2e / sector_total) * 100
```

Optimized (fast):
```python
# Calculate once using vectorized operations
enriched_data['Contribution (%)'] = enriched_data.apply(
    lambda row: (row['Emissions (MTCO2e)'] / sector_totals[row['USEEIO']]) * 100
    if row['USEEIO'] in sector_totals else None,
    axis=1
)
```

**Even better (pure vectorization):**
```python
# Join sector totals as a column
enriched_data = enriched_data.merge(
    sector_totals.rename('Sector Total'),
    left_on='USEEIO',
    right_index=True,
    how='left'
)
# Vectorized calculation
enriched_data['Contribution (%)'] = (
    enriched_data['Emissions (MTCO2e)'] / enriched_data['Sector Total']
) * 100
```

**Speedup:** 10-50x for large datasets

**2. Lookup Caching**

```python
# Cache expensive regex operations
_table_id_cache = {}

def extract_table_id(meta_source):
    if meta_source in _table_id_cache:
        return _table_id_cache[meta_source]
    
    match = re.search(r'EPA_GHGI_T_\d+_\d+', meta_source)
    result = match.group(0) if match else None
    _table_id_cache[meta_source] = result
    return result
```

**3. Parallel Processing**

For very large datasets (>100,000 rows):
```python
from multiprocessing import Pool
import numpy as np

def enrich_chunk(chunk_data, gwp_dict):
    return enrich_with_ar5_100_gwp(chunk_data, gwp_dict)

# Split into chunks
chunks = np.array_split(fbs_data, cpu_count())

# Process in parallel
with Pool() as pool:
    results = pool.starmap(enrich_chunk, [(chunk, gwp_dict) for chunk in chunks])

# Combine
enriched_data = pd.concat(results)
```

**Speedup:** 2-4x on multi-core systems

---

## Extending the Pipeline

### Adding a New Enrichment Layer

**Example: Add "Climate Zone" enrichment**

**Step 1: Create lookup data**
```csv
# data/USEEIO_to_ClimateZone.csv
USEEIO,Climate Zone
111110,Temperate
111120,Temperate
221111,Varied
...
```

**Step 2: Add config entry**
```python
# config.py
USEEIO_TO_CLIMATE_ZONE_CSV = "data/USEEIO_to_ClimateZone.csv"

KEEP_COLUMNS = [
    ...
    "Climate Zone",  # Add to column list
    ...
]
```

**Step 3: Create loader function**
```python
# scripts/enrich_fbs_with_meta.py
def load_climate_zone_lookup(csv_path):
    """Load USEEIO to Climate Zone mapping."""
    if not os.path.exists(csv_path):
        print(f"Warning: Climate zone file not found at {csv_path}")
        return {}
    
    try:
        df = pd.read_csv(csv_path)
        useeio_to_zone = dict(zip(df['USEEIO'], df['Climate Zone']))
        print(f"✓ Loaded {len(useeio_to_zone)} climate zone mappings")
        return useeio_to_zone
    except Exception as e:
        print(f"Error loading climate zones: {e}")
        return {}
```

**Step 4: Create enrichment function**
```python
def enrich_with_climate_zone(fbs_data, useeio_to_zone_dict):
    """Enrich FlowBySector data with climate zones."""
    if "USEEIO" not in fbs_data.columns:
        print("Skipping climate zone enrichment - USEEIO column not found")
        return fbs_data.copy()
    
    print("Enriching FlowBySector data with climate zones...")
    
    enriched_data = fbs_data.copy()
    enriched_data['Climate Zone'] = enriched_data['USEEIO'].map(useeio_to_zone_dict)
    
    matched_count = enriched_data['Climate Zone'].notna().sum()
    print(f"✓ Added Climate Zone to {matched_count:,} records")
    
    return enriched_data
```

**Step 5: Integrate into workflow**
```python
# In main() function:

# After Step 4.10: Load lookups
print("\nStep 4.11: Loading climate zone mapping...")
useeio_to_zone_dict = load_climate_zone_lookup(config.USEEIO_TO_CLIMATE_ZONE_CSV)

# After Step 7.11: Enrich data
print("\nStep 7.12: Enriching data with climate zones...")
enriched_data = enrich_with_climate_zone(enriched_data, useeio_to_zone_dict)
```

**Step 6: Validate**
```python
# local/verify_climate_zone.py
import pandas as pd

df = pd.read_excel('outputs/GHG_national_2022_m2_DecarbNexus_with_meta.xlsx')

print('Climate Zone Coverage:')
print(f'Total records: {len(df):,}')
print(f'Records with climate zone: {df["Climate Zone"].notna().sum():,}')
print(f'Coverage: {(df["Climate Zone"].notna().sum() / len(df)) * 100:.1f}%')

print('\n\nDistribution:')
print(df['Climate Zone'].value_counts())
```

### Adding a New Model Year

**Step 1: Update config**
```python
# config.py
ALTERNATIVE_MODELS = {
    ...
    "GHG_national_2024_m2": {
        "parquet_file": "GHG_national_2024_m2_v2.1.0.parquet",
        "description": "2024 GHG National Model - Method 2",
        "year": 2024
    }
}
```

**Step 2: Switch active model**
```python
# config.py
MODELNAME = "GHG_national_2024_m2"
FILE_NAME_PARQUET = "GHG_national_2024_m2_v2.1.0.parquet"
MODEL_YEAR = 2024
```

**Step 3: Update lookup files** (if needed)
- Check if EPA GHGI tables changed
- Update `EPA_GHGI_meta_sources.csv` with new tables
- Verify NAICS codes haven't changed

**Step 4: Run and validate**
```bash
python scripts/enrich_fbs_with_meta.py
```

---

**Last Updated:** November 7, 2025  
**Version:** 1.0.0  
**Maintained by:** [Your Organization]
