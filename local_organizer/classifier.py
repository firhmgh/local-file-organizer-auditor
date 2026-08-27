"""
Classifier and Organization Heuristic Engine V3:
- Multi-tier Categorization:
  1. PERTAHANKAN
  2. DUPLIKAT AMAN (Standalone files / repeated downloads that are 100% safe to trash)
  3. DUPLIKAT KONTEKSTUAL GIS (GIS dataset bundle sidecars: .cpg, .prj, .shp, .shx, .dbf, etc.)
  4. DUPLIKAT KONTEKSTUAL PROJECT/BUNDLE (Assets inside project trees, e.g. qgis2web, web exports, Laravel, Flutter, etc.)
  5. SALAH LOKASI (Misplaced documents/photos/videos in dump folders)
  6. PERLU REVIEW (Ambiguous/Large files)
  7. FILE SISTEM/KONFIGURASI (Immune project/system/code/database files)
  8. ARSIPKAN (Inactive old files)
  9. KANDIDAT HAPUS (Confirmed temporary/cache files)
- Context-Aware and Project-Bundle-Aware:
  - Detects GIS dataset bundles (.shp, .shx, .dbf, .prj, .cpg, .qmd, .qml, .gpkg).
  - Detects project/application bundles (qgis2web, css/images, legend, web fonts, leaflet assets).
  - Strictly protects bundle assets from automated deletion even if their hash is identical across export instances.
- Protects empty directories inside project trees / .git / GIS datasets.
"""
import re
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

from local_organizer.config import (
    ActionCategory,
    RiskLevel,
    PROTECTED_DIR_PATTERNS,
    PROTECTED_EXACT_FILENAMES,
    PROTECTED_EXTENSIONS,
    SOURCE_CODE_EXTENSIONS,
    GIS_DATASET_EXTENSIONS,
    PROJECT_BUNDLE_DIR_NAMES,
    STANDALONE_CLEANABLE_EXTENSIONS,
    EXTENSION_TYPE_MAP,
    TARGET_FOLDER_MAPPINGS,
)
from local_organizer.scanner import FileInfo, ScanResult
from local_organizer.keeper_selector import select_best_keeper


@dataclass
class AuditItem:
    file_info: FileInfo
    category: ActionCategory
    risk_level: RiskLevel
    reason: str
    suggested_target_path: Optional[str] = None
    duplicate_of: Optional[str] = None  # Rel path of primary keeper
    is_protected: bool = False
    details: Dict[str, str] = field(default_factory=dict)


@dataclass
class ClassificationReport:
    items: List[AuditItem]
    items_by_category: Dict[ActionCategory, List[AuditItem]]
    duplicate_groups: Dict[str, List[FileInfo]]  # hash -> list of FileInfo
    total_potential_space_savings: int
    category_counts: Dict[ActionCategory, int]
    empty_directories: List[Path]


def is_file_protected(file_info: FileInfo) -> Tuple[bool, str]:
    """
    Check if a file must be strictly protected from deletion/moving.
    Returns (is_protected, reason).
    """
    name_lower = file_info.name.lower()
    ext_lower = file_info.extension.lower()

    # 1. Inside protected directory
    if file_info.is_protected_location:
        for p in file_info.parent_dirs_lower:
            if p in PROTECTED_DIR_PATTERNS:
                return True, f"Terletak di dalam direktori terlindungi '{p}'"
        return True, "Terletak di dalam struktur direktori terlindungi (.git, venv, node_modules, dll.)"

    # 2. Exact protected filename
    if name_lower in PROTECTED_EXACT_FILENAMES:
        return True, f"File konfigurasi/sistem esensial ({file_info.name})"

    # 3. Protected extensions (e.g. database, certificates)
    if ext_lower in PROTECTED_EXTENSIONS:
        return True, f"File tipe terlindungi ({ext_lower})"

    # 4. Source code files
    if ext_lower in SOURCE_CODE_EXTENSIONS:
        return True, f"Source code / berkas kode program ({ext_lower})"

    # 5. Hidden files starting with dot
    if file_info.name.startswith("."):
        return True, f"Dotfile / konfigurasi tersembunyi ({file_info.name})"

    return False, ""


def is_gis_dataset_component(file_info: FileInfo, all_files_by_parent: Dict[Path, Set[str]]) -> Tuple[bool, str]:
    """
    Check if the file is part of a GIS dataset bundle (e.g. Shapefile package or QGIS bundle).
    Returns (is_gis, dataset_base_name).
    """
    ext_lower = file_info.extension.lower()
    if ext_lower not in GIS_DATASET_EXTENSIONS:
        return False, ""

    parent_path = file_info.path.parent
    sibling_names = all_files_by_parent.get(parent_path, set())
    stem_lower = file_info.path.stem.lower()

    # Check if there are other GIS components with same stem (e.g., .shp, .shx, .dbf, .prj, .cpg)
    shapefile_core_exts = {".shp", ".shx", ".dbf", ".prj", ".cpg"}
    matched_siblings = 0
    for core_ext in shapefile_core_exts:
        test_sibling = f"{stem_lower}{core_ext}"
        if test_sibling in sibling_names:
            matched_siblings += 1

    if matched_siblings >= 2 or ext_lower in {".shp", ".gpkg", ".gdb", ".qgz", ".qgs"}:
        return True, f"Dataset Geospasial/GIS ({file_info.path.stem})"

    return False, ""


def is_project_bundle_asset(file_info: FileInfo) -> Tuple[bool, str]:
    """
    Check if the file is an internal asset/resource of a project, web export (qgis2web), app build, etc.
    Returns (is_project_asset, project_bundle_name).
    """
    parents = file_info.parent_dirs_lower
    if not parents:
        return False, ""

    # Check for known project export or app signatures in path hierarchy
    for p in parents:
        if "qgis2web" in p:
            return True, f"Aset WebGIS Export ({p})"
        if p in PROJECT_BUNDLE_DIR_NAMES and len(parents) >= 2:
            return True, f"Aset Resource Proyek ({p})"

    return False, ""


def is_safe_standalone_duplicate(file_info: FileInfo, keeper_info: FileInfo, is_gis: bool, is_project: bool) -> Tuple[bool, str]:
    """
    Determine if a duplicate copy is safe for automated Recycle Bin cleanup.
    Safe duplicates are standalone user files (PDF, DOCX, user photos, personal videos, archives, downloads)
    that are OUTSIDE project/dataset bundles.
    """
    if is_gis:
        return False, "Komponen dataset GIS (penghapusan dapat merusak layer/proyek spasial)"

    if is_project:
        return False, "Aset/resource mandiri proyek (penghapusan dapat merusak tampilan/fungsi aplikasi)"

    ext_lower = file_info.extension.lower()
    name_lower = file_info.name.lower()
    parents = file_info.parent_dirs_lower

    # Repeated downloads pattern: "file (1).pdf", "doc - Copy.docx", "installer (2).exe"
    is_repeated_pattern = bool(
        re.search(r"\(\d+\)", name_lower)
        or re.search(r"[-_ ]copy", name_lower)
        or re.search(r"[-_ ]salinan", name_lower)
        or re.search(r"[-_ ]duplikat", name_lower)
    )

    # Standalone files directly in root or generic user folders (Downloads, Documents, Desktop, etc.)
    user_folders = {"downloads", "download", "documents", "dokumen", "desktop", "unduhan", "pictures", "gambar", "videos", "video", "music", "musik"}
    is_in_user_dir = len(parents) == 0 or any(u in parents for u in user_folders)

    # If both files are in the same folder and have identical content
    if file_info.path.parent == keeper_info.path.parent and (is_in_user_dir or is_repeated_pattern):
        return True, "Duplikat identik 100% dalam folder yang sama (salinan berulang)"

    # If it's a standalone file type
    if ext_lower in STANDALONE_CLEANABLE_EXTENSIONS and is_in_user_dir:
        if is_repeated_pattern or "downloads" in parents or len(parents) == 0:
            return True, f"Berkas mandiri terverifikasi identik 100% ({ext_lower})"
        else:
            return True, f"Berkas dokumen/media mandiri identik ({ext_lower})"

    return False, "Berkas memerlukan verifikasi kontekstual proyek"


def detect_misplaced_file(file_info: FileInfo, is_gis: bool = False, is_project: bool = False) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Identifies whether a file is likely misplaced based on its content type and current folder context.
    Never moves GIS bundle files or project files.
    """
    if is_gis or is_project:
        return False, None, None

    ext = file_info.extension.lower()
    name_lower = file_info.name.lower()
    parents = file_info.parent_dirs_lower

    # 1. Screenshot detection
    is_screenshot = (
        "screenshot" in name_lower
        or "tangkapan layar" in name_lower
        or "screen shot" in name_lower
        or name_lower.startswith("snip_")
        or name_lower.startswith("screenshot_")
    )
    if is_screenshot and ext in {".png", ".jpg", ".jpeg", ".webp"}:
        if "screenshots" not in parents and "tangkapan layar" not in parents:
            return True, TARGET_FOLDER_MAPPINGS["Screenshot"], "Tangkapan layar berada di luar folder Pictures/Screenshots"

    # 2. College / Thesis / School Work patterns
    college_keywords = ["tugas", "kuliah", "skripsi", "tesis", "uas", "uts", "makalah", "pr_", "praktikum", "laporan_akhir"]
    for kw in college_keywords:
        if kw in name_lower:
            if "kuliah" not in parents and "tugas" not in parents and "skripsi" not in parents:
                if ext in EXTENSION_TYPE_MAP and EXTENSION_TYPE_MAP[ext] == "Dokumen":
                    return True, TARGET_FOLDER_MAPPINGS["Tugas Kuliah"], f"Dokumen tugas/kuliah '{kw}' berada di folder umum"

    # 3. Work / Office patterns
    work_keywords = ["invoice", "faktur", "kontrak", "laporan_keuangan", "proposal_kerja", "slip_gaji", "notulen"]
    for kw in work_keywords:
        if kw in name_lower:
            if "work" not in parents and "pekerjaan" not in parents and "kantor" not in parents:
                return True, TARGET_FOLDER_MAPPINGS["Pekerjaan"], f"Dokumen pekerjaan '{kw}' berada di luar folder Work"

    # 4. Standard Type Mismatch:
    base_type = EXTENSION_TYPE_MAP.get(ext)
    if not base_type:
        return False, None, None

    # Check root dump
    if len(parents) == 0:
        target = TARGET_FOLDER_MAPPINGS.get(base_type, "Other")
        return True, target, f"File tipe {base_type} diletakkan di root direktori tanpa folder kategori"

    # Video inside documents
    if base_type == "Video" and any(p in {"documents", "dokumen", "docs", "text"} for p in parents):
        return True, TARGET_FOLDER_MAPPINGS["Video"], "File video tersimpan di dalam folder Dokumen"

    # Document inside Videos/Pictures/Music
    if base_type == "Dokumen" and any(p in {"videos", "video", "pictures", "foto", "gambar", "music", "musik"} for p in parents):
        return True, TARGET_FOLDER_MAPPINGS["Dokumen"], f"File dokumen tersimpan di dalam folder media ({parents[-1]})"

    # Photo/Image inside Documents
    if base_type == "Foto" and any(p in {"documents", "dokumen"} for p in parents):
        return True, TARGET_FOLDER_MAPPINGS["Foto"], "File foto tersimpan di dalam folder Dokumen"

    # Installer in Desktop/Documents
    if base_type == "Installer" and any(p in {"desktop", "documents", "dokumen"} for p in parents):
        return True, TARGET_FOLDER_MAPPINGS["Installer"], "File installer tersimpan di Desktop/Dokumen"

    # Archive in Desktop
    if base_type == "Archive" and any(p in {"desktop"} for p in parents):
        return True, TARGET_FOLDER_MAPPINGS["Archive"], "File arsip/zip menumpuk di Desktop"

    return False, None, None


def classify_files(scan_result: ScanResult, duplicate_groups: Dict[str, List[Path]]) -> ClassificationReport:
    """
    Main classification pipeline with Context, GIS Dataset, and Project Bundle Awareness:
    1. Index sibling files by directory to recognize GIS dataset bundles.
    2. Protect system/config/source files strictly.
    3. Separate duplicates into DUPLIKAT AMAN vs DUPLIKAT KONTEKSTUAL GIS vs DUPLIKAT KONTEKSTUAL PROJECT.
    4. Categorize remaining files into appropriate actions.
    """
    path_to_fileinfo: Dict[Path, FileInfo] = {f.path: f for f in scan_result.files}
    items: List[AuditItem] = []
    items_by_cat: Dict[ActionCategory, List[AuditItem]] = {cat: [] for cat in ActionCategory}
    cat_counts: Dict[ActionCategory, int] = {cat: 0 for cat in ActionCategory}
    total_potential_savings = 0

    # Build sibling cache for dataset bundle detection
    all_files_by_parent: Dict[Path, Set[str]] = {}
    for f in scan_result.files:
        all_files_by_parent.setdefault(f.path.parent, set()).add(f.name.lower())

    # Build duplicate lookup: which paths are keepers and which are duplicate copies
    duplicate_info_groups: Dict[str, List[FileInfo]] = {}
    keeper_paths: Set[Path] = set()
    duplicate_copy_map: Dict[Path, Tuple[FileInfo, str]] = {}  # path -> (keeper_info, hash)

    for f_hash, paths in duplicate_groups.items():
        infos = [path_to_fileinfo[p] for p in paths if p in path_to_fileinfo]
        if len(infos) < 2:
            continue

        duplicate_info_groups[f_hash] = infos
        keeper, duplicates = select_best_keeper(infos)
        keeper_paths.add(keeper.path)

        for d in duplicates:
            duplicate_copy_map[d.path] = (keeper, f_hash)

    # Process all scanned files
    for file_info in scan_result.files:
        is_prot, prot_reason = is_file_protected(file_info)
        is_gis, gis_name = is_gis_dataset_component(file_info, all_files_by_parent)
        is_project, project_name = is_project_bundle_asset(file_info)

        # Priority 1: Protected files (System, .env, .git, vendor, node_modules, source code)
        if is_prot:
            item = AuditItem(
                file_info=file_info,
                category=ActionCategory.FILE_SISTEM_KONFIG,
                risk_level=RiskLevel.KRITIS,
                reason=f"Dilindungi: {prot_reason}",
                is_protected=True,
            )
            items.append(item)
            continue

        # Priority 2: Duplicates handling (Safe vs GIS Contextual vs Project Bundle Contextual)
        if file_info.path in duplicate_copy_map:
            keeper_info, f_hash = duplicate_copy_map[file_info.path]
            is_safe, reason_safe = is_safe_standalone_duplicate(file_info, keeper_info, is_gis, is_project)

            if is_safe:
                item = AuditItem(
                    file_info=file_info,
                    category=ActionCategory.DUPLIKAT_AMAN,
                    risk_level=RiskLevel.RENDAH,
                    reason=f"{reason_safe}. Master copy: {keeper_info.rel_path}",
                    duplicate_of=keeper_info.rel_path,
                    details={"hash": f_hash, "keeper_rel_path": keeper_info.rel_path},
                )
                items.append(item)
                total_potential_savings += file_info.size
            elif is_gis:
                # Contextual GIS duplicate
                item = AuditItem(
                    file_info=file_info,
                    category=ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS,
                    risk_level=RiskLevel.SEDANG,
                    reason=f"Identik secara byte tetapi merupakan {reason_safe} ({gis_name}). Master: {keeper_info.rel_path}",
                    duplicate_of=keeper_info.rel_path,
                    details={"hash": f_hash, "keeper_rel_path": keeper_info.rel_path},
                )
                items.append(item)
            elif is_project:
                # Contextual Project/Bundle asset duplicate
                item = AuditItem(
                    file_info=file_info,
                    category=ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT,
                    risk_level=RiskLevel.SEDANG,
                    reason=f"Identik secara byte tetapi merupakan {reason_safe} ({project_name}). Master: {keeper_info.rel_path}",
                    duplicate_of=keeper_info.rel_path,
                    details={"hash": f_hash, "keeper_rel_path": keeper_info.rel_path},
                )
                items.append(item)
            else:
                # General contextual duplicate
                item = AuditItem(
                    file_info=file_info,
                    category=ActionCategory.DUPLIKAT_KONTEKSTUAL,
                    risk_level=RiskLevel.SEDANG,
                    reason=f"Identik secara byte tetapi berada dalam konteks terstruktur. Master: {keeper_info.rel_path}",
                    duplicate_of=keeper_info.rel_path,
                    details={"hash": f_hash, "keeper_rel_path": keeper_info.rel_path},
                )
                items.append(item)
            continue

        # Priority 3: Candidates for deletion (Temporary files, repeated downloads, old logs)
        ext_lower = file_info.extension.lower()
        name_lower = file_info.name.lower()
        file_type = EXTENSION_TYPE_MAP.get(ext_lower, "")

        if file_type == "Temporary" or ext_lower in {".tmp", ".temp", ".crdownload", ".part", ".bak", ".old"}:
            if not is_gis and not is_project:
                item = AuditItem(
                    file_info=file_info,
                    category=ActionCategory.KANDIDAT_HAPUS,
                    risk_level=RiskLevel.RENDAH,
                    reason=f"Berkas sementara / cache ({ext_lower}) yang aman dibersihkan ke Recycle Bin",
                )
                items.append(item)
                total_potential_savings += file_info.size
                continue

        # Old installers in download/desktop (> 30 days or repeated)
        if file_type == "Installer" and any(p in {"downloads", "download", "desktop", "temp"} for p in file_info.parent_dirs_lower):
            days_old = (datetime.datetime.now().timestamp() - file_info.mtime) / 86400
            if days_old > 30 or re.search(r"\(\d+\)", name_lower):
                item = AuditItem(
                    file_info=file_info,
                    category=ActionCategory.KANDIDAT_HAPUS,
                    risk_level=RiskLevel.SEDANG,
                    reason=f"Installer lama/duplikat ({int(days_old)} hari lalu di {file_info.parent_dirs_lower[-1] if file_info.parent_dirs_lower else 'root'})",
                )
                items.append(item)
                total_potential_savings += file_info.size
                continue

        # Priority 4: Misplaced files (Salah Lokasi)
        is_misplaced, suggested_target, misplaced_reason = detect_misplaced_file(file_info, is_gis, is_project)
        if is_misplaced and suggested_target:
            item = AuditItem(
                file_info=file_info,
                category=ActionCategory.SALAH_LOKASI,
                risk_level=RiskLevel.AMAN,
                reason=misplaced_reason or "Lokasi file kurang sesuai dengan kategorinya",
                suggested_target_path=suggested_target,
            )
            items.append(item)
            continue

        # Priority 5: Archive candidates (Very old files > 365 days in active folders)
        days_old = (datetime.datetime.now().timestamp() - file_info.mtime) / 86400
        if days_old > 365 and any(p in {"desktop", "downloads"} for p in file_info.parent_dirs_lower):
            item = AuditItem(
                file_info=file_info,
                category=ActionCategory.ARSIPKAN,
                risk_level=RiskLevel.AMAN,
                reason=f"File lama tidak dimodifikasi selama {int(days_old)} hari menumpuk di {file_info.parent_dirs_lower[-1]}",
                suggested_target_path="Archives/Old_Files",
            )
            items.append(item)
            continue

        # Priority 6: Ambiguous / Needs Review (Unknown extensions, unusual large files)
        if not file_type and file_info.size > 50 * 1024 * 1024:  # > 50 MB
            item = AuditItem(
                file_info=file_info,
                category=ActionCategory.PERLU_REVIEW,
                risk_level=RiskLevel.SEDANG,
                reason=f"File berukuran besar ({file_info.size} bytes) dengan tipe tidak dikenal ({file_info.extension})",
            )
            items.append(item)
            continue

        # Default: PERTAHANKAN (Keep in place)
        item = AuditItem(
            file_info=file_info,
            category=ActionCategory.PERTAHANKAN,
            risk_level=RiskLevel.AMAN,
            reason="Bagian dari dataset/proyek atau struktur berkas terorganisir dengan baik",
        )
        items.append(item)

    # Organize items into categories
    for item in items:
        items_by_cat[item.category].append(item)
        cat_counts[item.category] += 1

    return ClassificationReport(
        items=items,
        items_by_category=items_by_cat,
        duplicate_groups=duplicate_info_groups,
        total_potential_space_savings=total_potential_savings,
        category_counts=cat_counts,
        empty_directories=scan_result.empty_directories,
    )
