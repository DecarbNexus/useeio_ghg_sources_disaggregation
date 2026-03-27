# Export Reference Data from useeior for Python Pipeline
#
# This script builds the USEEIOv2.2.22-GHG model and exports seven CSVs
# that the Python pipeline needs:
#
#   1. adjusted_output.csv             — CPI-adjusted 2022 industry output in 2017$
#   2. adjusted_commodity_output.csv   — CPI-adjusted 2022 commodity output in 2017$
#   3. naics_bea_allocation.csv        — NAICS-to-BEA allocation weights (output-based)
#   4. V_n.csv                         — Market share matrix (industries × commodities)
#   5. industry_output_2022.csv        — Raw 2022 industry output (reference)
#   6. industry_cpi.csv                — Multi-year industry CPI table (reference)
#   7. B_matrix.csv                    — Full B matrix (flows × commodities, validation truth)
#
# Usage:
#   Rscript scripts/setup/export_reference_data.R
#
# Requires R >= 4.1 and internet access for the first install.
# Run once after cloning the repo; re-run if the model version changes.

# =============================================================================
# 0. Configuration — keep in sync with config.py
# =============================================================================

USEEIOR_TAG <- "v1.5.3"
USEEIOR_VER <- "1.5.3"
MODEL_NAME  <- "USEEIOv2.2.22-GHG"
DATA_YEAR   <- 2022
IO_YEAR     <- 2017

MODEL_SPEC_URL <- paste0(
  "https://raw.githubusercontent.com/USEPA/supply-chain-factors/main/",
  "model-specs/USEEIOv2.2.22-GHG.yml"
)

# Output directory (relative to project root)
OUTPUT_DIR <- "data"

# =============================================================================
# 1. Install / verify useeior
# =============================================================================

if (!requireNamespace("remotes", quietly = TRUE)) {
  install.packages("remotes")
}

installed_ver <- tryCatch(
  as.character(packageVersion("useeior")),
  error = function(e) NULL
)

if (is.null(installed_ver) || installed_ver != USEEIOR_VER) {
  message("Installing useeior ", USEEIOR_TAG, " from GitHub...")
  remotes::install_github(
    paste0("USEPA/useeior@", USEEIOR_TAG),
    dependencies = TRUE,
    upgrade      = "never"
  )
} else {
  message("useeior ", USEEIOR_VER, " already installed.")
}

library(useeior)
message("Loaded useeior version: ", packageVersion("useeior"))

# =============================================================================
# 2. Build the model
# =============================================================================

spec_local <- file.path(tempdir(), "USEEIOv2.2.22-GHG.yml")
if (!file.exists(spec_local)) {
  message("Downloading model spec from supply-chain-factors repo...")
  download.file(MODEL_SPEC_URL, destfile = spec_local, quiet = TRUE)
}

message("Building model: ", MODEL_NAME, " ...")
model <- buildModel(MODEL_NAME, configpaths = spec_local)
message("Model build complete.")
message("  Industries: ", nrow(model$Industries))
message("  Commodities: ", nrow(model$Commodities))
message("  B matrix: ", paste(dim(model$B), collapse = " x "))

# =============================================================================
# 3. Bind internal functions
# =============================================================================

adjustOutputbyCPI_fn       <- useeior:::adjustOutputbyCPI
getNAICStoBEAAllocation_fn <- useeior:::getNAICStoBEAAllocation

# =============================================================================
# 4. Export CSVs
# =============================================================================

if (!dir.exists(OUTPUT_DIR)) {
  dir.create(OUTPUT_DIR, recursive = TRUE)
}

# --- 4a. CPI-adjusted industry output (CbS denominator) ---------------------
# adjustOutputbyCPI(outputyear, referenceyear, location_acronym, IsRoUS, model, output_type)
adjusted <- adjustOutputbyCPI_fn(DATA_YEAR, IO_YEAR, "US", FALSE, model, "Industry")
out_path <- file.path(OUTPUT_DIR, "adjusted_output.csv")
write.csv(adjusted, out_path)
message("Exported: ", out_path, " (", nrow(adjusted), " rows)")

# --- 4b. CPI-adjusted commodity output (back-conversion denominator) --------
# Same call as 4a but with output_type = "Commodity"
adjusted_commodity <- adjustOutputbyCPI_fn(DATA_YEAR, IO_YEAR, "US", FALSE, model, "Commodity")
out_path <- file.path(OUTPUT_DIR, "adjusted_commodity_output.csv")
write.csv(adjusted_commodity, out_path)
message("Exported: ", out_path, " (", nrow(adjusted_commodity), " rows)")

# --- 4c. NAICS-to-BEA allocation weights ------------------------------------
# getNAICStoBEAAllocation(year, model)
allocation <- getNAICStoBEAAllocation_fn(DATA_YEAR, model)
out_path <- file.path(OUTPUT_DIR, "naics_bea_allocation.csv")
write.csv(allocation, out_path, row.names = FALSE)
message("Exported: ", out_path, " (", nrow(allocation), " rows)")

# --- 4d. V_n market share matrix (industries × commodities) ------------------
# model$V_n is the commodity market share matrix: V_n[i,j] = V[i,j] / q_j
# Used in the Python matrix multiply: B_commodity = B_industry %*% V_n
V_n <- as.data.frame(as.matrix(model$V_n))
out_path <- file.path(OUTPUT_DIR, "V_n.csv")
write.csv(V_n, out_path)
message("Exported: ", out_path, " (", nrow(V_n), " rows x ", ncol(V_n), " cols)")

# --- 4d. Raw 2022 industry output (reference) --------------------------------
output_2022 <- model$MultiYearIndustryOutput[, as.character(DATA_YEAR), drop = FALSE]
out_path <- file.path(OUTPUT_DIR, "industry_output_2022.csv")
write.csv(output_2022, out_path)
message("Exported: ", out_path, " (", nrow(output_2022), " rows)")

# --- 4e. Multi-year industry CPI (reference) ---------------------------------
cpi <- model$MultiYearIndustryCPI
out_path <- file.path(OUTPUT_DIR, "industry_cpi.csv")
write.csv(cpi, out_path)
message("Exported: ", out_path, " (", nrow(cpi), " rows)")

# --- 4f. B matrix (flows × commodities) — validation truth -------------------
B <- as.data.frame(as.matrix(model$B))
out_path <- file.path(OUTPUT_DIR, "B_matrix.csv")
write.csv(B, out_path)
message("Exported: ", out_path, " (", nrow(B), " rows x ", ncol(B), " cols)")

# =============================================================================
# 5. Summary
# =============================================================================

message("\n=== Export complete ===")
message("Files written to: ", normalizePath(OUTPUT_DIR))
message("  adjusted_output.csv            — CPI-adjusted industry output (", nrow(adjusted), " sectors)")
message("  adjusted_commodity_output.csv  — CPI-adjusted commodity output (", nrow(adjusted_commodity), " sectors)")
message("  naics_bea_allocation.csv       — Allocation weights (", nrow(allocation), " rows)")
message("  V_n.csv                        — Market share matrix (", nrow(V_n), " industries x ", ncol(V_n), " commodities)")
message("  industry_output_2022.csv       — Raw 2022 output (", nrow(output_2022), " sectors)")
message("  industry_cpi.csv               — CPI table (", nrow(cpi), " sectors x ", ncol(cpi), " years)")
message("  B_matrix.csv                   — B matrix (", nrow(B), " flows x ", ncol(B), " commodities)")
message("\nRun the Python pipeline next:")
message("  python scripts/generate_ghg_dataset.py")
