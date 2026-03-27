# Industry-to-Commodity Transformation

## Overview

The pipeline transforms industry-form emissions into commodity-form using the same
formula as useeior's B matrix construction:

$$B_{commodity} = B_{industry} \times V_n$$

where `B_industry` is the flow × industry intensity matrix and `V_n` is the 403×403
market share (make) matrix. The commodity-form result is validated against the
B matrix exported directly from useeior, achieving machine-precision agreement
(max relative error ≈ 7.5 × 10⁻¹³).

### Why Matrix Multiply?

useeior builds its B matrix (the satellite account in commodity form) via a single
matrix multiplication. The previous approach used nested for-loops iterating over
industries and commodities, which was both slower and harder to validate.
By switching to `numpy` matrix multiplication (`intensity_industry @ V_n`), we:

- Match useeior's exact computation
- Enable direct QC/QA comparison against the exported B matrix
- Reduce transformation time from minutes to seconds

## Prerequisites

Before running the Python pipeline, you need the R-exported reference data.
This is a **one-time step** (see [scripts/setup/README.md](../scripts/setup/README.md)):

```bash
Rscript scripts/setup/export_reference_data.R
```

This exports five CSVs to `data/`, including:

| File | Role in Commodity Transform |
|------|-----------|
| `adjusted_output.csv` | CPI-adjusted 2022 industry output in 2017$ — the denominator for emission intensities |
| `B_matrix.csv` | useeior's B matrix (flows × commodities) — the QC/QA validation truth |
| `V_n.csv` | Market share matrix (industries × commodities) — used in the matrix multiply |
| `q.csv` | Commodity output vector — used to convert commodity intensities back to absolute kg |
| `naics_bea_allocation.csv` | NAICS→BEA allocation weights — handles 1:many mappings upstream |

### Why CPI-Adjusted Output?

useeior's "CbS denominator" is **not** the raw industry output. It calls
`adjustOutputbyCPI(2022, 2017, "US", FALSE, model, "Industry")`, which deflates
2022 raw output to 2017 dollars using sector-specific CPI ratios. Using raw output
(e.g., from a simple `x.csv`) produces intensities that don't match the B matrix.
The R export script captures this exact adjusted output.

## Processing Flow

```
FlowBySector emissions (kg)
    │
    │  enrich_with_useeio() expands 1:many NAICS→BEA
    │  using allocation weights from naics_bea_allocation.csv
    ▼
Industry Emissions (kg) by BEA sector
    │
    │  ÷ CPI-adjusted output (USD) [from adjusted_output.csv]
    ▼
Emission Intensity (kg/USD) — "B_industry" rows
    │
    │  Pivot to matrix: flows × industries
    │  Matrix multiply: intensity_industry @ V_n
    ▼
Commodity Intensity (kg/USD) — "B_commodity" rows
    │
    │  × commodity output q_j [from q.csv]
    ▼
Commodity Emissions (kg)
    │
    │  Recalculate kgCO2e, MTCO2e, Contribution %
    ▼
Export industry + commodity forms
    │
    │  Compare commodity intensities against B_matrix.csv
    ▼
QC/QA workbook (outputs/QCQA.xlsx)
```

## Implementation Details

### Module: `scripts/pipeline/transform.py`

#### `normalize_emissions_by_output(df, adjusted_output_dict)`

Divides `Emissions (kg)` by CPI-adjusted industry output for each BEA sector code,
producing an `Emissions Intensity (kg/USD_2017)` column.

- `adjusted_output_dict` comes from `load_adjusted_output()` which reads `data/adjusted_output.csv`
- Records with missing or zero output get `NaN` intensity (logged as warnings)

#### `transform_to_commodity_form(df_normalized, market_share_matrix, commodity_output_dict, sector_code_to_name)`

1. **Aggregate** intensity by (flow dimensions, USEEIO Sector Code)
2. **Pivot** to a matrix: rows = unique flow combinations, columns = BEA industry codes
3. **Align** columns with V_n rows (industries); warn about any missing codes
4. **Matrix multiply**: `intensity_commodity = intensity_industry @ V_n`
5. **Unpivot** back to long form; drop zero-intensity records (< 1e-20)
6. **Recalculate** `Emissions (kg) = intensity × q_j`, then `kgCO2e = kg × GWP`, `MTCO2e = kgCO2e / 1e6`
7. **Contribution %** recalculated per commodity sector

### Module: `scripts/pipeline/loaders.py`

New loaders for the R-exported data:

- `load_adjusted_output()` → dict: `{sector_code: adjusted_USD}`
- `load_naics_bea_allocation()` → dict: `{naics: [(bea_code, weight), ...]}`
- `load_b_matrix()` → DataFrame (flows × commodities)
- `load_market_share_matrix(csv_path)` → DataFrame (industries × commodities)

### Module: `scripts/pipeline/enrichers.py`

`enrich_with_useeio()` now accepts an `allocation_dict` parameter. When a NAICS code
maps to multiple BEA codes, the function expands rows and weights `FlowAmount` by
the allocation fraction (based on relative industry output).

## QC/QA: B Matrix Validation

After the commodity transform, `generate_ghg_dataset.py` compares the computed
commodity intensities against useeior's exported B matrix (`data/B_matrix.csv`):

1. **Comparison** — For each (Gas, Commodity Sector) pair, compute:
   - `python_value`: sum of computed commodity intensities
   - `r_value`: corresponding cell in the B matrix
   - `abs_diff` and `rel_diff`

2. **Flagging** — Pairs with relative difference > 1e-6 are flagged

3. **Output** — `outputs/QCQA.xlsx` with four sheets:
   - **Comparison**: All (Gas, Sector) pairs with both values and differences
   - **Summary**: Counts, max/mean errors, pass/fail status
   - **Flagged**: Only pairs exceeding the tolerance (should be empty)
   - **Contribution Check**: Top contributors to any residual differences

Current results: **0 flagged pairs**, max relative error ≈ 7.5 × 10⁻¹³ (machine epsilon).

## Output Files

### Industry Form
- `GHG_national_2022_m2_DecarbNexus_industry.xlsx` / `.csv` / `.parquet` / `.jsonld`

### Commodity Form (with `_commodity` suffix)
- `GHG_national_2022_m2_DecarbNexus_commodity.xlsx` / `.csv` / `.parquet` / `.jsonld`

### QC/QA
- `outputs/QCQA.xlsx` — B matrix comparison workbook

## Running the Pipeline

```bash
# One-time R setup (if not already done)
Rscript scripts/setup/export_reference_data.R

# Run the full pipeline
python scripts/generate_ghg_dataset.py
```

The commodity transformation runs automatically as part of the pipeline when the
required data files exist in `data/`.

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
