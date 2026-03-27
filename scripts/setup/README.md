# R Setup Scripts

## One-Time Setup: Export Reference Data from useeior

Before running the Python pipeline, you need to export reference data from the
useeior R package. This is a one-time step (re-run only if the model version changes).

### Prerequisites

- **R >= 4.1** with internet access
- The script will auto-install `useeior v1.5.3` and its dependencies

### Run

```bash
Rscript scripts/setup/export_reference_data.R
```

### What It Does

Builds the `USEEIOv2.2.22-GHG` model and exports five CSVs to `data/`:

| File | Description |
|------|-------------|
| `adjusted_output.csv` | CPI-adjusted 2022 industry output in 2017$ (the CbS denominator) |
| `adjusted_commodity_output.csv` | CPI-adjusted 2022 commodity output in 2017$ (back-conversion multiplier) |
| `naics_bea_allocation.csv` | NAICS→BEA allocation weights based on industry output |
| `V_n.csv` | Market share matrix — industries × commodities (used in matrix multiply) |
| `industry_output_2022.csv` | Raw 2022 industry output (for reference) |
| `industry_cpi.csv` | Multi-year industry CPI table (for reference) |
| `B_matrix.csv` | Full B matrix — flows × commodities (validation truth) |

### Why Pre-Baked R Exports?

useeior performs complex CPI adjustments, RoUS handling, and multi-year
output interpolation internally. Rather than replicating that logic in Python,
we export the **final computed values** and use them directly. This ensures
our Python results match useeior exactly.

### Then Run the Python Pipeline

```bash
python scripts/generate_ghg_dataset.py
```
