"""
Unit & Integration Tests for Desktop Tkinter GUI without deleting or touching real files.
"""
import unittest
from unittest.mock import MagicMock, patch
import tempfile
import shutil
from pathlib import Path

import tkinter as tk
from local_organizer.gui import FileOrganizerApp
from local_organizer.config import ActionCategory
from local_organizer.scanner import scan_directory
from local_organizer.hasher import find_duplicate_groups
from local_organizer.classifier import classify_files


class TestFileOrganizerGUI(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

        # Setup dummy test files
        (self.test_dir / "document.pdf").write_bytes(b"PDF_CONTENT_TEST" * 50)
        (self.test_dir / "document (1).pdf").write_bytes(b"PDF_CONTENT_TEST" * 50)

        # Gis dummy files
        gis_dir = self.test_dir / "GIS_Dataset"
        gis_dir.mkdir()
        (gis_dir / "layer.shp").write_bytes(b"SHP_GEOMETRY" * 30)
        (gis_dir / "layer.shx").write_bytes(b"SHX_INDEX" * 10)
        (gis_dir / "layer.dbf").write_bytes(b"DBF_DATA" * 30)
        (gis_dir / "layer.prj").write_bytes(b"WGS84" * 10)

        # Temporary files
        (self.test_dir / "cache.tmp").write_bytes(b"TEMP_CACHE_BYTES" * 20)

        # Initialize Tkinter root window in withdrawn mode (offscreen)
        self.app = FileOrganizerApp()
        self.app.withdraw()

    def tearDown(self):
        try:
            self.app.destroy()
        except Exception:
            pass
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gui_initial_state(self):
        """Verify initial UI variables and disabled states."""
        self.assertIsNotNone(self.app.target_dir_var.get())
        self.assertEqual(self.app.audit_btn["state"], tk.NORMAL)
        self.assertEqual(self.app.cleanup_btn["state"], tk.DISABLED)
        self.assertEqual(self.app.report_btn["state"], tk.DISABLED)

    def test_gui_audit_worker_and_table_population(self):
        """Verify audit worker executes properly and updates summary cards & table."""
        self.app.target_dir_var.set(str(self.test_dir))

        # Run worker directly to test synchronous execution on dummy directory
        self.app._run_audit_worker(self.test_dir)

        # Trigger completion handler
        self.app._on_audit_success()

        # Check that scan results and report were populated
        self.assertIsNotNone(self.app.last_scan_result)
        self.assertIsNotNone(self.app.last_report)

        report = self.app.last_report
        self.assertGreaterEqual(len(report.items), 5)

        # Verify summary cards updated
        self.assertIn("berkas", self.app.card_labels["safe_dups"].cget("text"))
        self.assertIn("berkas", self.app.card_labels["gis_dups"].cget("text"))

        # Verify treeview populated
        tree_items = self.app.tree.get_children()
        self.assertGreaterEqual(len(tree_items), 5)

        # Cleanup button must be enabled now since safe duplicates/temp exist
        self.assertEqual(self.app.cleanup_btn["state"], tk.NORMAL)

    def test_gui_filter_dropdown(self):
        """Verify selecting category filter alters table items correctly."""
        self.app.target_dir_var.set(str(self.test_dir))
        self.app._run_audit_worker(self.test_dir)
        self.app._on_audit_success()

        # Filter by DUPLIKAT AMAN
        self.app.category_filter_var.set(ActionCategory.DUPLIKAT_AMAN.value)
        self.app._refresh_table_view()

        tree_items = self.app.tree.get_children()
        self.assertEqual(len(tree_items), 1)  # document (1).pdf

        # Filter by KANDIDAT HAPUS
        self.app.category_filter_var.set(ActionCategory.KANDIDAT_HAPUS.value)
        self.app._refresh_table_view()

        tree_items = self.app.tree.get_children()
        self.assertEqual(len(tree_items), 1)  # cache.tmp

    @patch("local_organizer.cleanup.send2trash")
    @patch("local_organizer.gui.messagebox.askyesno", return_value=True)
    @patch("local_organizer.gui.messagebox.showinfo")
    def test_gui_cleanup_execution_mocked(self, mock_info, mock_ask, mock_trash):
        """Verify cleanup worker calls execute_cleanup and trashes only safe duplicates/temp."""
        self.app.target_dir_var.set(str(self.test_dir))
        self.app._run_audit_worker(self.test_dir)
        self.app._on_audit_success()

        # Run cleanup worker directly
        self.app._run_cleanup_worker()

        # send2trash should be called for safe dups and temp
        self.assertTrue(mock_trash.called)
        trashed_paths = [call[0][0] for call in mock_trash.call_args_list]

        # Verify GIS files and master copies were NOT trashed
        for p in trashed_paths:
            self.assertNotIn("layer.shp", p)
            self.assertNotIn("layer.prj", p)
            self.assertFalse(p.endswith("document.pdf"))  # Master must not be trashed


if __name__ == "__main__":
    unittest.main()
