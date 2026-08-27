"""
Unit tests for multi-tier hashing and duplicate detection.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from local_organizer.hasher import (
    compute_partial_hash,
    compute_full_hash,
    find_duplicate_groups,
)


class TestHasher(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_same_name_different_content(self):
        """Files with same name in different subfolders but different content must NOT be duplicates."""
        dir1 = self.test_dir / "folder1"
        dir2 = self.test_dir / "folder2"
        dir1.mkdir()
        dir2.mkdir()

        f1 = dir1 / "notes.txt"
        f2 = dir2 / "notes.txt"

        f1.write_text("Isi catatan pertama", encoding="utf-8")
        f2.write_text("Isi catatan kedua yang sangat berbeda!", encoding="utf-8")

        files_by_size = {
            f1.stat().st_size: [f1],
            f2.stat().st_size: [f2],
        }
        # If sizes differ, size grouping handles it
        dup_groups = find_duplicate_groups(files_by_size)
        self.assertEqual(len(dup_groups), 0)

    def test_different_name_same_content(self):
        """Files with completely different names but identical content MUST be detected as duplicate."""
        f1 = self.test_dir / "original_image.png"
        f2 = self.test_dir / "salinan_foto_download_2.png"

        dummy_data = b"DUMMY_BINARY_DATA_IMAGE_12345" * 200
        f1.write_bytes(dummy_data)
        f2.write_bytes(dummy_data)

        files_by_size = {
            f1.stat().st_size: [f1, f2]
        }

        dup_groups = find_duplicate_groups(files_by_size)
        self.assertEqual(len(dup_groups), 1)
        group_files = list(dup_groups.values())[0]
        self.assertEqual(len(group_files), 2)
        self.assertIn(f1, group_files)
        self.assertIn(f2, group_files)

    def test_same_size_different_content_partial_hash(self):
        """Files with exact same size but different header bytes must be rejected quickly."""
        f1 = self.test_dir / "data1.bin"
        f2 = self.test_dir / "data2.bin"

        f1.write_bytes(b"A" * 5000)
        f2.write_bytes(b"B" * 5000)

        files_by_size = {
            5000: [f1, f2]
        }
        dup_groups = find_duplicate_groups(files_by_size)
        self.assertEqual(len(dup_groups), 0)


if __name__ == "__main__":
    unittest.main()
