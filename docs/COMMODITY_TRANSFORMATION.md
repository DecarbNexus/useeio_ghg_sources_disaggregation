# Industry-to-Commodity Transformation

## Overview

The GHG extraction pipeline now supports transforming industry-form emissions data into commodity-form for USEEIO supply chain modeling. This transformation allocates emissions from producing industries to the commodities (products) they create using Input-Output market share data.

## What Changed

### New Features

1. **Industry Output Normalization** - Emissions are normalized by industry economic output (from `x.csv`) to create emission intensity coefficients (kg emissions per dollar of output)

2. **Commodity Allocation** - Emission intensities are allocated to commodities using the V_n market share matrix (from `V_n.csv`), which shows how each industry's output is distributed across different commodity categories

3. **Dual Output System** - The pipeline now exports **both** forms:
   - **Industry form**: Emissions by producing industry (existing output)
   - **Commodity form**: Emissions by product/commodity (new output with `_commodity` suffix)

### Files Modified

- **`scripts/enrich_fbs_with_meta.py`**: Added transformation functions and updated pipeline

### New Functions

1. **`load_industry_output(csv_path)`** - Loads industry output values (x.csv)
   - Input: Path to x.csv file
   - Output: Dictionary mapping USEEIO sector codes to output in USD

2. **`load_market_share_matrix(csv_path)`** - Loads V_n market share matrix
   - Input: Path to V_n.csv file  
   - Output: DataFrame with industries as rows, commodities as columns

3. **`normalize_emissions_by_output(df, industry_output_dict)`** - Normalizes emissions
   - Divides Emissions (kg) by industry output (USD)
   - Creates emission intensity coefficients (kg/USD)

4. **`transform_to_commodity_form(df_normalized, market_share_matrix, sector_code_to_name)`** - Transforms to commodity form
   - Multiplies intensities by market shares
   - Allocates emissions to commodity codes
   - Aggregates across commodities
   - Recalculates MTCO2e and contribution percentages

5. **`save_outputs(..., commodity_data=None)`** - Updated to export both forms
   - Exports industry form with original filenames
   - Exports commodity form with `_commodity` suffix if provided

## Data Requirements

### Required Files (place in `data/` directory)

1. **`x.csv`** - Industry output in USD
   - Format: 2 columns (sector code with "/US", dollar value)
   - Example:
     ```
     "","value"
     "1111A0/US",38216000000
     "1111B0/US",52183000000
     ```
   - 404 rows (403 industries + header)

2. **`V_n.csv`** - Market share matrix (industry × commodity)
   - Format: Industries as rows, commodities as columns
   - Values: Market shares (0-1, sum to ~1.0 per row)
   - Example:
     ```
     "","1111A0/US","1111B0/US",...
     "1111A0/US",1.00005274,0,0,...
     "1111B0/US",0,0.99996507,0,...
     ```
   - 403 industry rows × 403 commodity columns

## Pipeline Integration

### New Steps (7.14 - 7.16)

**Step 7.14**: Load economic data files
- Loads x.csv and V_n.csv
- Validates data structure
- Strips "/US" suffix from sector codes

**Step 7.15**: Normalize and transform to commodity form
- Normalizes emissions by industry output
- Transforms using V_n market share matrix  
- Creates commodity-form records

**Step 7.16**: Prepare commodity data for export
- Aligns column structure with industry form
- Ensures consistency for dual export

### Processing Flow

```
Industry Emissions (kg)
    ↓
÷ Industry Output (USD) [from x.csv]
    ↓
Emission Intensity (kg/USD)
    ↓
× Market Share (0-1) [from V_n.csv]
    ↓
Commodity Emissions (kg)
    ↓
Aggregate by commodity + dimensions
    ↓
Recalculate MTCO2e & Contribution %
    ↓
Export to all formats
```

## Output Files

### Industry Form (existing filenames)
- `GHG_national_2022_m2_DecarbNexus.xlsx`
- `GHG_national_2022_m2_DecarbNexus.csv`
- `GHG_national_2022_m2_DecarbNexus.parquet`
- `GHG_national_2022_m2_DecarbNexus.jsonld`
- `GHG_national_2022_m2_DecarbNexus_sunburst.jsonld`

### Commodity Form (new with `_commodity` suffix)
- `GHG_national_2022_m2_DecarbNexus_commodity.xlsx`
- `GHG_national_2022_m2_DecarbNexus_commodity.csv`
- `GHG_national_2022_m2_DecarbNexus_commodity.parquet`
- `GHG_national_2022_m2_DecarbNexus_commodity.jsonld`
- `GHG_national_2022_m2_DecarbNexus_commodity_sunburst.jsonld`

## Usage

### Running the Pipeline

```bash
# Standard run (will automatically include commodity transformation if data files exist)
python scripts/enrich_fbs_with_meta.py
```

### Expected Output

```
================================================================================
INDUSTRY-TO-COMMODITY TRANSFORMATION
================================================================================
Converting industry-form emissions to commodity-form for USEEIO modeling
This enables supply chain analysis by product/commodity rather than by industry
================================================================================

Step 7.14: Loading economic data files...
Loading industry output data from: data/x.csv
✓ Loaded 403 industry output values
  Total output: $25,874,000,000,000
  Min: $38,216,000,000, Max: $2,850,000,000,000

Loading market share matrix from: data/V_n.csv
✓ Loaded V_n matrix: 403 industries × 403 commodities
  ✓ Row sums validated (max deviation: 0.000123)

Step 7.15: Normalizing and transforming to commodity form...
Normalizing emissions by industry output...
✓ Calculated emission intensities for 8,772 records
  Total emissions: 6,123,456,789 kg
  Average intensity: 2.367e-04 kg/USD

Transforming to commodity form using V_n matrix...
  Processing 8,772 records with valid emission intensities
  Progress: 50/384 industries (13.0%)
  Progress: 100/384 industries (26.0%)
  ...
✓ Created 123,456 commodity records
  Aggregating by: USEEIO Sector Code, NAICS Sector Code, GHG Source Category, ...
✓ Aggregated to 9,234 commodity records
  Calculating contribution percentages for commodity form...
✓ Emission totals:
  Industry form: 6,123,456,789 kg
  Commodity form: 6,123,441,023 kg
  Difference: 0.03%

✓ Commodity transformation complete
  Industry form: 8,772 records
  Commodity form: 9,234 records

================================================================================
SAVING OUTPUTS
================================================================================

Industry form:
----------------------------------------
  Excluded 5 QC columns from flat exports
  ✓ Excel: GHG_national_2022_m2_DecarbNexus.xlsx
  ✓ CSV: GHG_national_2022_m2_DecarbNexus.csv
  ✓ Parquet: GHG_national_2022_m2_DecarbNexus.parquet
  ✓ JSON-LD (full): GHG_national_2022_m2_DecarbNexus.jsonld
  ✓ JSON-LD (light): GHG_national_2022_m2_DecarbNexus_sunburst.jsonld

Commodity form:
----------------------------------------
  Excluded 5 QC columns from flat exports
  ✓ Excel: GHG_national_2022_m2_DecarbNexus_commodity.xlsx
  ✓ CSV: GHG_national_2022_m2_DecarbNexus_commodity.csv
  ✓ Parquet: GHG_national_2022_m2_DecarbNexus_commodity.parquet
  ✓ JSON-LD (full): GHG_national_2022_m2_DecarbNexus_commodity.jsonld
  ✓ JSON-LD (light): GHG_national_2022_m2_DecarbNexus_commodity_sunburst.jsonld
```

## Validation

### Data Integrity Checks

The transformation includes several validation steps:

1. **Market Share Validation**
   - Checks that V_n row sums are approximately 1.0
   - Warns if deviation exceeds 1%

2. **Emissions Conservation**
   - Compares total emissions before and after transformation
   - Warns if difference exceeds 1%

3. **Missing Data**
   - Reports any USEEIO codes not found in x.csv
   - Reports any industries not found in V_n.csv

### Expected Differences

- **Record count**: Commodity form may have different number of records due to:
  - Aggregation across multiple industries producing same commodity
  - Splitting of diversified industries across multiple commodities

- **USEEIO codes**: Commodity form uses commodity codes instead of industry codes
  - Industry: "111300/US" (Fruit and nut farming)
  - Commodity: "111300/US" (Fruits and nuts)

- **Contribution %**: Recalculated for commodity-based groupings
  - Industry form: % within producing industry
  - Commodity form: % within commodity category

## Use Cases

### When to Use Industry Form
- Direct emission reporting by sector
- Producer responsibility analysis
- Emission source identification
- Regulatory compliance reporting

### When to Use Commodity Form
- Supply chain emission analysis (USEEIO)
- Product carbon footprinting
- Consumer-based emission accounting
- Life cycle assessment (LCA)
- Embodied emissions in trade

## Troubleshooting

### Transformation Skipped

If you see:
```
⚠ Warning: Industry output file not found: data/x.csv
  Skipping commodity transformation
```

**Solution**: Add x.csv and V_n.csv to the `data/` directory

### Missing USEEIO Codes

If you see warnings about missing codes:
```
⚠ Warning: 42 records have missing industry output values
  Missing USEEIO codes: 520000, 531HSO, 531HST, ...
```

**Impact**: These records will not be included in commodity form transformation

**Solution**: 
- Check if codes are valid USEEIO sector codes
- Verify x.csv contains all required codes
- Update x.csv if codes are legitimate but missing

### Large Emissions Difference

If commodity total differs by >1%:
```
⚠ Warning: Emissions difference exceeds 1% (2.34%)
```

**Possible causes**:
- V_n row sums not equal to 1.0
- Missing industries in V_n matrix
- Rounding errors in large datasets

**Solution**:
- Check V_n matrix validation output
- Verify V_n completeness
- Review aggregation logic

## Technical Details

### Transformation Mathematics

For each industry record with emission E_i (kg):

1. **Normalization**:
   ```
   intensity_i = E_i / x_i
   ```
   where x_i is industry output in USD

2. **Commodity Allocation**:
   ```
   E_c = Σ_i (intensity_i × V_n[i,c] × x_i)
        = Σ_i (E_i × V_n[i,c])
   ```
   where V_n[i,c] is market share of industry i in commodity c

3. **Aggregation**:
   - Group by: commodity code + NAICS + GHG category + activity + gas
   - Sum emissions across all contributing industries

### Memory Considerations

- Transformation creates temporary records for each industry-commodity pair
- Peak memory ~2-3x the size of industry form data
- For large datasets (>100K records), monitor memory usage

### Performance

- Transformation time ~30-60 seconds for typical dataset (8-10K records)
- Scales linearly with number of records
- Progress updates every 50 industries

## References

- USEEIO Documentation: https://www.epa.gov/land-research/us-environmentally-extended-input-output-useeio-technical-content
- Input-Output Analysis: https://en.wikipedia.org/wiki/Input%E2%80%93output_model
- Market Share Matrices: Leontief, W. (1970). "Environmental Repercussions and the Economic Structure: An Input-Output Approach"

## Future Enhancements

Potential improvements for future versions:

1. **Configurable transformation** - Add config flag to enable/disable commodity transformation
2. **Partial transformation** - Support subset of industries/commodities
3. **Alternative matrices** - Support different market share matrices (V vs V_n)
4. **Uncertainty quantification** - Propagate uncertainty through transformation
5. **Visualization** - Compare industry vs commodity distributions
6. **Documentation** - Auto-generate transformation report with diagnostics
