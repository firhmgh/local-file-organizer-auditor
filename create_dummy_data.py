"""
Helper script to generate a rich dummy test workspace for demonstration and manual auditing.
"""
from pathlib import Path
import shutil


def create_dummy_workspace(base_dir: str | Path = "dummy_test_workspace") -> Path:
    root = Path(base_dir).resolve()
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)

    # 1. Protected Files & Directories
    git_dir = root / ".git" / "objects"
    git_dir.mkdir(parents=True, exist_ok=True)
    (git_dir / "pack-123.pack").write_bytes(b"GIT_INTERNAL_OBJECT_DATA" * 50)
    (root / ".env").write_text("DATABASE_URL=postgres://user:pass@localhost:5432/db", encoding="utf-8")
    (root / "app_config.sqlite").write_bytes(b"SQLITE3_HEADER_DATA" * 20)

    node_mod = root / "node_modules" / "lodash"
    node_mod.mkdir(parents=True, exist_ok=True)
    (node_mod / "index.js").write_text("module.exports = {};", encoding="utf-8")

    proj_src = root / "Projects" / "MyProject"
    proj_src.mkdir(parents=True, exist_ok=True)
    (proj_src / "main.py").write_text("print('hello world')", encoding="utf-8")
    (proj_src / "requirements.txt").write_text("requests>=2.31.0\n", encoding="utf-8")

    # 2. Duplicate across different folders with different names (Exact SHA-256 duplicate)
    doc_dir = root / "Documents"
    doc_dir.mkdir(parents=True, exist_ok=True)
    shared_report_content = b"LAPORAN_KEUANGAN_RESMI_2026_VERSION_FINAL" * 100

    (doc_dir / "Laporan_Keuangan_2026.pdf").write_bytes(shared_report_content)

    dl_dir = root / "Downloads"
    dl_dir.mkdir(parents=True, exist_ok=True)
    (dl_dir / "Laporan_Keuangan_2026 (1).pdf").write_bytes(shared_report_content)

    # 3. Same filename but different content (Should NOT be duplicate)
    sub1 = root / "FolderA"
    sub2 = root / "FolderB"
    sub1.mkdir(parents=True, exist_ok=True)
    sub2.mkdir(parents=True, exist_ok=True)
    (sub1 / "readme.txt").write_text("Konten A yang spesifik", encoding="utf-8")
    (sub2 / "readme.txt").write_text("Konten B yang sama sekali berbeda", encoding="utf-8")

    # 4. Misplaced files
    # Video placed inside Documents
    (doc_dir / "vlog_liburan_bali.mp4").write_bytes(b"VIDEO_HEADER_MP4" * 1000)
    # Screenshot on Desktop
    desktop_dir = root / "Desktop"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    (desktop_dir / "Screenshot_2026_meeting.png").write_bytes(b"PNG_IMAGE_BYTES" * 200)

    # 5. Temporary files and installer
    (dl_dir / "temp_cache.tmp").write_bytes(b"CACHE_TEMP" * 50)
    (dl_dir / "old_setup_v1 (1).exe").write_bytes(b"EXE_INSTALLER" * 500)

    # 6. Empty directory
    empty_d = root / "OldEmptyFolder" / "SubEmpty"
    empty_d.mkdir(parents=True, exist_ok=True)

    print(f"[OK] Dummy test workspace successfully created at: {root}")
    return root


if __name__ == "__main__":
    create_dummy_workspace()
