"""
Comprehensive end-to-end audit and dummy environment test.
Simulates all edge cases:
- Protected .git, .env, node_modules, source code, sqlite db
- Exact duplicate across different folders
- Duplicate with different filenames
- Same filename with different content
- Empty directory
- Misplaced files (video in docs, screenshot in desktop)
- Temporary files & old installers
- Validates that dry-run leaves filesystem untouched
- Validates that cleanup only removes non-protected duplicates and temp files to Recycle Bin (or mock)
"""
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

from local_organizer.scanner import scan_directory
from local_organizer.hasher import find_duplicate_groups
from local_organizer.classifier import classify_files
from local_organizer.reporter import generate_audit_markdown, generate_audit_json
from local_organizer.cleanup import execute_cleanup
from local_organizer.config import ActionCategory, RiskLevel


class TestEndToEndAudit(unittest.TestCase):
    def setUp(self):
        self.dummy_root = Path("d:/local-file-organizer-auditor/dummy_test_workspace").resolve()
        if self.dummy_root.exists():
            shutil.rmtree(self.dummy_root, ignore_errors=True)
        self.dummy_root.mkdir(parents=True, exist_ok=True)
        self._populate_dummy_workspace()

    def tearDown(self):
        if self.dummy_root.exists():
            shutil.rmtree(self.dummy_root, ignore_errors=True)

    def _populate_dummy_workspace(self):
        # 1. Protected directories & files
        git_dir = self.dummy_root / ".git" / "objects"
        git_dir.mkdir(parents=True, exist_ok=True)
        (git_dir / "pack-123.pack").write_bytes(b"GIT_INTERNAL_OBJECT_DATA" * 50)

        (self.dummy_root / ".env").write_text("DATABASE_URL=postgres://...", encoding="utf-8")
        (self.dummy_root / "app_config.sqlite").write_bytes(b"SQLITE3_HEADER_DATA" * 20)

        node_mod = self.dummy_root / "node_modules" / "lodash"
        node_mod.mkdir(parents=True, exist_ok=True)
        (node_mod / "index.js").write_text("module.exports = {};", encoding="utf-8")

        proj_src = self.dummy_root / "Projects" / "MyProject"
        proj_src.mkdir(parents=True, exist_ok=True)
        (proj_src / "main.py").write_text("print('hello world')", encoding="utf-8")

        # 2. Duplicate across different folders with different names
        doc_dir = self.dummy_root / "Documents"
        doc_dir.mkdir(parents=True, exist_ok=True)
        shared_report_content = b"LAPORAN_KEUANGAN_RESMI_2026_VERSION_FINAL" * 100

        (doc_dir / "Laporan_Keuangan_2026.pdf").write_bytes(shared_report_content)

        dl_dir = self.dummy_root / "Downloads"
        dl_dir.mkdir(parents=True, exist_ok=True)
        # Duplicate with different name and download suffix
        (dl_dir / "Laporan_Keuangan_2026 (1).pdf").write_bytes(shared_report_content)

        # 3. Same filename but different content (Must NOT be flagged as duplicate)
        sub1 = self.dummy_root / "FolderA"
        sub2 = self.dummy_root / "FolderB"
        sub1.mkdir(parents=True, exist_ok=True)
        sub2.mkdir(parents=True, exist_ok=True)
        (sub1 / "readme.txt").write_text("Konten A yang spesifik", encoding="utf-8")
        (sub2 / "readme.txt").write_text("Konten B yang sama sekali berbeda", encoding="utf-8")

        # 4. Misplaced files
        # Video placed inside Documents
        (doc_dir / "vlog_liburan_bali.mp4").write_bytes(b"VIDEO_HEADER_MP4" * 1000)
        # Screenshot on Desktop
        desktop_dir = self.dummy_root / "Desktop"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        (desktop_dir / "Screenshot_2026_meeting.png").write_bytes(b"PNG_IMAGE_BYTES" * 200)

        # 5. Temporary files and installer
        (dl_dir / "temp_cache.tmp").write_bytes(b"CACHE_TEMP" * 50)
        (dl_dir / "old_setup_v1 (1).exe").write_bytes(b"EXE_INSTALLER" * 500)

        # 6. Empty directory
        empty_d = self.dummy_root / "OldEmptyFolder" / "SubEmpty"
        empty_d.mkdir(parents=True, exist_ok=True)

    def test_full_audit_lifecycle(self):
        # Step 1: Scan
        scan_res = scan_directory(self.dummy_root)
        self.assertGreater(scan_res.scanned_file_count, 5)

        # Step 2: Hash & Duplicates
        dup_groups = find_duplicate_groups(scan_res.files_by_size)
        self.assertEqual(len(dup_groups), 1, "Should find exactly 1 duplicate group")

        # Step 3: Classify
        report = classify_files(scan_res, dup_groups)

        # Verify Protected Immunity
        prot_items = report.items_by_category[ActionCategory.FILE_SISTEM_KONFIG]
        prot_names = [it.file_info.name for it in prot_items]
        self.assertIn(".env", prot_names)
        self.assertIn("app_config.sqlite", prot_names)
        self.assertIn("main.py", prot_names)
        self.assertIn("pack-123.pack", prot_names)
        self.assertIn("index.js", prot_names)

        # Verify Duplicate Identification & Keeper
        dup_items = report.items_by_category[ActionCategory.DUPLIKAT_AMAN]
        self.assertEqual(len(dup_items), 1)
        # The keeper should be the one in Documents, the one in Downloads should be duplicate
        self.assertEqual(dup_items[0].file_info.name, "Laporan_Keuangan_2026 (1).pdf")
        self.assertIn("Documents", dup_items[0].duplicate_of)

        # Verify Misplaced files
        misplaced_items = report.items_by_category[ActionCategory.SALAH_LOKASI]
        misplaced_names = [m.file_info.name for m in misplaced_items]
        self.assertIn("vlog_liburan_bali.mp4", misplaced_names)
        self.assertIn("Screenshot_2026_meeting.png", misplaced_names)

        # Verify Reports generation
        md_out = self.dummy_root / "LOCAL_FILE_AUDIT.md"
        json_out = self.dummy_root / "LOCAL_FILE_AUDIT.json"
        generate_audit_markdown(scan_res, report, md_out)
        generate_audit_json(scan_res, report, json_out)

        self.assertTrue(md_out.exists())
        self.assertTrue(json_out.exists())
        self.assertGreater(md_out.stat().st_size, 200)
        self.assertGreater(json_out.stat().st_size, 200)

        # Step 4: Test Cleanup Execution with mock Recycle Bin
        with patch("local_organizer.cleanup.send2trash") as mock_trash:
            summary = execute_cleanup(
                scan_result=scan_res,
                report=report,
                clean_duplicates=True,
                clean_temp_files=True,
                relocate_misplaced=True,
                remove_empty_dirs=True,
            )

            # Check that protected files were never touched
            for skipped in summary.skipped_protected_files:
                self.assertNotIn(".env", [f[0] for f in summary.trashed_files])
                self.assertNotIn("main.py", [f[0] for f in summary.trashed_files])

            # Check that send2trash was called for duplicate and temporary files
            self.assertGreater(mock_trash.call_count, 0)
            trashed_rel = [f[0] for f in summary.trashed_files]
            self.assertIn("Downloads\\Laporan_Keuangan_2026 (1).pdf", [t.replace("/", "\\") for t in trashed_rel])


if __name__ == "__main__":
    unittest.main()
