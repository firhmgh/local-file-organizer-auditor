# Local File Organizer & Auditor (Windows Edition)

Tool CLI Python **non-destructive** profesional untuk mengaudit, mendeteksi duplikat identik, menganalisis file nyasar (salah lokasi), folder kosong, serta memberikan rekomendasi restrukturisasi direktori tanpa merusak atau mengubah isi file Anda.

Dirancang khusus dengan standar keamanan tinggi (**Safe by Default**) untuk lingkungan Windows:
- **Zero Accidental Deletion**: Tidak pernah melakukan *permanent delete* (menggunakan **Windows Recycle Bin** via `send2trash`).
- **Immunity System**: File sistem, dependency (`node_modules`, `venv`), file environment (`.env`), database (`.sqlite`, `.db`), source code, dan direktori `.git` **kebal 100%** terhadap rekomendasi hapus/pindah.
- **Dry-Run by Default**: Tahap audit pertama murni investigasi & pelaporan tanpa menyentuh struktur file Anda.

---

## 🌟 Fitur Utama

1. **Deteksi Duplikat Identik Bertingkat (Tiered Hashing)**
   - Filter awal berdasarkan ukuran berkas (*byte-level size match*).
   - *Partial Hashing* (SHA-256 pada header 4KB) untuk eliminasi cepat berkas berbeda isi.
   - *Full SHA-256 Hashing* untuk validasi 100% identik antar file meskipun nama atau tanggalnya berbeda.
   - Mendeteksi salinan identik dalam folder yang sama maupun lintas subfolder.

2. **Pemilihan File Utama Cerdas (*Intelligent Keeper Selector*)**
   - Tidak hanya memilih file tertua/terbaru secara acak.
   - Memilih file yang disimpan di folder terstruktur (`Documents/`, `Projects/`) dan membuang salinan yang menumpuk di folder `Downloads/` atau yang berakhiran `(1)`, `- Copy`, dsb.

3. **Klasifikasi Kategori Transparan & Context-Aware (V3)**
   - **`PERTAHANKAN`**: Berkas berada di lokasi tepat dan terstruktur.
   - **`DUPLIKAT AMAN`**: Salinan 100% redundan mandiri (PDF, DOCX, foto, video, salinan berulang `(1)`), aman dipindah ke Recycle Bin.
   - **`DUPLIKAT KONTEKSTUAL GIS`**: Sidecar dataset spasial (`.shp`, `.prj`, `.dbf`, `.cpg`, `.qmd`, `.qml`, `.gpkg`) yang **KEBAL DILINDUNGI**.
   - **`DUPLIKAT KONTEKSTUAL PROJECT`**: Aset dan resource internal proyek/export web (`qgis2web`, `css/images`, `legend`, `js`) yang **KEBAL DILINDUNGI**.
   - **`SALAH LOKASI`**: Berkas nyasar di root folder (misal video di folder dokumen, screenshot di desktop).
   - **`KANDIDAT HAPUS`**: Berkas temporary/cache (`.tmp`, `.part`, log usang).
   - **`ARSIPKAN`**: Berkas tidak aktif berusia > 1 tahun yang menumpuk di Desktop/Downloads.
   - **`PERLU REVIEW`**: Berkas ukuran besar (>50MB) atau tipe tidak dikenal yang memerlukan tinjauan manual.
   - **`FILE SISTEM/KONFIGURASI`**: Komponen penting proyek & OS (.git, .env, dependencies, source code, db) yang **DILINDUNGI PENUH**.

4. **Project & GIS Bundle Aware Detection**:
   - Memastikan tidak ada asset web export, dataset geospasial, atau dependensi aplikasi yang dirusak hanya karena memiliki SHA-256 identik dengan file lain.

5. **Laporan Audit Ganda (Markdown & JSON)**
   - **`LOCAL_FILE_AUDIT.md`**: Dokumen laporan lengkap dalam format Markdown tabel rapi, ringkasan kapasitas hemat, rincian hash, dan usulan folder tujuan.
   - **`LOCAL_FILE_AUDIT.json`**: Output terstruktur standar JSON untuk histori audit atau otomasi script lanjutan.

6. **Mode Cleanup Terpisah & Aman**
   - Eksekusi pembersihan hanya berjalan jika flag `--apply-cleanup` diberikan dan dikonfirmasi dengan persetujuan eksplisit.
   - File dipindahkan ke **Windows Recycle Bin** sehingga selalu bisa dipulihkan (*Restore*).

---

## 📦 Struktur Direktori Proyek

```text
local-file-organizer-auditor/
│
├── local_organizer/
│   ├── __init__.py
│   ├── cli.py                  # Antarmuka CLI & argumen interaktif
│   ├── config.py               # Rule immunity, pola ekstensi & kategori
│   ├── scanner.py              # File traversal & pengumpul metadata
│   ├── hasher.py               # Multi-tier duplicate detector (Size -> Partial -> Full SHA-256)
│   ├── classifier.py           # Klasifikasi 7 status & deteksi file nyasar
│   ├── keeper_selector.py      # Algoritma penentuan file master vs duplikat redundan
│   ├── reporter.py             # Generator LOCAL_FILE_AUDIT.md & .json
│   ├── cleanup.py              # Eksekutor aman Windows Recycle Bin (send2trash)
│   └── utils.py                # Helper byte formatting & path
│
├── tests/
│   ├── __init__.py
│   ├── test_hasher.py          # Unit test algoritma hashing & duplicate
│   ├── test_classifier.py      # Unit test proteksi & klasifikasi
│   └── test_end_to_end.py      # Unit test audit end-to-end & mock recycle bin
│
├── create_dummy_data.py        # Generator dataset dummy untuk simulasi
├── run_audit.py                # Runner script utama
├── requirements.txt            # Dependensi (send2trash, rich, pytest)
├── pyproject.toml
└── README.md
```

---

## 🚀 Panduan Instalasi

### 1. Prasyarat
- Python 3.9 atau versi yang lebih baru (Windows 10/11 didukung penuh).

### 2. Pasang Dependensi
Buka Terminal (PowerShell / Command Prompt) pada direktori proyek:
```bash
pip install -r requirements.txt
```

---

## 💻 Panduan Penggunaan

### 1. Menjalankan Audit (Default: Mode Dry-Run / Non-Destructive)
Untuk mengaudit folder target tertentu tanpa mengubah apa pun:

```powershell
python run_audit.py --path "D:\FolderYangInginDiaudit"
```
atau tentukan lokasi penyimpanan laporan:
```powershell
python run_audit.py --path "D:\FolderYangInginDiaudit" --output-dir "D:\FolderLaporan"
```

### 2. Opsi Filter & Pengecualian
- **Mengecualikan folder tertentu:**
  ```powershell
  python run_audit.py --path "D:\Data" --exclude-dirs build cache logs
  ```
- **Mengecualikan ekstensi tertentu:**
  ```powershell
  python run_audit.py --path "D:\Data" --exclude-exts .iso .vmdk
  ```
- **Hanya pindai subfolder tertentu (Whitelist):**
  ```powershell
  python run_audit.py --path "D:\Data" --whitelist-dirs Documents Pictures
  ```
- **Filter ukuran minimum berkas (misal berkas di atas 1MB):**
  ```powershell
  python run_audit.py --path "D:\Data" --min-size 1048576
  ```

---

## 🧹 Mode Cleanup (Pembersihan Aman)

Setelah Anda meninjau file laporan `LOCAL_FILE_AUDIT.md` dan menyetujui rekomendasinya, Anda dapat menjalankan cleanup.

### Contoh Perintah:
1. **Membersihkan duplikat redundan & file sampah ke Windows Recycle Bin (dengan prompt konfirmasi):**
   ```powershell
   python run_audit.py --path "D:\FolderTarget" --apply-cleanup
   ```
2. **Sekaligus merelokasi file salah lokasi & membersihkan folder kosong:**
   ```powershell
   python run_audit.py --path "D:\FolderTarget" --apply-cleanup --relocate-misplaced --remove-empty-dirs --confirm
   ```

> **Catatan Keamanan:** 
> - File yang masuk ke Recycle Bin dapat dibuka kembali melalui Windows Desktop Recycle Bin jika sewaktu-waktu Anda ingin memulihkannya (*Restore*).
> - File dengan status `FILE SISTEM/KONFIGURASI` dan `PERTAHANKAN` **tidak akan pernah disentuh**.

---

## 🧪 Menjalankan Pengujian Otomatis (Unit Tests & Dummy Simulation)

Proyek ini telah dilengkapi dengan unit test menyeluruh:
```powershell
python -m unittest discover tests -v
```

Untuk menguji tool pada lingkungan dummy tanpa menyentuh file nyata:
```powershell
# 1. Buat folder dummy simulasi
python create_dummy_data.py

# 2. Jalankan audit pada dummy_test_workspace
python run_audit.py --path dummy_test_workspace --output-dir dummy_test_workspace
```

---

## 🛡️ Daftar Proteksi Kebal (Immunity List)

Tool ini secara otomatis melindungi:
- **Direktori Proyek & Sistem**: `.git`, `.github`, `node_modules`, `vendor`, `.venv`, `venv`, `__pycache__`, `.vscode`, `.idea`, `AppData`, `Windows/System32`.
- **Berkas Konfigurasi**: `.env`, `.gitignore`, `package.json`, `requirements.txt`, `pyproject.toml`, `docker-compose.yml`, `tsconfig.json`, `Makefile`, dll.
- **Source Code**: `.py`, `.js`, `.ts`, `.html`, `.css`, `.go`, `.rs`, `.java`, `.php`, `.cpp`, `.sql`, dll.
- **Database & Kunci Enkripsi**: `.sqlite`, `.db`, `.pem`, `.key`, `.kdbx`.
