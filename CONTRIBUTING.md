# Contributing

Thanks for your interest in improving this project! This guide explains the repo layout and how to make changes safely.

## Repo layout

- `scripts/`
  - `extract_meta_from_EPA_GHGI.py` — builds `outputs/EPA_GHGI_meta_sources.{csv,yaml}` by parsing EPA GHGI YAML, normalizing description into `Subcategory`, and deriving `IPCC_Category` from chapter.
  - `enrich_fbs_with_meta.py` — loads a FlowBySector parquet and merges the metadata CSV using `MetaSources` → `meta_id` extraction.
- `outputs/` — generated artifacts (git-ignored). Recreate by running the scripts.
- `docs/` — documentation notes, if any.
- `README.md` — overview and usage.
- `requirements.txt` — minimal dependencies for the scripts.
- `.gitignore` — ignores temp files, outputs, and local envs.

Legacy or personal experiments should go to `local/` or `sandbox/` (both are git-ignored) to keep the repo clean.

## Development setup

1) Create and activate a virtual environment (Windows PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Generate metadata CSV/YAML:

```powershell
python -m scripts.extract_meta_from_EPA_GHGI
```

3) Enrich a FlowBySector parquet with metadata:

```powershell
python -m scripts.enrich_fbs_with_meta
```

## Custom label overrides

Provide a CSV with `table_id,label` or `meta_id,label` and run the extractor with `--label-map`.

## Code style

- Prefer small, focused functions.
- Keep regex-based transforms in `CUSTOM_DESC_TRANSFORMS`.
- Avoid hardcoding local machine paths; prefer parameters or environment variables when possible.

## Opening issues / PRs

- Describe the change and why it’s needed.
- Include before/after samples when modifying transforms.
- For new Annex rules, specify the patterns and the resulting category.
