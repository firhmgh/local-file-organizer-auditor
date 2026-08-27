"""
Decision engine for choosing which file to KEEP as primary among duplicate copies.
Evaluation criteria prioritizes:
1. Immunity/Protection status (never delete protected files)
2. Directory structure quality (organized subfolders vs root/dump folders like Downloads/Desktop)
3. Descriptive, clean naming (penalize '(1)', 'copy', 'salinan', 'download')
4. Path depth and project relevance
"""
import re
from pathlib import Path
from typing import List, Tuple
from local_organizer.config import PROTECTED_EXACT_FILENAMES
from local_organizer.scanner import FileInfo, is_in_protected_directory


def score_file_keeper(file_info: FileInfo) -> float:
    """
    Calculate a suitability score for keeping this file as the primary version.
    Higher score = better candidate to KEEP.
    """
    score = 100.0
    path_str = str(file_info.path).lower()
    name_str = file_info.name.lower()

    # Rule 1: Files in protected locations or exact protected names get top priority
    if file_info.is_protected_location or name_str in PROTECTED_EXACT_FILENAMES:
        score += 1000.0

    # Rule 2: Penalize junk/dump folders
    dump_folders = {"download", "downloads", "temp", "tmp", "desktop", "unduhan"}
    for dump in dump_folders:
        if dump in file_info.parent_dirs_lower:
            score -= 40.0

    # Rule 3: Reward structured directories
    organized_folders = {"documents", "dokumen", "projects", "proyek", "pictures", "gambar", "videos", "music", "arsip", "archives", "work", "kuliah", "tugas"}
    for org in organized_folders:
        if org in file_info.parent_dirs_lower:
            score += 25.0

    # Rule 4: Penalize copy/duplicate suffixes in filename (e.g. 'file (1).pdf', 'image - Copy.png', 'doc_salinan.docx')
    copy_patterns = [
        r"\(\d+\)",            # (1), (2), etc.
        r"[-_ ]copy",          # - copy, _copy,  copy
        r"[-_ ]salinan",       # - salinan
        r"[-_ ]duplikat",      # - duplikat
        r"[-_ ]backup",        # - backup
        r"[-_ ]v\d+",          # - v1, _v2
    ]
    for cp in copy_patterns:
        if re.search(cp, name_str):
            score -= 30.0

    # Rule 5: Shorter, cleaner relative path depth is usually more organized than deeply nested accidental dumps,
    # but not at root directory (e.g. D:\file.pdf vs D:\Documents\file.pdf)
    depth = len(file_info.parent_dirs_lower)
    if depth == 0:
        # File is in root audit directory
        score -= 10.0
    elif 1 <= depth <= 3:
        # Well structured depth
        score += 10.0
    elif depth > 6:
        # Too deep
        score -= 5.0

    # Rule 6: Slight preference for older modification time (original creation) as a tie-breaker
    # Add fractional value based on timestamp
    score += (file_info.mtime % 1000) / 10000.0

    return score


def select_best_keeper(candidates: List[FileInfo]) -> Tuple[FileInfo, List[FileInfo]]:
    """
    Given a list of duplicate FileInfo objects, selects the best one to KEEP,
    and returns (keeper, duplicates_to_clean).
    """
    if not candidates:
        raise ValueError("Candidate list cannot be empty")
    if len(candidates) == 1:
        return candidates[0], []

    scored_candidates = [(score_file_keeper(c), c) for c in candidates]
    # Sort descending by score
    scored_candidates.sort(key=lambda x: x[0], reverse=True)

    keeper = scored_candidates[0][1]
    duplicates = [c[1] for c in scored_candidates[1:]]

    return keeper, duplicates
