"""
File and directory scanner:
- Recursively gathers files and empty directories
- Extracts metadata (size, mtime, ctime, extension, parent directories)
- Respects blacklist/whitelist and exclusion filters
"""
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from local_organizer.config import PROTECTED_DIR_PATTERNS


@dataclass
class FileInfo:
    path: Path
    rel_path: str
    size: int
    mtime: float
    ctime: float
    extension: str
    name: str
    is_hidden: bool
    is_protected_location: bool = False
    parent_dirs_lower: List[str] = field(default_factory=list)


@dataclass
class ScanResult:
    root_path: Path
    files: List[FileInfo]
    files_by_size: Dict[int, List[Path]]
    empty_directories: List[Path]
    total_size_bytes: int
    scanned_file_count: int
    skipped_count: int
    errors: List[str]


def is_hidden_path(path: Path) -> bool:
    """Check if file or any parent folder in relative hierarchy is hidden."""
    # Check leading dot in name
    if path.name.startswith(".") and path.name not in {".", ".."}:
        return True
    for part in path.parts:
        if part.startswith(".") and part not in {".", ".."}:
            return True

    # Windows hidden attribute check
    try:
        if os.name == "nt":
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs != -1 and bool(attrs & 2):  # FILE_ATTRIBUTE_HIDDEN = 2
                return True
    except Exception:
        pass
    return False


def is_in_protected_directory(path: Path, root_path: Optional[Path] = None) -> bool:
    """
    Check if the path lies within a known protected directory pattern relative to scan root.
    If root_path is provided, only inspect directory parts relative to root.
    """
    if root_path:
        try:
            rel = path.relative_to(root_path)
            parts_lower = [p.lower() for p in rel.parts[:-1]]
        except Exception:
            parts_lower = [p.lower() for p in path.parts]
    else:
        parts_lower = [p.lower() for p in path.parts]

    for pattern in PROTECTED_DIR_PATTERNS:
        if pattern.lower() in parts_lower:
            return True
    return False


def scan_directory(
    root_dir: str | Path,
    excluded_dirs: Optional[Set[str]] = None,
    excluded_extensions: Optional[Set[str]] = None,
    whitelist_dirs: Optional[Set[str]] = None,
    min_size_bytes: int = 0,
    progress_callback: Optional[Callable[[int, Path], None]] = None,
) -> ScanResult:
    """
    Perform a safe, non-modifying scan of the specified root_dir.
    Optional progress_callback(current_count, current_path) is called periodically.
    """
    root_path = Path(root_dir).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Direktori target tidak ditemukan: {root_path}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Target bukan direktori: {root_path}")

    excluded_dirs_lower = {d.lower() for d in (excluded_dirs or set())}
    excluded_exts_lower = {e.lower() if e.startswith(".") else f".{e.lower()}" for e in (excluded_extensions or set())}
    whitelist_dirs_lower = {w.lower() for w in (whitelist_dirs or set())}

    files: List[FileInfo] = []
    files_by_size: Dict[int, List[Path]] = {}
    empty_directories: List[Path] = []
    total_size = 0
    skipped_count = 0
    errors: List[str] = []

    # os.walk bottom-up helps identify empty directories easily
    for current_root, dirnames, filenames in os.walk(root_path, topdown=False):
        current_path = Path(current_root)

        # Check for empty directories
        if not dirnames and not filenames:
            # Avoid marking root_path itself if empty, and never mark empty dirs in protected hierarchies (.git, node_modules, etc.)
            if current_path != root_path and not is_in_protected_directory(current_path):
                empty_directories.append(current_path)

        for filename in filenames:
            file_path = current_path / filename
            try:
                # Check whitelist if specified
                rel_parts = file_path.relative_to(root_path).parts
                rel_parts_lower = [p.lower() for p in rel_parts]

                if whitelist_dirs_lower:
                    # Must match at least one whitelist directory
                    matched_whitelist = any(
                        wl in rel_parts_lower[:-1] for wl in whitelist_dirs_lower
                    )
                    if not matched_whitelist:
                        skipped_count += 1
                        continue

                # Check custom excluded dirs
                if any(ed in rel_parts_lower[:-1] for ed in excluded_dirs_lower):
                    skipped_count += 1
                    continue

                ext = file_path.suffix.lower()
                if ext in excluded_exts_lower:
                    skipped_count += 1
                    continue

                stat = file_path.stat()
                file_size = stat.st_size

                if file_size < min_size_bytes:
                    skipped_count += 1
                    continue

                hidden = is_hidden_path(file_path)
                in_prot_dir = is_in_protected_directory(file_path, root_path=root_path)

                info = FileInfo(
                    path=file_path,
                    rel_path=str(file_path.relative_to(root_path)),
                    size=file_size,
                    mtime=stat.st_mtime,
                    ctime=stat.st_ctime,
                    extension=ext,
                    name=filename,
                    is_hidden=hidden,
                    is_protected_location=in_prot_dir,
                    parent_dirs_lower=rel_parts_lower[:-1],
                )

                files.append(info)
                files_by_size.setdefault(file_size, []).append(file_path)
                total_size += file_size

                if progress_callback and len(files) % 50 == 0:
                    progress_callback(len(files), file_path)

            except (PermissionError, FileNotFoundError, OSError) as e:
                errors.append(f"Gagal membaca metadata {file_path}: {e}")

    if progress_callback:
        progress_callback(len(files), root_path)

    return ScanResult(
        root_path=root_path,
        files=files,
        files_by_size=files_by_size,
        empty_directories=empty_directories,
        total_size_bytes=total_size,
        scanned_file_count=len(files),
        skipped_count=skipped_count,
        errors=errors,
    )
