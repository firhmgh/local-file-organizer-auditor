"""
Unit tests for classifier and immunity protection rules.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from local_organizer.config import ActionCategory, RiskLevel
from local_organizer.scanner import FileInfo, ScanResult
from local_organizer.classifier import (
    is_file_protected,
    detect_misplaced_file,
    classify_files,
)


class TestClassifier(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_protection_rules(self):
        """Verify that .git, .env, node_modules, source code, db are strictly protected."""
        # Case 1: .env file
        env_file = FileInfo(
            path=self.test_dir / ".env",
            rel_path=".env",
            size=50,
            mtime=1000.0,
            ctime=1000.0,
            extension="",
            name=".env",
            is_hidden=True,
            is_protected_location=False,
            parent_dirs_lower=[],
        )
        is_prot, reason = is_file_protected(env_file)
        self.assertTrue(is_prot)
        self.assertIn("esensial", reason.lower())

        # Case 2: inside .git directory
        git_blob = FileInfo(
            path=self.test_dir / ".git" / "objects" / "123",
            rel_path=".git/objects/123",
            size=120,
            mtime=1000.0,
            ctime=1000.0,
            extension="",
            name="123",
            is_hidden=True,
            is_protected_location=True,
            parent_dirs_lower=[".git", "objects"],
        )
        is_prot, reason = is_file_protected(git_blob)
        self.assertTrue(is_prot)

        # Case 3: inside node_modules
        node_file = FileInfo(
            path=self.test_dir / "node_modules" / "express" / "index.js",
            rel_path="node_modules/express/index.js",
            size=500,
            mtime=1000.0,
            ctime=1000.0,
            extension=".js",
            name="index.js",
            is_hidden=False,
            is_protected_location=True,
            parent_dirs_lower=["node_modules", "express"],
        )
        is_prot, reason = is_file_protected(node_file)
        self.assertTrue(is_prot)

        # Case 4: Database file
        db_file = FileInfo(
            path=self.test_dir / "app.sqlite",
            rel_path="app.sqlite",
            size=5000,
            mtime=1000.0,
            ctime=1000.0,
            extension=".sqlite",
            name="app.sqlite",
            is_hidden=False,
            is_protected_location=False,
            parent_dirs_lower=[],
        )
        is_prot, reason = is_file_protected(db_file)
        self.assertTrue(is_prot)

    def test_misplaced_detection(self):
        """Verify detection of misplaced videos in documents and screenshots."""
        # Video in Documents
        vid_in_docs = FileInfo(
            path=self.test_dir / "Documents" / "holiday_clip.mp4",
            rel_path="Documents/holiday_clip.mp4",
            size=15000000,
            mtime=1000.0,
            ctime=1000.0,
            extension=".mp4",
            name="holiday_clip.mp4",
            is_hidden=False,
            is_protected_location=False,
            parent_dirs_lower=["documents"],
        )
        is_mis, target, reason = detect_misplaced_file(vid_in_docs)
        self.assertTrue(is_mis)
        self.assertEqual(target, "Videos")

        # Screenshot on Desktop
        shot_on_desktop = FileInfo(
            path=self.test_dir / "Desktop" / "Screenshot_2026_01.png",
            rel_path="Desktop/Screenshot_2026_01.png",
            size=500000,
            mtime=1000.0,
            ctime=1000.0,
            extension=".png",
            name="Screenshot_2026_01.png",
            is_hidden=False,
            is_protected_location=False,
            parent_dirs_lower=["desktop"],
        )
        is_mis, target, reason = detect_misplaced_file(shot_on_desktop)
        self.assertTrue(is_mis)
        self.assertEqual(target, "Pictures/Screenshots")


if __name__ == "__main__":
    unittest.main()
