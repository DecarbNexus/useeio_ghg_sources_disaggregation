# Export Reference Data from useeior for Python Pipeline
#
# This script builds the USEEIOv2.2.22-GHG model and exports nine CSVs
# that the Python pipeline needs:
#
#   1. cpi_adjusted_industry_output.csv — CPI-adjusted industry output in {DATA_YEAR}$ in 2017$
#   2. cpi_adjusted_commodity_output.csv — CPI-adjusted commodity output in {DATA_YEAR}$ in 2017$
#   3. naics_bea_allocation.csv        — NAICS-to-BEA allocation weights (output-based)
#   4. V_n.csv                         — Market share matrix (industries × commodities)
#   5. raw_industry_output_{DATA_YEAR}.csv  — Raw {DATA_YEAR} industry output (reference)
#   6. industry_cpi.csv                — Multi-year industry CPI table (reference)
#   7. B_matrix.csv                    — Full B matrix (flows × commodities, validation truth)
#   8. naics_to_useeio_crosswalk.csv   — NAICS-to-USEEIO crosswalk (model$crosswalk)
#   9. sector_classification.csv       — USEEIO sector classification (model$Industries + model$Commodities)
#
# Usage:
#   Rscript scripts/setup/export_reference_data.R
#
# Requires R >= 4.1 and internet access for the first install.
# Run once after cloning the repo; re-run if the model version changes.

# =============================================================================
# 0. Configuration — keep in sync with config.py
# =============================================================================

# ── Set this ONE value to switch Supply Chain Emission Factor releases ────────
SEF_VERSION <- "v1.4.0"  # keep in sync with config.py
# ─────────────────────────────────────────────────────────────────────────────

SEF_SPECS <- list(
  "v1.3.0" = list(useeior_tag = "v1.5.3",  useeior_ver = "1.5.3",
                  model_name  = "USEEIOv2.2.22-GHG",      data_year = 2022),
  "v1.4.0" = list(useeior_tag = "SEFv1.4", useeior_ver = "1.8.0",
                  model_name  = "USEEIOv2.6.0-phoebe-23", data_year = 2023)
)

if (is.null(SEF_SPECS[[SEF_VERSION]])) stop("Unknown SEF_VERSION: ", SEF_VERSION)
.s <- SEF_SPECS[[SEF_VERSION]]

GITHUB_ORG  <- "cornerstone-data"
USEEIOR_TAG <- .s$useeior_tag
USEEIOR_VER <- .s$useeior_ver
MODEL_NAME  <- .s$model_name
DATA_YEAR   <- .s$data_year
IO_YEAR     <- 2017

MODEL_SPEC_URL <- paste0(
  "https://raw.githubusercontent.com/", GITHUB_ORG,
  "/supply-chain-factors/main/model-specs/", MODEL_NAME, ".yml"
)

# Output directory (relative to project root) — version-stamped so multiple
# SEF versions can coexist: data/SEF_v1.3.0/, data/SEF_v1.4.0/, etc.
OUTPUT_DIR <- file.path("data", paste0("SEF_", SEF_VERSION))

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

# If the wrong version is already loaded in this R session, R cannot replace it
# without a restart. Detect this early and stop with a clear message.
if (!is.null(installed_ver) && installed_ver != USEEIOR_VER &&
    "useeior" %in% loadedNamespaces()) {
  stop(
    "useeior ", installed_ver, " is loaded in this R session, but ",
    USEEIOR_VER, " is required.\n",
    "Please restart R (Session > Restart R in RStudio, or close/reopen R) ",
    "and re-run this script."
  )
}

if (is.null(installed_ver) || installed_ver != USEEIOR_VER) {
  message("Installing useeior ", USEEIOR_TAG, " from GitHub...")
  remotes::install_github(
    paste0("cornerstone-data/useeior@", USEEIOR_TAG),
    dependencies = TRUE,
    upgrade      = "never"
  )
} else {
  message("useeior ", USEEIOR_VER, " already installed.")
}

library(useeior)
library(dplyr)
library(tidyr)
library(stringr)
if (as.character(packageVersion("useeior")) != USEEIOR_VER) {
  stop("useeior loaded as ", packageVersion("useeior"),
       " but ", USEEIOR_VER, " is required. Restart R and re-run.")
}
message("Loaded useeior version: ", packageVersion("useeior"))

# =============================================================================
# 2. Build the model
# =============================================================================

spec_local <- file.path(tempdir(), paste0(MODEL_NAME, ".yml"))
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
out_path <- file.path(OUTPUT_DIR, "cpi_adjusted_industry_output.csv")
write.csv(adjusted, out_path)
message("Exported: ", out_path, " (", nrow(adjusted), " rows)")

# --- 4b. CPI-adjusted commodity output (back-conversion denominator) --------
# Same call as 4a but with output_type = "Commodity"
adjusted_commodity <- adjustOutputbyCPI_fn(DATA_YEAR, IO_YEAR, "US", FALSE, model, "Commodity")
out_path <- file.path(OUTPUT_DIR, "cpi_adjusted_commodity_output.csv")
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

# --- 4e. Raw industry output for DATA_YEAR (reference) ----------------------
output_year <- model$MultiYearIndustryOutput[, as.character(DATA_YEAR), drop = FALSE]
out_path <- file.path(OUTPUT_DIR, paste0("raw_industry_output_", DATA_YEAR, ".csv"))
write.csv(output_year, out_path)
message("Exported: ", out_path, " (", nrow(output_year), " rows)")

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

# --- 4g. NAICS-to-USEEIO crosswalk (directly from model$crosswalk) ----------
crosswalk <- model$crosswalk
out_path  <- file.path(OUTPUT_DIR, "naics_to_useeio_crosswalk.csv")
write.csv(crosswalk, out_path, row.names = FALSE)
message("Exported: ", out_path, " (", nrow(crosswalk), " rows)")

# --- 4h. USEEIO sector classification (model$Industries + model$Commodities) -
sector_classification <- model$Industries %>%
  dplyr::select(Code, `Industry name` = Name) %>%
  dplyr::left_join(
    model$Commodities %>%
      dplyr::select(Code, `Commodity name` = Name, Category, Subcategory, Description),
    by = "Code"
  ) %>%
  tidyr::separate_wider_delim(
    Category,
    delim    = ": ",
    names    = c("Category Code", "Category Name"),
    too_many = "merge",
    too_few  = "align_start"
  ) %>%
  tidyr::separate_wider_delim(
    Subcategory,
    delim    = ": ",
    names    = c("Subcategory Code", "Subcategory Name"),
    too_many = "merge",
    too_few  = "align_start"
  ) %>%
  dplyr::mutate(
    Description = stringr::str_remove(Description, "^(BEA Code & Name is '?\\w+:.*?'?\\.\\s*)")
  ) %>%
  dplyr::select(
    `Category Code`,
    `Category Name`,
    `Subcategory Code`,
    `Subcategory Name`,
    `Sector code`   = Code,
    `Sector name`   = `Industry name`,
    `Commodity name`,
    Description
  )
out_path <- file.path(OUTPUT_DIR, "sector_classification.csv")
write.csv(sector_classification, out_path, row.names = FALSE)
message("Exported: ", out_path, " (", nrow(sector_classification), " rows)")

# =============================================================================
# 5. Summary
# =============================================================================

message("\n=== Export complete ===")
message("Files written to: ", normalizePath(OUTPUT_DIR))
message("  cpi_adjusted_industry_output.csv   — CPI-adjusted industry output (", nrow(adjusted), " sectors)")
message("  cpi_adjusted_commodity_output.csv  — CPI-adjusted commodity output (", nrow(adjusted_commodity), " sectors)")
message("  naics_bea_allocation.csv           — Allocation weights (", nrow(allocation), " rows)")
message("  V_n.csv                            — Market share matrix (", nrow(V_n), " industries x ", ncol(V_n), " commodities)")
message("  raw_industry_output_", DATA_YEAR, ".csv     — Raw ", DATA_YEAR, " output (", nrow(output_year), " sectors)")
message("  industry_cpi.csv               — CPI table (", nrow(cpi), " sectors x ", ncol(cpi), " years)")
message("  B_matrix.csv                   — B matrix (", nrow(B), " flows x ", ncol(B), " commodities)")
message("  naics_to_useeio_crosswalk.csv  — NAICS-to-USEEIO crosswalk (", nrow(crosswalk), " rows)")
message("  sector_classification.csv      — Sector classification (", nrow(sector_classification), " rows)")
message("\nRun the Python pipeline next:")
message("  python scripts/generate_ghg_dataset.py")
