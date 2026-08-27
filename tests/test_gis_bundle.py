"""
Unit tests for GIS bundle awareness and project bundle (e.g. qgis2web) asset protection.
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from local_organizer.config import ActionCategory
from local_organizer.scanner import scan_directory
from local_organizer.hasher import find_duplicate_groups
from local_organizer.classifier import classify_files


class TestGISAndProjectBundleAwareness(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_gis_sidecars_protected_as_contextual_duplicates(self):
        """
        Verify that multiple GIS Shapefile packages with identical .cpg / .prj sidecar content
        are NOT flagged as DUPLIKAT_AMAN, but as DUPLIKAT_KONTEKSTUAL_GIS.
        """
        # Dataset 1: AFD02
        ds1 = self.test_dir / "Dataset1"
        ds1.mkdir()
        (ds1 / "AFD02.shp").write_bytes(b"SHP_GEOMETRY_1" * 50)
        (ds1 / "AFD02.shx").write_bytes(b"SHX_INDEX_1" * 20)
        (ds1 / "AFD02.dbf").write_bytes(b"DBF_TABLE_1" * 50)
        (ds1 / "AFD02.cpg").write_text("UTF-8", encoding="utf-8")
        (ds1 / "AFD02.prj").write_text("WGS 84 / UTM zone 47N", encoding="utf-8")

        # Dataset 2: AFD03
        ds2 = self.test_dir / "Dataset2"
        ds2.mkdir()
        (ds2 / "AFD03.shp").write_bytes(b"SHP_GEOMETRY_2" * 60)
        (ds2 / "AFD03.shx").write_bytes(b"SHX_INDEX_2" * 20)
        (ds2 / "AFD03.dbf").write_bytes(b"DBF_TABLE_2" * 60)
        (ds2 / "AFD03.cpg").write_text("UTF-8", encoding="utf-8")
        (ds2 / "AFD03.prj").write_text("WGS 84 / UTM zone 47N", encoding="utf-8")

        scan_res = scan_directory(self.test_dir)
        dup_groups = find_duplicate_groups(scan_res.files_by_size)
        report = classify_files(scan_res, dup_groups)

        # Assertion: GIS files must NOT be in DUPLIKAT_AMAN
        safe_dups = report.items_by_category[ActionCategory.DUPLIKAT_AMAN]
        self.assertEqual(len(safe_dups), 0, "GIS sidecar duplicates must NOT be classified as DUPLIKAT_AMAN")

        gis_dups = report.items_by_category[ActionCategory.DUPLIKAT_KONTEKSTUAL_GIS]
        self.assertGreaterEqual(len(gis_dups), 2)
        for item in gis_dups:
            self.assertIn("dataset geospasial", item.reason.lower())

    def test_qgis2web_export_assets_protected_as_project_duplicates(self):
        """
        Verify that multiple independent qgis2web web exports sharing identical UI assets
        (e.g., css/images/cancel.png, legend/layer.png, markers) are protected as DUPLIKAT_KONTEKSTUAL_PROJECT.
        """
        # Export 1
        exp1 = self.test_dir / "qgis2web_export_1" / "css" / "images"
        exp1.mkdir(parents=True)
        img_bytes = b"PNG_RULER_ICON_BYTES_123" * 20
        (exp1 / "rulers.png").write_bytes(img_bytes)

        # Export 2
        exp2 = self.test_dir / "qgis2web_export_2" / "css" / "images"
        exp2.mkdir(parents=True)
        (exp2 / "rulers.png").write_bytes(img_bytes)

        scan_res = scan_directory(self.test_dir)
        dup_groups = find_duplicate_groups(scan_res.files_by_size)
        report = classify_files(scan_res, dup_groups)

        safe_dups = report.items_by_category[ActionCategory.DUPLIKAT_AMAN]
        self.assertEqual(len(safe_dups), 0, "qgis2web assets must NOT be marked DUPLIKAT_AMAN")

        proj_dups = report.items_by_category[ActionCategory.DUPLIKAT_KONTEKSTUAL_PROJECT]
        self.assertEqual(len(proj_dups), 1)
        self.assertIn("qgis2web", proj_dups[0].reason.lower())

    def test_standalone_duplicate_correctly_classified_as_safe(self):
        """
        Verify that standalone files like PDF/DOCX or repeated downloads '(1)'
        ARE classified as DUPLIKAT_AMAN.
        """
        f1 = self.test_dir / "Laporan.pdf"
        f2 = self.test_dir / "Laporan (1).pdf"
        pdf_data = b"%PDF-1.4 DUMMY_REPORT" * 100
        f1.write_bytes(pdf_data)
        f2.write_bytes(pdf_data)

        scan_res = scan_directory(self.test_dir)
        dup_groups = find_duplicate_groups(scan_res.files_by_size)
        report = classify_files(scan_res, dup_groups)

        safe_dups = report.items_by_category[ActionCategory.DUPLIKAT_AMAN]
        self.assertEqual(len(safe_dups), 1)
        self.assertEqual(safe_dups[0].file_info.name, "Laporan (1).pdf")


if __name__ == "__main__":
    unittest.main()
