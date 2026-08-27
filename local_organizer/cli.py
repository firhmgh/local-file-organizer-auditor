"""
Command-line Interface (CLI) for Local File Organizer & Auditor.
"""
import sys
import argparse
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    # Use standard console with safe fallback
    console = Console(highlight=False, legacy_windows=False)
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

from local_organizer.config import ActionCategory
from local_organizer.scanner import scan_directory
from local_organizer.hasher import find_duplicate_groups
from local_organizer.classifier import classify_files
from local_organizer.reporter import generate_audit_markdown, generate_audit_json
from local_organizer.cleanup import execute_cleanup
from local_organizer.utils import format_bytes


def print_banner():
    title = "========================================================\n" \
            "   LOCAL FILE ORGANIZER & AUDITOR (Windows Edition)\n" \
            "      Non-Destructive Local File & Folder Auditor\n" \
            "========================================================"
    if HAS_RICH:
        console.print(Panel(
            "[bold cyan]LOCAL FILE ORGANIZER & AUDITOR[/bold cyan]\n"
            "[italic green]Non-Destructive Local File & Folder Audit & Duplicate Detector[/italic green]",
            border_style="cyan"
        ))
    else:
        print(title)


def print_summary_table(scan_res, report):
    if HAS_RICH:
        table = Table(title="Ringkasan Hasil Audit V3 (Project & Bundle Aware)", border_style="blue")
        table.add_column("Kategori", style="bold")
        table.add_column("Jumlah Berkas", justify="right")
        table.add_column("Status Tindakan", style="dim")

        table.add_row("PERTAHANKAN", str(report.category_counts[ActionCategory.PERTAHANKAN]), "[green]Lokasi Tepat / Terorganisir[/green]")
        table.add_row("DUPLIKAT AMAN", str(report.category_counts[ActionCategory.DUPLIKAT_AMAN]), "[bold green]100% Identik Mandiri (Aman Recycle Bin)[/bold green]")
        table.add_row("DUPLIKAT KONTEKSTUAL GIS", str(report.category_counts[ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS]), "[yellow]Dataset GIS Sidecar (DILINDUNGI)[/yellow]")
        table.add_row("DUPLIKAT KONTEKSTUAL PROJECT", str(report.category_counts[ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT]), "[cyan]Aset Proyek / Web Export (DILINDUNGI)[/cyan]")
        table.add_row("SALAH LOKASI", str(report.category_counts[ActionCategory.SALAH_LOKASI]), "[magenta]Perlu Ditata Ulang[/magenta]")
        table.add_row("KANDIDAT HAPUS", str(report.category_counts[ActionCategory.KANDIDAT_HAPUS]), "[red]Temporary / Cache Usang[/red]")
        table.add_row("ARSIPKAN", str(report.category_counts[ActionCategory.ARSIPKAN]), "[blue]Berkas Lama (> 1 Thn)[/blue]")
        table.add_row("PERLU REVIEW", str(report.category_counts[ActionCategory.PERLU_REVIEW]), "[yellow]Tinjauan Manual[/yellow]")
        table.add_row("FILE SISTEM/KONFIGURASI", str(report.category_counts[ActionCategory.FILE_SISTEM_KONFIG]), "[bold green]KEBAL / DILINDUNGI[/bold green]")

        console.print(table)
        console.print(f"\n[bold]Total Berkas:[/bold] {scan_res.scanned_file_count} | [bold]Total Ukuran:[/bold] {format_bytes(scan_res.total_size_bytes)} | [bold cyan]Potensi Hemat Aman (Recycle Bin):[/bold cyan] [bold green]{format_bytes(report.total_potential_space_savings)}[/bold green]")
    else:
        print("\n--- RINGKASAN HASIL AUDIT ---")
        for cat in ActionCategory:
            print(f" - {cat.value:35}: {report.category_counts[cat]} berkas")
        print(f"Total Berkas: {scan_res.scanned_file_count} | Total Ukuran: {format_bytes(scan_res.total_size_bytes)} | Potensi Hemat Aman: {format_bytes(report.total_potential_space_savings)}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="local-organizer",
        description="Non-destructive file & folder auditor and duplicate detector with Recycle Bin safety.",
    )
    parser.add_argument(
        "--path", "-p",
        type=str,
        required=True,
        help="Path direktori lokal yang ingin diaudit.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=".",
        help="Direktori penyimpanan laporan LOCAL_FILE_AUDIT.md & .json (default: direktori saat ini).",
    )
    parser.add_argument(
        "--exclude-dirs",
        nargs="+",
        default=[],
        help="Nama folder tambahan yang ingin dikecualikan dari scan.",
    )
    parser.add_argument(
        "--exclude-exts",
        nargs="+",
        default=[],
        help="Ekstensi file yang ingin diabaikan (misal: .log .iso).",
    )
    parser.add_argument(
        "--whitelist-dirs",
        nargs="+",
        default=[],
        help="Hanya pindai subdirektori tertentu dalam path target.",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=0,
        help="Ukuran berkas minimum dalam bytes yang akan diperiksa.",
    )
    parser.add_argument(
        "--apply-cleanup",
        action="store_true",
        help="Aktifkan mode pembersihan file. CATATAN: Mode default adalah dry-run (hanya audit).",
    )
    parser.add_argument(
        "--relocate-misplaced",
        action="store_true",
        help="Pindahkan file yang salah lokasi ke folder yang direkomendasikan saat cleanup.",
    )
    parser.add_argument(
        "--remove-empty-dirs",
        action="store_true",
        help="Hapus direktori kosong yang ditemukan saat cleanup.",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Konfirmasi otomatis persetujuan cleanup tanpa prompt interaktif.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    print_banner()

    target_path = Path(args.path).resolve()
    if not target_path.exists():
        msg = f"[!] Error: Direktori target '{target_path}' tidak ditemukan!"
        if HAS_RICH:
            console.print(f"[bold red]{msg}[/bold red]")
        else:
            print(msg)
        sys.exit(1)

    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if HAS_RICH:
        console.print(f"[bold]Memulai pemindaian direktori:[/bold] `{target_path}`")
    else:
        print(f"Memulai pemindaian direktori: {target_path}")

    # 1. Scan directory
    scan_res = scan_directory(
        root_dir=target_path,
        excluded_dirs=set(args.exclude_dirs),
        excluded_extensions=set(args.exclude_exts),
        whitelist_dirs=set(args.whitelist_dirs),
        min_size_bytes=args.min_size,
    )

    # 2. Hash & detect duplicate groups
    if HAS_RICH:
        console.print(f"[bold]Menganalisis ukuran & menghitung SHA-256 duplicate candidates...[/bold]")
    dup_groups = find_duplicate_groups(scan_res.files_by_size)

    # 3. Classify & evaluate immunity
    report = classify_files(scan_res, dup_groups)

    # 4. Generate Reports
    md_file = out_dir / "LOCAL_FILE_AUDIT.md"
    json_file = out_dir / "LOCAL_FILE_AUDIT.json"

    generate_audit_markdown(scan_res, report, md_file)
    generate_audit_json(scan_res, report, json_file)

    print_summary_table(scan_res, report)

    if HAS_RICH:
        console.print(f"[bold green]Laporan audit berhasil dibuat:[/bold green]")
        console.print(f"   Markdown: [cyan]{md_file}[/cyan]")
        console.print(f"   JSON    : [cyan]{json_file}[/cyan]\n")
    else:
        print(f"Laporan berhasil dibuat:\n - {md_file}\n - {json_file}\n")

    # 5. Handle Cleanup if requested
    if args.apply_cleanup:
        if not args.confirm:
            if HAS_RICH:
                console.print("[bold yellow]PERINGATAN KONFIRMASI CLEANUP:[/bold yellow]")
                console.print("Tindakan ini akan memindahkan duplikat redundan & berkas sampah ke [bold cyan]Windows Recycle Bin[/bold cyan].")
                val = input("Ketik 'YA' untuk melanjutkan eksekusi: ").strip()
            else:
                val = input("Tindakan ini akan memindahkan duplikat ke Recycle Bin. Ketik 'YA' untuk lanjut: ").strip()

            if val.upper() != "YA":
                print("Operasi cleanup dibatalkan oleh pengguna.")
                return

        if HAS_RICH:
            console.print("[bold green]Mengeksekusi pembersihan aman (send2trash)...[/bold green]")
        
        summary = execute_cleanup(
            scan_result=scan_res,
            report=report,
            clean_duplicates=True,
            clean_temp_files=True,
            relocate_misplaced=args.relocate_misplaced,
            remove_empty_dirs=args.remove_empty_dirs,
        )

        if HAS_RICH:
            console.print(f"[bold green]Pembersihan Selesai![/bold green]")
            console.print(f" - Berkas dibuang ke Recycle Bin: [bold]{len(summary.trashed_files)}[/bold] berkas ({format_bytes(summary.bytes_freed)})")
            console.print(f" - Berkas direlokasi: [bold]{len(summary.relocated_files)}[/bold] berkas")
            console.print(f" - Berkas penting terlindungi (dilewati): [bold green]{len(summary.skipped_protected_files)}[/bold green]")
        else:
            print(f"Pembersihan selesai! {len(summary.trashed_files)} file dipindahkan ke Recycle Bin ({format_bytes(summary.bytes_freed)} dibebaskan).")
    else:
        if HAS_RICH:
            console.print("[dim]Mode audit selesai (Dry-run). Tidak ada berkas yang diubah, dihapus, atau dipindahkan.[/dim]")
            console.print("[dim]Gunakan flag `--apply-cleanup` jika Anda ingin mengeksekusi rekomendasi pembersihan.[/dim]")


if __name__ == "__main__":
    main()
