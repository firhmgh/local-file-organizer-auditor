"""
Multi-tier hashing module for duplicate file detection:
1. Size matching filter
2. First 4KB partial SHA-256 hash
3. Full content SHA-256 hash
"""
import hashlib
from pathlib import Path
from typing import Callable, Dict, List, Optional
from local_organizer.config import SMALL_CHUNK_SIZE, FULL_HASH_CHUNK_SIZE


def compute_partial_hash(file_path: Path, chunk_size: int = SMALL_CHUNK_SIZE) -> Optional[str]:
    """
    Compute SHA-256 hash of the first `chunk_size` bytes of a file.
    Fast screening to eliminate files with identical sizes but different headers.
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            chunk = f.read(chunk_size)
            if not chunk:
                return hashlib.sha256(b"").hexdigest()
            hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def compute_full_hash(file_path: Path, chunk_size: int = FULL_HASH_CHUNK_SIZE) -> Optional[str]:
    """
    Compute full SHA-256 hash of a file.
    """
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return None


def find_duplicate_groups(
    file_paths_by_size: Dict[int, List[Path]],
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, List[Path]]:
    """
    Given a mapping of {file_size: [Path, ...]}, finds groups of true identical duplicates.
    Uses multi-tier hashing (Partial -> Full SHA-256) to ensure zero false positives with minimal I/O.
    Returns {full_sha256_hash: [Path, ...]} containing 2 or more files.
    Optional progress_callback(processed_count, total_candidates, current_msg) is called periodically.
    """
    duplicate_groups: Dict[str, List[Path]] = {}
    candidate_size_groups = [paths for size, paths in file_paths_by_size.items() if len(paths) >= 2]
    total_candidates = sum(len(paths) for paths in candidate_size_groups)
    processed_count = 0
    for size, paths in file_paths_by_size.items():
        # If only one file has this size, it cannot be a duplicate
        if len(paths) < 2:
            continue

        # For zero-byte files, handle separately (optional: could group by hash of empty)
        if size == 0:
            # All 0-byte files have the same empty hash
            empty_hash = hashlib.sha256(b"").hexdigest()
            duplicate_groups[f"empty_{empty_hash}"] = paths
            processed_count += len(paths)
            if progress_callback:
                progress_callback(processed_count, total_candidates, "Memproses berkas 0-byte...")
            continue

        # Step 2: Partial Hash Filter
        partial_map: Dict[str, List[Path]] = {}
        for p in paths:
            p_hash = compute_partial_hash(p)
            if p_hash:
                partial_map.setdefault(p_hash, []).append(p)
            processed_count += 1
            if progress_callback and processed_count % 50 == 0:
                progress_callback(processed_count, total_candidates, f"Screening partial hash: {p.name}")

        # Step 3: Full SHA-256 for those with matching partial hashes
        for p_hash, candidate_paths in partial_map.items():
            if len(candidate_paths) < 2:
                continue

            # If candidates are small enough (<= SMALL_CHUNK_SIZE), partial hash is already full hash
            if size <= SMALL_CHUNK_SIZE:
                duplicate_groups[p_hash] = candidate_paths
                continue

            full_map: Dict[str, List[Path]] = {}
            for p in candidate_paths:
                f_hash = compute_full_hash(p)
                if f_hash:
                    full_map.setdefault(f_hash, []).append(p)
                if progress_callback:
                    progress_callback(processed_count, total_candidates, f"Computing full SHA-256: {p.name}")

            for f_hash, exact_paths in full_map.items():
                if len(exact_paths) >= 2:
                    duplicate_groups[f_hash] = exact_paths

    if progress_callback:
        progress_callback(total_candidates, total_candidates, "Selesai menghitung hash.")

    return duplicate_groups
