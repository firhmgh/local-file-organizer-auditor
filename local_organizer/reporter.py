"""
Report Generator for Markdown (LOCAL_FILE_AUDIT.md) and JSON (LOCAL_FILE_AUDIT.json).
V3: Context-Aware, GIS Dataset Aware, and Project Bundle Aware.
"""
import json
import datetime
from pathlib import Path
from typing import Any, Dict, List

from local_organizer.config import ActionCategory
from local_organizer.scanner import ScanResult
from local_organizer.classifier import ClassificationReport, AuditItem
from local_organizer.utils import format_bytes, format_timestamp


def generate_audit_json(
    scan_result: ScanResult,
    report: ClassificationReport,
    output_path: Path,
) -> Path:
    """Generate structured machine-readable LOCAL_FILE_AUDIT.json."""
    data: Dict[str, Any] = {
        "metadata": {
            "tool_name": "local-file-organizer-auditor",
            "version": "3.0.0",
            "generated_at": datetime.datetime.now().isoformat(),
            "target_directory": str(scan_result.root_path),
            "total_files_scanned": scan_result.scanned_file_count,
            "total_size_bytes": scan_result.total_size_bytes,
            "total_size_human": format_bytes(scan_result.total_size_bytes),
            "potential_space_savings_bytes": report.total_potential_space_savings,
            "potential_space_savings_human": format_bytes(report.total_potential_space_savings),
        },
        "summary_by_category": {
            cat.value: report.category_counts[cat] for cat in ActionCategory
        },
        "empty_directories": [
            str(d.relative_to(scan_result.root_path)) for d in report.empty_directories
        ],
        "duplicate_groups_count": len(report.duplicate_groups),
        "items": [],
    }

    for item in report.items:
        data["items"].append({
            "relative_path": item.file_info.rel_path,
            "absolute_path": str(item.file_info.path),
            "category": item.category.value,
            "risk_level": item.risk_level.value,
            "reason": item.reason,
            "size_bytes": item.file_info.size,
            "size_human": format_bytes(item.file_info.size),
            "modified_time": format_timestamp(item.file_info.mtime),
            "is_protected": item.is_protected,
            "suggested_target_path": item.suggested_target_path,
            "duplicate_of": item.duplicate_of,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path


def generate_audit_markdown(
    scan_result: ScanResult,
    report: ClassificationReport,
    output_path: Path,
) -> Path:
    """Generate user-friendly, professional LOCAL_FILE_AUDIT.md report with V3 Project & GIS Bundle Awareness."""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md: List[str] = [
        "# Laporan Audit & Rekomendasi Organisasi File (Versi 3 - Project & Bundle Aware)",
        f"\n**Waktu Audit:** `{now_str}`  ",
        f"**Direktori Target:** `{scan_result.root_path}`  ",
        f"**Mode Eksekusi:** `Audit & Dry-Run (Non-Destructive)`\n",
        "---",
        "## 1. Ringkasan Eksekutif\n",
        "| Parameter | Nilai |",
        "| :--- | :--- |",
        f"| **Total Berkas Terpindai** | **{scan_result.scanned_file_count:,}** file |",
        f"| **Total Kapasitas Terpakai** | **{format_bytes(scan_result.total_size_bytes)}** |",
        f"| **Grup Duplikat Identik** | **{len(report.duplicate_groups)}** kelompok duplikat |",
        f"| **Duplikat Aman Mandiri (Recycle Bin)** | **{report.category_counts[ActionCategory.DUPLIKAT_AMAN]}** berkas mandiri |",
        f"| **Duplikat Kontekstual GIS** | **{report.category_counts[ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS]}** berkas terlindungi |",
        f"| **Duplikat Kontekstual Proyek/Aset** | **{report.category_counts[ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT]}** berkas terlindungi |",
        f"| **Potensi Penghematan Ruang Aman** | **{format_bytes(report.total_potential_space_savings)}** |",
        f"| **Folder Kosong Terdeteksi (Non-Proyek)** | **{len(report.empty_directories)}** folder |",
        "",
        "### Distribusi Kategori Status",
        "",
        "| Kategori | Jumlah Berkas | Keterangan Tindakan |",
        "| :--- | :--- | :--- |",
        f"| **PERTAHANKAN** | {report.category_counts[ActionCategory.PERTAHANKAN]} | Berkas berada di lokasi tepat dan terstruktur |",
        f"| **DUPLIKAT AMAN** | {report.category_counts[ActionCategory.DUPLIKAT_AMAN]} | 100% Identik Mandiri (PDF/Media/Salinan ganda pengguna), aman ke Recycle Bin |",
        f"| **DUPLIKAT KONTEKSTUAL GIS** | {report.category_counts[ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS]} | Komponen dataset GIS (`.shp`, `.prj`, `.dbf`, `.cpg`) (**DILINDUNGI**) |",
        f"| **DUPLIKAT KONTEKSTUAL PROJECT** | {report.category_counts[ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT]} | Aset web/export/aplikasi (`qgis2web`, css, images, js) (**DILINDUNGI**) |",
        f"| **SALAH LOKASI** | {report.category_counts[ActionCategory.SALAH_LOKASI]} | Berkas nyasar, disarankan relokasi ke folder yang sesuai |",
        f"| **KANDIDAT HAPUS** | {report.category_counts[ActionCategory.KANDIDAT_HAPUS]} | File temporary/cache (.tmp, .log usang) |",
        f"| **ARSIPKAN** | {report.category_counts[ActionCategory.ARSIPKAN]} | Berkas lama yang tidak aktif di folder kerja/desktop |",
        f"| **PERLU REVIEW** | {report.category_counts[ActionCategory.PERLU_REVIEW]} | Berkas berukuran besar / ekstensi asing, perlu tinjauan manual |",
        f"| **FILE SISTEM/KONFIGURASI** | {report.category_counts[ActionCategory.FILE_SISTEM_KONFIG]} | **DILINDUNGI** (.git, .env, dependencies, source code, db) |",
        "",
        "---",
        "## 2. Rincian Duplikat Aman vs Duplikat Kontekstual\n",
    ]

    safe_dups = report.items_by_category[ActionCategory.DUPLIKAT_AMAN]
    gis_dups = report.items_by_category[ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS]
    proj_dups = report.items_by_category[ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT]

    md.append(f"### A. Duplikat Aman untuk Pembersihan ({len(safe_dups)} Berkas)\n")
    if not safe_dups:
        md.append("_Tidak ada duplikat mandiri yang aman untuk dibersihkan otomatis._\n")
    else:
        md.append("| Berkas Duplikat | Ukuran | Master Copy yang Disimpan | Alasan Aman |")
        md.append("| :--- | :--- | :--- | :--- |")
        for item in safe_dups[:100]:
            md.append(f"| `{item.file_info.rel_path}` | {format_bytes(item.file_info.size)} | `{item.duplicate_of}` | {item.reason} |")
        if len(safe_dups) > 100:
            md.append(f"| *...dan {len(safe_dups) - 100} duplikat aman lainnya.* | | | *Lihat LOCAL_FILE_AUDIT.json untuk daftar lengkap.* |")
        md.append("")

    md.append(f"\n### B. Duplikat Kontekstual Dataset GIS ({len(gis_dups)} Berkas - DILINDUNGI)\n")
    if not gis_dups:
        md.append("_Tidak ada duplikat dataset GIS terdeteksi._\n")
    else:
        md.append("> **Peringatan Keamanan GIS:** Berkas sidecar `.cpg`, `.prj`, `.dbf`, `.shx` merupakan komponen integral dari dataset spasial yang berbeda. Berkas ini **TIDAK AKAN** dihapus agar layer peta tidak rusak.\n")
        md.append("| Berkas Komponen Dataset | Ukuran | Status Proteksi |")
        md.append("| :--- | :--- | :--- |")
        for item in gis_dups[:50]:
            md.append(f"| `{item.file_info.rel_path}` | {format_bytes(item.file_info.size)} | {item.reason} |")
        if len(gis_dups) > 50:
            md.append(f"| *...dan {len(gis_dups) - 50} berkas dataset GIS lainnya.* | | *Semua diproteksi penuh.* |")
        md.append("")

    md.append(f"\n### C. Duplikat Kontekstual Project / Bundle Export ({len(proj_dups)} Berkas - DILINDUNGI)\n")
    if not proj_dups:
        md.append("_Tidak ada duplikat aset proyek terdeteksi._\n")
    else:
        md.append("> **Peringatan Keamanan Proyek:** Berkas asset (gambar, icon, css, legend) pada export mandiri seperti `qgis2web` atau web app dibutuhkan agar setiap export dapat berjalan secara independen. Berkas ini **DILINDUNGI** dari pembersihan otomatis.\n")
        md.append("| Berkas Asset Proyek | Ukuran | Alasan Proteksi |")
        md.append("| :--- | :--- | :--- |")
        for item in proj_dups[:50]:
            md.append(f"| `{item.file_info.rel_path}` | {format_bytes(item.file_info.size)} | {item.reason} |")
        if len(proj_dups) > 50:
            md.append(f"| *...dan {len(proj_dups) - 50} aset proyek lainnya.* | | *Semua diproteksi penuh.* |")
        md.append("")

    md.extend([
        "---",
        "## 3. Berkas Salah Lokasi & Rekomendasi Struktur\n",
    ])

    misplaced_items = report.items_by_category[ActionCategory.SALAH_LOKASI]
    if not misplaced_items:
        md.append("_Semua berkas berada di lokasi yang sesuai._\n")
    else:
        md.append("| Berkas Saat Ini | Ukuran | Alasan | Usulan Folder Tujuan |")
        md.append("| :--- | :--- | :--- | :--- |")
        for item in misplaced_items[:100]:
            md.append(f"| `{item.file_info.rel_path}` | {format_bytes(item.file_info.size)} | {item.reason} | **`{item.suggested_target_path}/`** |")
        if len(misplaced_items) > 100:
            md.append(f"| *...dan {len(misplaced_items) - 100} berkas lainnya.* | | | *Lihat LOCAL_FILE_AUDIT.json.* |")
        md.append("")

    md.extend([
        "---",
        "## 4. Kandidat Pembersihan (Temporary & Cache Usang)\n",
    ])

    cleanup_items = report.items_by_category[ActionCategory.KANDIDAT_HAPUS]
    if not cleanup_items:
        md.append("_Tidak ditemukan berkas temporary atau installer usang._\n")
    else:
        md.append("| Berkas | Ukuran | Risiko | Alasan |")
        md.append("| :--- | :--- | :--- | :--- |")
        for item in cleanup_items:
            md.append(f"| `{item.file_info.rel_path}` | {format_bytes(item.file_info.size)} | `{item.risk_level.value}` | {item.reason} |")
        md.append("")

    md.extend([
        "---",
        "## 5. Berkas Sistem & Proyek Terlindungi (Immunity List)\n",
        "> **Jaminan Keamanan:** Berkas-berkas di bawah ini diidentifikasi sebagai komponen penting (source code, environment, dependency, atau konfigurasi IDE/sistem) dan **TIDAK AKAN PERNAH** dihapus atau dipindahkan secara otomatis.\n",
    ])

    protected_items = report.items_by_category[ActionCategory.FILE_SISTEM_KONFIG]
    if not protected_items:
        md.append("_Tidak ditemukan file sistem/konfigurasi khusus._\n")
    else:
        md.append(f"Total file terlindungi: **{len(protected_items)}** file.\n")
        md.append("| Berkas Terlindungi | Kategori Proteksi |")
        md.append("| :--- | :--- |")
        for item in protected_items[:30]:
            md.append(f"| `{item.file_info.rel_path}` | {item.reason} |")
        if len(protected_items) > 30:
            md.append(f"| *...dan {len(protected_items) - 30} berkas terlindungi lainnya.* | *Proteksi otomatis aktif.* |")
        md.append("")

    md.extend([
        "---",
        "## 6. Direktori Kosong Terdeteksi (Non-Proyek)\n",
    ])

    if not report.empty_directories:
        md.append("_Tidak ditemukan direktori kosong di luar struktur proyek._\n")
    else:
        for d in report.empty_directories:
            rel = str(d.relative_to(scan_result.root_path))
            md.append(f"- `{rel}/`")
        md.append("")

    md.extend([
        "---",
        "## 7. Panduan Tindakan Lanjutan\n",
        "1. **Tinjau Laporan:** Periksa daftar di atas untuk memastikan rekomendasi telah sesuai kebutuhan Anda.",
        "2. **Mode Cleanup (Jika Dikehendaki):** Jalankan perintah dengan flag `--apply-cleanup` dan `--confirm` untuk mengeksekusi pembersihan hanya pada `DUPLIKAT AMAN` dan `KANDIDAT HAPUS` ke Windows Recycle Bin.",
        "3. **Keamanan Ekstra:** Seluruh file `DUPLIKAT KONTEKSTUAL GIS`, `DUPLIKAT KONTEKSTUAL PROJECT`, dan `FILE SISTEM/KONFIGURASI` tetap **100% aman dan tidak tersentuh**.",
        "",
    ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    return output_path
