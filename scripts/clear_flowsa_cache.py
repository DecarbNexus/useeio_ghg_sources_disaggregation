"""
Clear FlowSA Cached Data

This script removes cached FlowByActivity and FlowBySector files that may be 
from different versions of FlowSA. This ensures that when you regenerate data,
it will use the current FlowSA version to download fresh source data.

The cache is located at: C:\Users\<username>\AppData\Local\flowsa\

Usage:
    python clear_flowsa_cache.py
    python clear_flowsa_cache.py --activity-only  # Only clear FlowByActivity files
    python clear_flowsa_cache.py --dry-run        # Show what would be deleted
"""

import os
import sys
import shutil
from pathlib import Path
import argparse

# Import config for path
import config


def get_cache_directories():
    """Get FlowSA cache directory paths."""
    base_path = Path(config.FLOWSA_DATA_PATH)
    
    return {
        "FlowByActivity": base_path / "FlowByActivity",
        "FlowBySector": base_path / "FlowBySector",
        "Bibliography": base_path / "Bibliography",
        "base": base_path
    }


def list_cached_files(cache_dir):
    """List all cached files in a directory with their metadata."""
    if not cache_dir.exists():
        return []
    
    files = []
    for file_path in cache_dir.glob("*"):
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "path": file_path,
                "name": file_path.name,
                "size_mb": stat.st_size / (1024 * 1024),
                "modified": stat.st_mtime
            })
    
    return sorted(files, key=lambda x: x["name"])


def clear_directory(cache_dir, dry_run=False):
    """Clear all files in a cache directory."""
    if not cache_dir.exists():
        print(f"  Directory does not exist: {cache_dir}")
        return 0, 0
    
    files = list_cached_files(cache_dir)
    
    if not files:
        print(f"  No files to delete")
        return 0, 0
    
    total_size = sum(f["size_mb"] for f in files)
    
    if dry_run:
        print(f"  Would delete {len(files)} files ({total_size:.1f} MB):")
        for f in files[:10]:  # Show first 10
            print(f"    - {f['name']} ({f['size_mb']:.2f} MB)")
        if len(files) > 10:
            print(f"    ... and {len(files) - 10} more files")
    else:
        print(f"  Deleting {len(files)} files ({total_size:.1f} MB)...")
        for f in files:
            try:
                f["path"].unlink()
            except Exception as e:
                print(f"    Error deleting {f['name']}: {e}")
        print(f"  ✓ Deleted {len(files)} files")
    
    return len(files), total_size


def main():
    parser = argparse.ArgumentParser(
        description="Clear FlowSA cached data files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_flowsa_cache.py                  # Clear all cached data
  python clear_flowsa_cache.py --activity-only  # Only clear FlowByActivity files
  python clear_flowsa_cache.py --dry-run        # Preview what would be deleted
  python clear_flowsa_cache.py --keep-fbs       # Keep FlowBySector reference files
        """
    )
    
    parser.add_argument(
        "--activity-only",
        action="store_true",
        help="Only clear FlowByActivity files (most common source of version issues)"
    )
    
    parser.add_argument(
        "--keep-fbs",
        action="store_true",
        help="Keep FlowBySector files (useful to preserve downloaded reference files)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("FlowSA Cache Cleanup")
    print("="*80)
    
    if args.dry_run:
        print("DRY RUN MODE - No files will be deleted")
    
    print(f"\nCache location: {config.FLOWSA_DATA_PATH}")
    print()
    
    cache_dirs = get_cache_directories()
    
    total_files = 0
    total_size = 0
    
    # Clear FlowByActivity (most important - these are the source of version conflicts)
    print("FlowByActivity cache:")
    files, size = clear_directory(cache_dirs["FlowByActivity"], args.dry_run)
    total_files += files
    total_size += size
    print()
    
    # Clear FlowBySector (unless --keep-fbs or --activity-only)
    if not args.activity_only and not args.keep_fbs:
        print("FlowBySector cache:")
        files, size = clear_directory(cache_dirs["FlowBySector"], args.dry_run)
        total_files += files
        total_size += size
        print()
    elif args.keep_fbs:
        print("FlowBySector cache: SKIPPED (--keep-fbs flag)")
        print()
    else:
        print("FlowBySector cache: SKIPPED (--activity-only flag)")
        print()
    
    # Summary
    print("="*80)
    if args.dry_run:
        print(f"Would delete {total_files} files ({total_size:.1f} MB total)")
        print("\nRe-run without --dry-run to actually delete files")
    else:
        print(f"✓ Cleanup complete: {total_files} files deleted ({total_size:.1f} MB freed)")
        print("\nNext time you run generateFlowBySector(), FlowSA will download")
        print("fresh FlowByActivity files using the current version.")
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
