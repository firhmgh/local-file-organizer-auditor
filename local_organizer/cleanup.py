"""
Safe cleanup and relocation execution module.
- NEVER performs permanent deletion: sends redundant duplicates and temporary files to Windows Recycle Bin via send2trash.
- Strictly verifies immunity before touching any file.
- Handles safe relocation of misplaced files.
- Removes empty directories if requested.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass

try:
    from send2trash import send2trash
except ImportError:
    # Fallback simulation if send2trash is not installed yet
    def send2trash(path_str: str):
        raise RuntimeError("send2trash library belum terinstall. Install via `pip install send2trash`")

from local_organizer.config import ActionCategory
from local_organizer.classifier import ClassificationReport, AuditItem, is_file_protected
from local_organizer.scanner import ScanResult


@dataclass
class CleanupExecutionSummary:
    trashed_files: List[Tuple[str, int]]  # (rel_path, size_bytes)
    relocated_files: List[Tuple[str, str]]  # (from_rel_path, to_rel_path)
    removed_empty_dirs: List[str]
    skipped_protected_files: List[str]
    errors: List[str]
    bytes_freed: int


def execute_cleanup(
    scan_result: ScanResult,
    report: ClassificationReport,
    clean_duplicates: bool = True,
    clean_temp_files: bool = True,
    relocate_misplaced: bool = False,
    remove_empty_dirs: bool = False,
) -> CleanupExecutionSummary:
    """
    Executes safe cleanup strictly after user confirmation.
    All removals are sent to Windows Recycle Bin.
    """
    trashed: List[Tuple[str, int]] = []
    relocated: List[Tuple[str, str]] = []
    removed_dirs: List[str] = []
    skipped_protected: List[str] = []
    errors: List[str] = []
    freed_bytes = 0

    root_path = scan_result.root_path

    # Step 1: Process item actions
    for item in report.items:
        # Double check immunity
        is_prot, _ = is_file_protected(item.file_info)
        if is_prot or item.is_protected or item.category == ActionCategory.FILE_SISTEM_KONFIG:
            skipped_protected.append(item.file_info.rel_path)
            continue

        # Duplicates removal to Recycle Bin (STRICTLY DUPLIKAT_AMAN only)
        if clean_duplicates and item.category == ActionCategory.DUPLIKAT_AMAN:
            try:
                if item.file_info.path.exists():
                    send2trash(str(item.file_info.path))
                    trashed.append((item.file_info.rel_path, item.file_info.size))
                    freed_bytes += item.file_info.size
            except Exception as e:
                errors.append(f"Gagal memindahkan ke Recycle Bin '{item.file_info.rel_path}': {e}")
            continue

        # Temporary files / junk removal to Recycle Bin
        if clean_temp_files and item.category == ActionCategory.KANDIDAT_HAPUS:
            try:
                if item.file_info.path.exists():
                    send2trash(str(item.file_info.path))
                    trashed.append((item.file_info.rel_path, item.file_info.size))
                    freed_bytes += item.file_info.size
            except Exception as e:
                errors.append(f"Gagal memindahkan ke Recycle Bin '{item.file_info.rel_path}': {e}")
            continue

        # Misplaced files relocation
        if relocate_misplaced and item.category == ActionCategory.SALAH_LOKASI and item.suggested_target_path:
            try:
                if item.file_info.path.exists():
                    target_dir = root_path / item.suggested_target_path
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_file = target_dir / item.file_info.name

                    # Prevent overwriting existing file
                    if target_file.exists():
                        target_file = target_dir / f"{item.file_info.path.stem}_relocated{item.file_info.path.suffix}"

                    shutil.move(str(item.file_info.path), str(target_file))
                    rel_dest = str(target_file.relative_to(root_path))
                    relocated.append((item.file_info.rel_path, rel_dest))
            except Exception as e:
                errors.append(f"Gagal memindahkan file '{item.file_info.rel_path}': {e}")
            continue

    # Step 2: Empty directories
    if remove_empty_dirs:
        for empty_dir in report.empty_directories:
            try:
                if empty_dir.exists() and not any(empty_dir.iterdir()):
                    empty_dir.rmdir()
                    removed_dirs.append(str(empty_dir.relative_to(root_path)))
            except Exception as e:
                errors.append(f"Gagal menghapus direktori kosong '{empty_dir}': {e}")

    return CleanupExecutionSummary(
        trashed_files=trashed,
        relocated_files=relocated,
        removed_empty_dirs=removed_dirs,
        skipped_protected_files=skipped_protected,
        errors=errors,
        bytes_freed=freed_bytes,
    )
