"""
Utility Functions for FlowBySector Data Processing

This module contains helper functions used across the enrichment pipeline.
"""

import os
import sys
import subprocess
import pandas as pd
from pathlib import Path

# Add parent directory to path to import config
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))
import config


def get_emissions_intensity_col():
    """
    Get the emissions intensity column name with the model year.
    
    Returns:
    --------
    str
        Column name like "Emissions Intensity (kg/USD_2022)"
    """
    return f"Emissions Intensity (kg/USD_{config.MODEL_YEAR})"


def check_flowsa_version():
    """
    Check if the installed FlowSA version matches requirements.
    
    Returns:
    --------
    tuple : (str, str)
        (installed_version, installed_git_hash)
    """
    try:
        # Get FlowSA package location
        import flowsa
        flowsa_path = Path(flowsa.__file__).parent
        
        # Try to get version from git
        try:
            git_hash = subprocess.check_output(
                ['git', 'rev-parse', '--short=7', 'HEAD'],
                cwd=flowsa_path,
                stderr=subprocess.DEVNULL,
                text=True
            ).strip()
        except:
            git_hash = None
        
        # Try to get version from package metadata
        try:
            import importlib.metadata
            version = importlib.metadata.version('flowsa')
        except:
            try:
                version = flowsa.__version__
            except:
                version = None
        
        return version, git_hash
    except Exception as e:
        print(f"Warning: Could not determine FlowSA version: {e}")
        return None, None


def validate_flowsa_version():
    """
    Validate that FlowSA version matches requirements in config.
    
    Raises:
    -------
    RuntimeError
        If version doesn't match and STRICT_VERSION_CHECK is True
    """
    if not config.STRICT_VERSION_CHECK:
        return
    
    installed_version, installed_git_hash = check_flowsa_version()
    
    # Handle both single version string and list of acceptable versions
    required_versions = config.REQUIRED_FLOWSA_VERSION
    if isinstance(required_versions, str):
        required_versions = [required_versions]
    
    print(f"\nFlowSA Version Check:")
    print(f"  Required version: {' or '.join(required_versions)} (tag: {config.REQUIRED_FLOWSA_GIT_TAG})")
    print(f"  Installed version: {installed_version or 'unknown'} (git: {installed_git_hash or 'unknown'})")
    
    # Check version - this is the critical check
    version_match = installed_version in required_versions
    
    # Git hash check is optional/advisory only (may not work in all environments)
    # Only warn if both are available and don't match
    if installed_git_hash and config.REQUIRED_FLOWSA_GIT_HASH:
        if installed_git_hash != config.REQUIRED_FLOWSA_GIT_HASH:
            print(f"  Note: Git hash differs (expected: {config.REQUIRED_FLOWSA_GIT_HASH})")
            print(f"        This is usually fine if version numbers match")
    
    if not version_match:
        error_msg = [
            "\n" + "="*80,
            "ERROR: FlowSA Version Mismatch",
            "="*80,
            f"Your reference parquet file was generated with FlowSA v{' or '.join(required_versions)}",
            f"You currently have FlowSA v{installed_version or 'unknown'} (git: {installed_git_hash or 'unknown'})",
            "",
            "To fix this, reinstall the correct version:",
            f"  pip uninstall flowsa",
            f"  pip install git+https://github.com/USEPA/flowsa.git@{config.REQUIRED_FLOWSA_GIT_TAG}",
            "",
            "Or run the installation script:",
            f"  python install_flowsa_2.0.3.py",
            "",
            "Or to skip version checking, set STRICT_VERSION_CHECK = False in config.py",
            "="*80
        ]
        raise RuntimeError("\n".join(error_msg))
    
    print("  ✓ Version check passed")


def filter_columns(df, keep_cols, exclude_qc=False, qc_cols=None):
    """
    Filter DataFrame to keep only specified columns that are present.
    
    Optionally excludes quality control columns if requested.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame to filter
    keep_cols : list
        List of column names to keep (if present)
    exclude_qc : bool, optional
        If True, exclude quality control columns from output (default: False)
    qc_cols : list, optional
        List of quality control column names to exclude if exclude_qc=True
        
    Returns:
    --------
    pandas.DataFrame
        Filtered DataFrame with only the specified columns
    """
    # Remove QC columns from keep list if requested
    if exclude_qc and qc_cols:
        keep_cols = [c for c in keep_cols if c not in qc_cols]
        print(f"Excluding {len(qc_cols)} quality control columns from output")
    
    # Find which columns from our keep list are actually present in the data
    present_cols = [c for c in keep_cols if c in df.columns]
    missing_cols = [c for c in keep_cols if c not in df.columns]
    
    if missing_cols:
        print(f"Note: {len(missing_cols)} requested columns not found in data")
        if len(missing_cols) <= 5:
            print(f"  Missing: {missing_cols}")
    
    return df[present_cols].copy()


# TODO: Add more utility functions as needed during incremental migration
# Candidates from enrich_fbs_with_meta.py:
# - safe_division()
# - format_number()
# - clean_string()
# - etc.
