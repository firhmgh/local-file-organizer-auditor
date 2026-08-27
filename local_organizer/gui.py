"""
Desktop GUI Layer for Local File Organizer & Auditor (Windows Edition).
- Safe-by-Default: Integrates directly with core engine without altering logic.
- Background Threading: Prevents UI freezing during scan and cleanup.
- Interactive Dashboard: Real-time progress bar, summary cards, filterable results table.
- Non-destructive: Prohibits permanent delete; allows Recycle Bin cleanup ONLY for DUPLIKAT AMAN and KANDIDAT HAPUS after explicit user confirmation.
- Immune protection: FILE SISTEM/KONFIGURASI, GIS bundles, project bundles, and PERTAHANKAN files are completely locked.
"""
import os
import sys
import threading
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from local_organizer.config import ActionCategory, RiskLevel
from local_organizer.scanner import scan_directory, ScanResult
from local_organizer.hasher import find_duplicate_groups
from local_organizer.classifier import classify_files, ClassificationReport, AuditItem
from local_organizer.reporter import generate_audit_markdown, generate_audit_json
from local_organizer.cleanup import execute_cleanup, CleanupExecutionSummary
from local_organizer.utils import format_bytes, format_timestamp


class FileOrganizerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Local File Organizer & Auditor - Windows Desktop Edition")
        self.geometry("1180x760")
        self.minsize(980, 640)

        # Apply modern Windows style if available
        self.style = ttk.Style(self)
        available_themes = self.style.theme_names()
        if "vista" in available_themes:
            self.style.theme_use("vista")
        elif "clam" in available_themes:
            self.style.theme_use("clam")

        # Custom styling colors
        self.configure(bg="#F4F6F9")
        self.style.configure(".", font=("Segoe UI", 9))
        self.style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        self.style.configure("Card.TFrame", background="#FFFFFF", relief="ridge")

        # State Variables
        self.target_dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.status_var = tk.StringVar(value="Siap. Pilih folder target lalu klik 'Mulai Audit (Dry-Run)'.")
        self.progress_var = tk.DoubleVar(value=0.0)
        self.category_filter_var = tk.StringVar(value="SEMUA KATEGORI")

        self.is_processing = False
        self.last_scan_result: Optional[ScanResult] = None
        self.last_report: Optional[ClassificationReport] = None
        self.last_markdown_path: Optional[Path] = None

        self._build_ui()

    def _build_ui(self):
        # 1. Header Frame
        header_frame = tk.Frame(self, bg="#1E293B", padx=16, pady=12)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header_frame,
            text="Local File Organizer & Auditor",
            font=("Segoe UI", 14, "bold"),
            fg="#FFFFFF",
            bg="#1E293B",
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Non-destructive file & duplicate auditor dengan proteksi ketat sistem, GIS dataset, dan bundle proyek.",
            font=("Segoe UI", 9),
            fg="#94A3B8",
            bg="#1E293B",
        )
        subtitle_lbl.pack(anchor="w")

        # 2. Control Bar (Folder Selector & Action Buttons)
        control_frame = tk.Frame(self, bg="#FFFFFF", padx=16, pady=10, relief="groove", bd=1)
        control_frame.pack(fill=tk.X, padx=12, pady=(10, 6))

        tk.Label(control_frame, text="Folder Target:", font=("Segoe UI", 9, "bold"), bg="#FFFFFF").pack(side=tk.LEFT, padx=(0, 6))

        dir_entry = ttk.Entry(control_frame, textvariable=self.target_dir_var, font=("Segoe UI", 9))
        dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        browse_btn = ttk.Button(control_frame, text="Pilih Folder...", command=self._browse_directory)
        browse_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.audit_btn = tk.Button(
            control_frame,
            text="🔍 Mulai Audit (Dry-Run)",
            bg="#0284C7",
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self._start_audit_thread,
        )
        self.audit_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.report_btn = tk.Button(
            control_frame,
            text="📄 Buka Laporan",
            state=tk.DISABLED,
            bg="#E2E8F0",
            fg="#475569",
            font=("Segoe UI", 9),
            padx=10,
            pady=4,
            relief="flat",
            command=self._open_markdown_report,
        )
        self.report_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.cleanup_btn = tk.Button(
            control_frame,
            text="🗑️ Eksekusi Cleanup (Recycle Bin)",
            state=tk.DISABLED,
            bg="#DC2626",
            fg="#FFFFFF",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            relief="flat",
            cursor="hand2",
            command=self._confirm_and_run_cleanup,
        )
        self.cleanup_btn.pack(side=tk.RIGHT)

        # 3. Summary Cards Frame
        cards_container = tk.Frame(self, bg="#F4F6F9")
        cards_container.pack(fill=tk.X, padx=12, pady=4)

        self.card_labels: Dict[str, tk.Label] = {}
        card_specs = [
            ("total_files", "Total File", "0", "#0F172A"),
            ("total_size", "Total Kapasitas", "0 B", "#0F172A"),
            ("safe_dups", "Duplikat Aman", "0 berkas", "#16A34A"),
            ("gis_dups", "Duplikat GIS (Kebal)", "0 berkas", "#D97706"),
            ("proj_dups", "Aset Proyek (Kebal)", "0 berkas", "#0284C7"),
            ("misplaced", "Salah Lokasi", "0 berkas", "#9333EA"),
            ("candidates_del", "Kandidat Hapus", "0 berkas", "#DC2626"),
            ("savings", "Potensi Hemat Aman", "0 B", "#16A34A"),
        ]

        for idx, (key, title, default_val, text_color) in enumerate(card_specs):
            card = tk.Frame(cards_container, bg="#FFFFFF", relief="solid", bd=1, padx=8, pady=6)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)

            tk.Label(card, text=title, font=("Segoe UI", 8), fg="#64748B", bg="#FFFFFF").pack(anchor="w")
            val_lbl = tk.Label(card, text=default_val, font=("Segoe UI", 10, "bold"), fg=text_color, bg="#FFFFFF")
            val_lbl.pack(anchor="w")
            self.card_labels[key] = val_lbl

        # 4. Table Filter & Controls
        filter_frame = tk.Frame(self, bg="#F4F6F9")
        filter_frame.pack(fill=tk.X, padx=12, pady=(8, 4))

        tk.Label(filter_frame, text="Filter Kategori Tampilan:", font=("Segoe UI", 9, "bold"), bg="#F4F6F9").pack(side=tk.LEFT, padx=(0, 6))

        self.filter_combobox = ttk.Combobox(
            filter_frame,
            textvariable=self.category_filter_var,
            state="readonly",
            values=[
                "SEMUA KATEGORI",
                ActionCategory.DUPLIKAT_AMAN.value,
                ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS.value,
                ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT.value,
                ActionCategory.SALAH_LOKASI.value,
                ActionCategory.KANDIDAT_HAPUS.value,
                ActionCategory.PERTAHANKAN.value,
                ActionCategory.FILE_SISTEM_KONFIG.value,
            ],
            width=32,
        )
        self.filter_combobox.pack(side=tk.LEFT)
        self.filter_combobox.bind("<<ComboboxSelected>>", lambda e: self._refresh_table_view())

        self.table_count_lbl = tk.Label(filter_frame, text="Menampilkan: 0 item", font=("Segoe UI", 9), fg="#64748B", bg="#F4F6F9")
        self.table_count_lbl.pack(side=tk.RIGHT)

        # 5. Interactive Results Table (Treeview)
        table_frame = tk.Frame(self, bg="#FFFFFF", relief="solid", bd=1)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        columns = ("rel_path", "category", "size", "risk", "reason", "duplicate_of", "suggested_target")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("rel_path", text="Path Berkas")
        self.tree.heading("category", text="Kategori")
        self.tree.heading("size", text="Ukuran")
        self.tree.heading("risk", text="Tingkat Risiko")
        self.tree.heading("reason", text="Alasan Analisis")
        self.tree.heading("duplicate_of", text="Master Copy")
        self.tree.heading("suggested_target", text="Target Relokasi")

        self.tree.column("rel_path", width=260, anchor="w")
        self.tree.column("category", width=140, anchor="center")
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("risk", width=90, anchor="center")
        self.tree.column("reason", width=280, anchor="w")
        self.tree.column("duplicate_of", width=180, anchor="w")
        self.tree.column("suggested_target", width=120, anchor="w")

        v_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Tags for row coloring
        self.tree.tag_configure("safe_dup", foreground="#15803D", background="#F0FDF4")
        self.tree.tag_configure("gis_dup", foreground="#B45309", background="#FFFBEB")
        self.tree.tag_configure("proj_dup", foreground="#0369A1", background="#F0F9FF")
        self.tree.tag_configure("cand_del", foreground="#B91C1C", background="#FEF2F2")
        self.tree.tag_configure("misplaced", foreground="#7E22CE", background="#FAF5FF")
        self.tree.tag_configure("protected", foreground="#475569", background="#F8FAFC")

        # 6. Footer / Status Bar
        status_bar = tk.Frame(self, bg="#E2E8F0", padx=12, pady=6)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress_bar = ttk.Progressbar(status_bar, variable=self.progress_var, maximum=100.0, length=180)
        self.progress_bar.pack(side=tk.RIGHT, padx=(10, 0))

        status_lbl = tk.Label(status_bar, textvariable=self.status_var, font=("Segoe UI", 9), fg="#1E293B", bg="#E2E8F0")
        status_lbl.pack(side=tk.LEFT, fill=tk.X)

    def _browse_directory(self):
        chosen = filedialog.askdirectory(initialdir=self.target_dir_var.get() or str(Path.home()))
        if chosen:
            self.target_dir_var.set(str(Path(chosen)))

    def _set_ui_state_busy(self, busy: bool):
        self.is_processing = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.audit_btn.config(state=state)
        if busy:
            self.cleanup_btn.config(state=tk.DISABLED)
            self.report_btn.config(state=tk.DISABLED)
        else:
            if self.last_report:
                safe_count = self.last_report.category_counts.get(ActionCategory.DUPLIKAT_AMAN, 0)
                cand_count = self.last_report.category_counts.get(ActionCategory.KANDIDAT_HAPUS, 0)
                self.cleanup_btn.config(state=tk.NORMAL if (safe_count + cand_count > 0) else tk.DISABLED)
                self.report_btn.config(state=tk.NORMAL if self.last_markdown_path else tk.DISABLED)

    def _start_audit_thread(self):
        target_path = Path(self.target_dir_var.get().strip())
        if not target_path.exists() or not target_path.is_dir():
            messagebox.showerror("Error", f"Direktori target tidak valid atau tidak ditemukan:\n{target_path}")
            return

        self._set_ui_state_busy(True)
        self.progress_var.set(0)
        self.status_var.set(f"Memindai direktori: {target_path}...")

        threading.Thread(target=self._run_audit_worker, args=(target_path,), daemon=True).start()

    def _run_audit_worker(self, target_path: Path):
        try:
            # 1. Scanner
            def scan_cb(count, current_p):
                self.after(0, lambda: self.status_var.set(f"Memindai berkas ({count:,} ditemukan)..."))

            scan_res = scan_directory(target_path, progress_callback=scan_cb)

            # 2. Hasher
            def hash_cb(processed, total, msg):
                pct = (processed / total * 100.0) if total > 0 else 0
                self.after(0, lambda: (self.progress_var.set(pct), self.status_var.set(f"Menganalisis hash ({processed:,}/{total:,}): {msg}")))

            dup_groups = find_duplicate_groups(scan_res.files_by_size, progress_callback=hash_cb)

            # 3. Classifier
            self.after(0, lambda: self.status_var.set("Mengklasifikasikan berkas & mendeteksi bundle proyek/GIS..."))
            report = classify_files(scan_res, dup_groups)

            # 4. Generate report in reports/gui_audit/
            reports_dir = Path("reports") / "gui_audit"
            reports_dir.mkdir(parents=True, exist_ok=True)
            md_path = reports_dir / "LOCAL_FILE_AUDIT.md"
            json_path = reports_dir / "LOCAL_FILE_AUDIT.json"

            generate_audit_markdown(scan_res, report, md_path)
            generate_audit_json(scan_res, report, json_path)

            self.last_scan_result = scan_res
            self.last_report = report
            self.last_markdown_path = md_path

            self.after(0, self._on_audit_success)

        except Exception as e:
            self.after(0, lambda err=e: self._on_audit_error(err))

    def _on_audit_success(self):
        self._set_ui_state_busy(False)
        self.progress_var.set(100.0)
        self.status_var.set("Audit selesai (Mode Dry-Run). Tidak ada berkas yang diubah.")

        if not self.last_scan_result or not self.last_report:
            return

        res = self.last_scan_result
        rep = self.last_report

        # Update Summary Cards
        self.card_labels["total_files"].config(text=f"{res.scanned_file_count:,}")
        self.card_labels["total_size"].config(text=format_bytes(res.total_size_bytes))
        self.card_labels["safe_dups"].config(text=f"{rep.category_counts.get(ActionCategory.DUPLIKAT_AMAN, 0):,} berkas")
        self.card_labels["gis_dups"].config(text=f"{rep.category_counts.get(ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS, 0):,} berkas")
        self.card_labels["proj_dups"].config(text=f"{rep.category_counts.get(ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT, 0):,} berkas")
        self.card_labels["misplaced"].config(text=f"{rep.category_counts.get(ActionCategory.SALAH_LOKASI, 0):,} berkas")
        self.card_labels["candidates_del"].config(text=f"{rep.category_counts.get(ActionCategory.KANDIDAT_HAPUS, 0):,} berkas")
        self.card_labels["savings"].config(text=format_bytes(rep.total_potential_space_savings))

        self._refresh_table_view()

    def _on_audit_error(self, err: Exception):
        self._set_ui_state_busy(False)
        self.status_var.set(f"Error selama audit: {err}")
        messagebox.showerror("Audit Error", f"Terjadi kesalahan selama proses audit:\n{err}")

    def _refresh_table_view(self):
        # Clear existing rows
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        if not self.last_report:
            self.table_count_lbl.config(text="Menampilkan: 0 item")
            return

        selected_cat = self.category_filter_var.get()
        items_to_show: List[AuditItem] = []

        for item in self.last_report.items:
            if selected_cat == "SEMUA KATEGORI" or item.category.value == selected_cat:
                items_to_show.append(item)

        for item in items_to_show:
            tag = "protected"
            if item.category == ActionCategory.DUPLIKAT_AMAN:
                tag = "safe_dup"
            elif item.category == ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS:
                tag = "gis_dup"
            elif item.category == ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT:
                tag = "proj_dup"
            elif item.category == ActionCategory.KANDIDAT_HAPUS:
                tag = "cand_del"
            elif item.category == ActionCategory.SALAH_LOKASI:
                tag = "misplaced"

            self.tree.insert(
                "",
                tk.END,
                values=(
                    item.file_info.rel_path,
                    item.category.value,
                    format_bytes(item.file_info.size),
                    item.risk_level.value,
                    item.reason,
                    item.duplicate_of or "-",
                    item.suggested_target_path or "-",
                ),
                tags=(tag,),
            )

        self.table_count_lbl.config(text=f"Menampilkan: {len(items_to_show):,} item (dari {len(self.last_report.items):,})")

    def _open_markdown_report(self):
        if self.last_markdown_path and self.last_markdown_path.exists():
            try:
                if os.name == "nt":
                    os.startfile(str(self.last_markdown_path))
                else:
                    subprocess.Popen(["xdg-open", str(self.last_markdown_path)])
            except Exception as e:
                messagebox.showerror("Error", f"Gagal membuka berkas laporan:\n{e}")

    def _confirm_and_run_cleanup(self):
        if not self.last_report or not self.last_scan_result:
            return

        safe_dups = self.last_report.items_by_category.get(ActionCategory.DUPLIKAT_AMAN, [])
        cand_del = self.last_report.items_by_category.get(ActionCategory.KANDIDAT_HAPUS, [])
        total_items = len(safe_dups) + len(cand_del)

        if total_items == 0:
            messagebox.showinfo("Informasi", "Tidak ada item DUPLIKAT AMAN atau KANDIDAT HAPUS untuk dibersihkan.")
            return

        total_bytes = sum(i.file_info.size for i in safe_dups) + sum(i.file_info.size for i in cand_del)

        confirm_msg = (
            f"KONFIRMASI PEMBERSIHAN AMAN:\n\n"
            f"• {len(safe_dups)} berkas DUPLIKAT AMAN\n"
            f"• {len(cand_del)} berkas KANDIDAT HAPUS (Temporary/Cache)\n"
            f"• Total ruang yang dibebaskan: {format_bytes(total_bytes)}\n\n"
            f"⚠️ Jaminan Keamanan:\n"
            f"- Seluruh berkas HANYA akan dipindahkan ke WINDOWS RECYCLE BIN.\n"
            f"- File Master, GIS Sidecars, Aset Proyek/Export, dan File Sistem 100% KEBAL.\n\n"
            f"Apakah Anda yakin ingin memindahkan {total_items} berkas ke Recycle Bin?"
        )

        if not messagebox.askyesno("Konfirmasi Windows Recycle Bin", confirm_msg, icon="warning"):
            return

        self._set_ui_state_busy(True)
        self.status_var.set("Menjalankan pembersihan aman ke Windows Recycle Bin...")

        threading.Thread(target=self._run_cleanup_worker, daemon=True).start()

    def _run_cleanup_worker(self):
        try:
            summary: CleanupExecutionSummary = execute_cleanup(
                self.last_scan_result,
                self.last_report,
                clean_duplicates=True,
                clean_temp_files=True,
                relocate_misplaced=False,
                remove_empty_dirs=False,
            )
            self.after(0, lambda s=summary: self._on_cleanup_complete(s))
        except Exception as e:
            self.after(0, lambda err=e: self._on_cleanup_error(err))

    def _on_cleanup_complete(self, summary: CleanupExecutionSummary):
        self._set_ui_state_busy(False)
        self.status_var.set(f"Pembersihan selesai: {len(summary.trashed_files)} berkas dipindahkan ke Recycle Bin ({format_bytes(summary.bytes_freed)} dibebaskan).")

        msg = (
            f"Pembersihan Berhasil Selesai!\n\n"
            f"• Berkas dipindahkan ke Recycle Bin: {len(summary.trashed_files)} berkas\n"
            f"• Total ruang dibebaskan: {format_bytes(summary.bytes_freed)}\n"
            f"• Berkas sistem/kebal diabaikan: {len(summary.skipped_protected_files)} berkas\n"
            f"• Error: {len(summary.errors)}\n\n"
            f"Seluruh berkas yang dibuang dapat dipulihkan kapan saja melalui Windows Recycle Bin."
        )
        messagebox.showinfo("Pembersihan Sukses", msg)

        # Automatically re-audit target folder to refresh UI state
        self._start_audit_thread()

    def _on_cleanup_error(self, err: Exception):
        self._set_ui_state_busy(False)
        self.status_var.set(f"Error pembersihan: {err}")
        messagebox.showerror("Cleanup Error", f"Terjadi kesalahan saat memindahkan ke Recycle Bin:\n{err}")


def launch_gui():
    """Main launcher entrypoint for the desktop GUI."""
    app = FileOrganizerApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
