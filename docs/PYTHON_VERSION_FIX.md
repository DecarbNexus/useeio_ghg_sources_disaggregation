# Python Version Compatibility Issue

## The Problem

Your installation failed because:
- **You have**: Python 3.14
- **FlowSA v2.0.3 needs**: Python 3.9, 3.10, or 3.11
- **pandas 2.0.3 cannot build** on Python 3.14

Error: `Failed building wheel for pandas`

## Solution: Install Python 3.11

### Step 1: Download Python 3.11

**Option A: Download from python.org**
1. Go to: https://www.python.org/downloads/
2. Download Python 3.11.9 (latest 3.11.x)
3. Run installer
4. **Important**: Check "Add Python 3.11 to PATH"

**Option B: Use winget (Windows 11)**
```powershell
winget install Python.Python.3.11
```

### Step 2: Create New Virtual Environment with Python 3.11

```bash
# Navigate to your project
cd "c:\Users\DamienLieber\Python workspace\Flowsa_extract_GHG_sources"

# Remove old venv (optional but recommended)
rmdir /s .venv

# Create new venv with Python 3.11
py -3.11 -m venv .venv

# Activate it
.venv\Scripts\activate

# Verify Python version
python --version
# Should show: Python 3.11.x
```

### Step 3: Install FlowSA

Now run the installation again:

```bash
python install_flowsa_2.0.3.py
```

Or manually:
```bash
pip install git+https://github.com/USEPA/flowsa.git@1cb504c0e7a656ec8d9f2bf00b479df855838c43
```

## Why This Happens

Python 3.14 changed internal APIs that break older versions of pandas:
- `_PyLong_AsByteArray` signature changed
- Complex number handling changed
- Several deprecated APIs removed

pandas 2.0.3 (from 2023) was built for Python 3.9-3.12 and doesn't know about Python 3.14.

## Quick Reference: Python Version Matrix

| Python Version | FlowSA v2.0.3 | pandas 2.0.3 | Status |
|----------------|---------------|--------------|---------|
| 3.9            | ✓             | ✓            | Works   |
| 3.10           | ✓             | ✓            | Works   |
| 3.11           | ✓             | ✓            | **Recommended** |
| 3.12           | Maybe         | Maybe        | Untested |
| 3.14           | ✗             | ✗            | **Fails** |

## Troubleshooting

### "py -3.11" not found

If `py -3.11` doesn't work, try:

```bash
# Find where Python 3.11 is installed
where python

# Use full path, e.g.:
C:\Python311\python.exe -m venv .venv
```

### Multiple Python versions

If you have multiple Pythons:

```bash
# List available versions
py --list

# Use specific version
py -3.11 -m venv .venv
```

### Can't install Python 3.11

If you can't install Python 3.11, you have two options:

**Option A: Use pre-built wheels (if available)**
```bash
# Try installing pandas from wheel first
pip install pandas==2.0.3

# Then install flowsa
pip install git+https://github.com/USEPA/flowsa.git@1cb504c
```

**Option B: Use conda (recommended for data science)**
```bash
# Install miniconda first, then:
conda create -n flowsa python=3.11
conda activate flowsa
pip install git+https://github.com/USEPA/flowsa.git@1cb504c
```

## Next Steps

After installing Python 3.11 and creating the new venv:

1. ✓ Verify Python version: `python --version`
2. ✓ Install FlowSA: `python install_flowsa_2.0.3.py`
3. ✓ Run extraction: `python run_extraction.py`

## Alternative: Skip to Pre-built Data

If you can't get Python 3.11 working, you can skip the regeneration step and work directly with the existing parquet file at:
```
C:\Users\DamienLieber\AppData\Local\flowsa\FlowBySector\GHG_national_2022_m2_v2.0.3_1cb504c.parquet
```

Just modify your enrichment script to skip the generation step and only do the metadata enrichment.
