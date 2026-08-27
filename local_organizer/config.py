"""
Configuration rules, protected directory/file patterns, and categorization schemas.
"""
from enum import Enum
from typing import Dict, List, Set


class ActionCategory(str, Enum):
    PERTAHANKAN = "PERTAHANKAN"
    DUPLIKAT_AMAN = "DUPLIKAT AMAN"
    DUPLIKAT_KONTEKSTUAL_GIS = "DUPLIKAT KONTEKSTUAL GIS"
    DUPLIKAT_KONTEKSTUAL_PROJECT = "DUPLIKAT KONTEKSTUAL PROJECT/BUNDLE"
    DUPLIKAT_KONTEKSTUAL = "DUPLIKAT KONTEKSTUAL/DEPENDENCY"  # General fallback
    DUPLIKAT_IDENTIK = "DUPLIKAT IDENTIK"  # Legacy fallback
    SALAH_LOKASI = "SALAH LOKASI"
    PERLU_REVIEW = "PERLU REVIEW"
    FILE_SISTEM_KONFIG = "FILE SISTEM/KONFIGURASI"
    ARSIPKAN = "ARSIPKAN"
    KANDIDAT_HAPUS = "KANDIDAT HAPUS"


class RiskLevel(str, Enum):
    AMAN = "AMAN"
    RENDAH = "RENDAH"
    SEDANG = "SEDANG"
    TINGGI = "TINGGI"
    KRITIS = "KRITIS (DILINDUNGI)"


# Web / Project bundle folder signatures (e.g., qgis2web, laravel, flutter, vite, static sites)
PROJECT_BUNDLE_DIR_NAMES: Set[str] = {
    "css",
    "js",
    "assets",
    "images",
    "img",
    "markers",
    "legend",
    "fonts",
    "webfonts",
    "static",
    "public",
    "dist",
    "build",
    "resources",
    "storage",
    "components",
    "modules",
    "libs",
    "lib",
    "vendor",
    "node_modules",
    "templates",
    "views",
    "layouts",
    "qgis2web",
}


# GIS bundle extensions that belong to spatial datasets (Shapefile, GeoPackage, QGIS, etc.)
GIS_DATASET_EXTENSIONS: Set[str] = {
    ".shp",
    ".shx",
    ".dbf",
    ".prj",
    ".cpg",
    ".qpj",
    ".sbn",
    ".sbx",
    ".fbn",
    ".fbx",
    ".ain",
    ".aih",
    ".ixs",
    ".mxs",
    ".atx",
    ".xml",  # metadata sidecar in GIS
    ".qmd",
    ".qml",
    ".qlr",
    ".qgz",
    ".qgs",
    ".gpkg",
    ".gdb",
    ".kml",
    ".kmz",
    ".geojson",
    ".tif",
    ".tiff",
    ".tfw",
    ".ecw",
    ".ers",
}

# Standalone cleanable extensions (Safe standalone duplicate removal if byte-for-byte identical)
STANDALONE_CLEANABLE_EXTENSIONS: Set[str] = {
    ".pdf",
    ".docx",
    ".doc",
    ".xlsx",
    ".xls",
    ".pptx",
    ".ppt",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".bmp",
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".mp3",
    ".wav",
    ".zip",
    ".rar",
    ".7z",
    ".tar",
    ".gz",
}


# Protected folder names (any folder with these names, or subfolders within them, are protected)
PROTECTED_DIR_PATTERNS: Set[str] = {
    ".git",
    ".github",
    ".svn",
    ".hg",
    ".vscode",
    ".idea",
    "node_modules",
    "vendor",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "appdata",
    "windows",
    "system32",
    "syswow64",
    "program files",
    "program files (x86)",
    "programdata",
    "$recycle.bin",
    "system volume information",
    ".terraform",
    ".gradle",
    ".m2",
    "packages",
}

# Exact filenames that are protected from deletion or relocation
PROTECTED_EXACT_FILENAMES: Set[str] = {
    # Environment & Config
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.staging",
    ".gitignore",
    ".gitattributes",
    ".dockerignore",
    "dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.json",
    "composer.lock",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    "makefile",
    "cmakelists.txt",
    "tsconfig.json",
    "webpack.config.js",
    "vite.config.js",
    "vite.config.ts",
    # Windows system files
    "desktop.ini",
    "thumbs.db",
    "bootmgr",
    "bootsect.bak",
    "hiberfil.sys",
    "pagefile.sys",
    "swapfile.sys",
    "ntuser.dat",
}

# Protected extensions (e.g. database files, key files, certs)
PROTECTED_EXTENSIONS: Set[str] = {
    ".sqlite",
    ".sqlite3",
    ".db",
    ".db3",
    ".mdf",
    ".ldf",
    ".pem",
    ".key",
    ".crt",
    ".pfx",
    ".kdbx",
    ".lock",
    ".id_rsa",
    ".pub",
}

# Source code extensions
SOURCE_CODE_EXTENSIONS: Set[str] = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".java",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".dart",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".ps1",
    ".bat",
    ".cmd",
    ".sql",
    ".r",
    ".m",
    ".lua",
    ".vue",
    ".svelte",
}

# File type extension classification
EXTENSION_TYPE_MAP: Dict[str, str] = {
    # Documents
    ".pdf": "Dokumen",
    ".docx": "Dokumen",
    ".doc": "Dokumen",
    ".xlsx": "Dokumen",
    ".xls": "Dokumen",
    ".csv": "Dokumen",
    ".pptx": "Dokumen",
    ".ppt": "Dokumen",
    ".txt": "Dokumen",
    ".md": "Dokumen",
    ".odt": "Dokumen",
    ".ods": "Dokumen",
    ".odp": "Dokumen",
    ".rtf": "Dokumen",
    ".epub": "Dokumen",
    # Images / Photos
    ".jpg": "Foto",
    ".jpeg": "Foto",
    ".png": "Foto",
    ".webp": "Foto",
    ".gif": "Foto",
    ".bmp": "Foto",
    ".tiff": "Foto",
    ".svg": "Foto",
    ".raw": "Foto",
    ".cr2": "Foto",
    ".nef": "Foto",
    ".heic": "Foto",
    ".ico": "Foto",
    # Videos
    ".mp4": "Video",
    ".mkv": "Video",
    ".avi": "Video",
    ".mov": "Video",
    ".wmv": "Video",
    ".flv": "Video",
    ".webm": "Video",
    ".m4v": "Video",
    ".3gp": "Video",
    # Audio
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".aac": "Audio",
    ".ogg": "Audio",
    ".m4a": "Audio",
    ".wma": "Audio",
    # Archives
    ".zip": "Archive",
    ".rar": "Archive",
    ".7z": "Archive",
    ".tar": "Archive",
    ".gz": "Archive",
    ".bz2": "Archive",
    ".xz": "Archive",
    ".iso": "Archive",
    # Installers
    ".exe": "Installer",
    ".msi": "Installer",
    ".pkg": "Installer",
    ".dmg": "Installer",
    ".deb": "Installer",
    ".rpm": "Installer",
    ".apk": "Installer",
    # Temporary / Cache
    ".tmp": "Temporary",
    ".temp": "Temporary",
    ".log": "Temporary",
    ".bak": "Temporary",
    ".old": "Temporary",
    ".cache": "Temporary",
    ".crdownload": "Temporary",
    ".part": "Temporary",
}

# Recommended standard target folders for misplaced files
TARGET_FOLDER_MAPPINGS: Dict[str, str] = {
    "Dokumen": "Documents",
    "Foto": "Pictures",
    "Video": "Videos",
    "Audio": "Music",
    "Archive": "Archives",
    "Installer": "Installers",
    "Screenshot": "Pictures/Screenshots",
    "Tugas Kuliah": "Documents/Kuliah",
    "Pekerjaan": "Documents/Work",
    "Coding Projects": "Projects",
}

# Default chunk size for hashing
SMALL_CHUNK_SIZE = 4096  # 4 KB
FULL_HASH_CHUNK_SIZE = 65536  # 64 KB
