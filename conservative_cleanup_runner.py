"""
Conservative Cleanup Executor strictly for approved whitelist:
- 17 Standalone Safe Duplicate files
- 2 Free Temporary files
- 4 Non-structural Empty Folders

Validations before each action:
1. Path exists
2. For duplicates: Master copy exists & SHA-256 is 100% byte-for-byte identical
3. For temporary files: File is not locked / not in-use
4. For empty folders: Folder is truly empty (0 child items)
5. send2trash to Windows Recycle Bin (NEVER permanent delete)
"""
import os
import hashlib
from pathlib import Path
from send2trash import send2trash
from local_organizer.utils import format_bytes

downloads_root = Path(os.environ.get('USERPROFILE', 'C:/Users/LENOVO')) / 'Downloads'

# Approved 17 Safe Duplicates with their respective master copy
APPROVED_DUPLICATES = [
    (
        "expone/WhatsApp Video 2021-11-30 at 21.01.59 (1).mp4",
        "expone/WhatsApp Video 2021-11-30 at 21.01.59 (2).mp4"
    ),
    (
        "j/Proposal Skripsi Ribel/Referensi/2025+4-1+JURRIT+Lisna+Berutu+Jurnal+SDA (1).pdf",
        "j/Proposal Skripsi Ribel/Referensi/2025+4-1+JURRIT+Lisna+Berutu+Jurnal+SDA.pdf"
    ),
    (
        "j/Proposal Skripsi Ribel/Referensi/admin,+11_JTSKNO80(2)MARCH2018_SHEREN (1).pdf",
        "j/Proposal Skripsi Ribel/Referensi/admin,+11_JTSKNO80(2)MARCH2018_SHEREN.pdf"
    ),
    (
        "j/Proposal Skripsi Ribel/Referensi/asistenteeditorial2,+03_Art2_Developing+Systemic (1).pdf",
        "j/Proposal Skripsi Ribel/Referensi/asistenteeditorial2,+03_Art2_Developing+Systemic.pdf"
    ),
    (
        "j/Proposal Skripsi Ribel/Referensi/asistenteeditorial2,+03_Art2_Developing+Systemic (2).pdf",
        "j/Proposal Skripsi Ribel/Referensi/asistenteeditorial2,+03_Art2_Developing+Systemic.pdf"
    ),
    (
        "j/Proposal Skripsi Ribel/Referensi/asistenteeditorial2,+03_Art2_Developing+Systemic (3).pdf",
        "j/Proposal Skripsi Ribel/Referensi/asistenteeditorial2,+03_Art2_Developing+Systemic.pdf"
    ),
    (
        "192-207_Laravel+Dashboard+for+Immature+Oil+Palm+.pdf",
        "Jurnal Maghfirah_Laravel Dashboard for Immature Oil Palm (TBM III) Monitoring Using XYZ Tiles and Large Language Models.pdf"
    ),
    (
        "1KAS_AFD04_TBM2023_BLOK.zip",
        "1KAS BATAS/1KAS BATAS/2023/1KAS_AFD04_TBM2023_BLOK.zip"
    ),
    (
        "1KAS_AFD05_TBM2023_BLOK.zip",
        "1KAS BATAS/1KAS BATAS/2023/1KAS_AFD05_TBM2023_BLOK.zip"
    ),
    (
        "buku modul APSI model ERDIS (1).pdf",
        "buku modul APSI model ERDIS.pdf"
    ),
    (
        "cth2.xlsx",
        "cth2 (%).xlsx"
    ),
    (
        "INV.PKK_1DSH_1KHP SM II 2024_rev_2 (1).xlsx",
        "INV.PKK_1DSH_1KHP SM II 2024_rev_2.xlsx"
    ),
    (
        "JUTIF Template (1).docx",
        "Jurnal.docx"
    ),
    (
        "KSD.xlsx",
        "1750163275_KSD.xlsx"
    ),
    (
        "REKAPITULASI TBM PERIODE 1.xlsx",
        "REKAPITULASI TBM PERIODE 1 2025.xlsx"
    ),
    (
        "Skripsi Khoirun Nisa Harahap_FIX - Copy.pdf",
        "Skripsi Khoirun Nisa Harahap_FIX.pdf"
    ),
    (
        "Manuscript_LLM_ESG_Reporting_System_Palm_Oil.docx",
        "j/DD 200626/SkripsiNiko/Dokumen/Manuscript_LLM_ESG_Reporting_System_Palm_Oil.docx"
    ),
]

# Approved 2 Unlocked Temporary Files
APPROVED_TEMP_FILES = [
    "j/DD 220626/~WRL0828.tmp",
    "~WRL2028.tmp",
]

# Approved 4 Non-structural Empty Folders
APPROVED_EMPTY_FOLDERS = [
    "KotaPekanbaru/KOTA PEKANBARU",
    "Labuhanbatu/Labuhanbatu",
    "REKAP/1DL2/JANFEBMAR2025",
    "Telegram Desktop",
]


def run_conservative_cleanup():
    results = {
        "success_duplicates": [],
        "success_temp": [],
        "success_dirs": [],
        "skipped": [],
        "failed": [],
        "total_bytes_freed": 0,
    }

    print("=================================================================")
    print("   CONSERVATIVE CLEANUP EXECUTION (WINDOWS RECYCLE BIN)")
    print("=================================================================\n")

    # 1. Process 17 Duplicates
    print("--- [1/3] Memproses 17 Duplikat Mandiri Terverifikasi ---")
    for idx, (cand_rel, master_rel) in enumerate(APPROVED_DUPLICATES, 1):
        cand_path = downloads_root / Path(cand_rel)
        master_path = downloads_root / Path(master_rel)

        if not cand_path.exists():
            results["skipped"].append((cand_rel, "File target tidak ditemukan / sudah tidak ada"))
            print(f"[{idx:02d}] SKIPPED: {cand_rel} -> File target tidak ditemukan")
            continue

        if not master_path.exists():
            results["skipped"].append((cand_rel, f"Master copy tidak ditemukan: {master_rel}"))
            print(f"[{idx:02d}] SKIPPED: {cand_rel} -> Master copy {master_rel} tidak ada")
            continue

        # Compute SHA-256
        try:
            cand_bytes = cand_path.read_bytes()
            master_bytes = master_path.read_bytes()
            cand_hash = hashlib.sha256(cand_bytes).hexdigest()
            master_hash = hashlib.sha256(master_bytes).hexdigest()
        except Exception as e:
            results["failed"].append((cand_rel, f"Gagal membaca byte untuk hashing: {e}"))
            print(f"[{idx:02d}] FAILED: {cand_rel} -> Hashing error: {e}")
            continue

        if cand_hash != master_hash:
            results["skipped"].append((cand_rel, f"Hash SHA-256 tidak cocok dengan master ({cand_hash} vs {master_hash})"))
            print(f"[{idx:02d}] SKIPPED: {cand_rel} -> SHA-256 Hash MISMATCH!")
            continue

        file_size = len(cand_bytes)

        # Move to Recycle Bin via send2trash
        try:
            send2trash(str(cand_path))
            results["success_duplicates"].append((cand_rel, file_size, master_rel, cand_hash))
            results["total_bytes_freed"] += file_size
            print(f"[{idx:02d}] SUCCESS: {cand_rel} ({format_bytes(file_size)}) -> Recycle Bin")
        except Exception as e:
            results["failed"].append((cand_rel, f"Gagal memindahkan ke Recycle Bin: {e}"))
            print(f"[{idx:02d}] FAILED: {cand_rel} -> send2trash error: {e}")

    # 2. Process 2 Temporary Files
    print("\n--- [2/3] Memproses 2 Berkas Temporary Bebas Lock ---")
    for idx, temp_rel in enumerate(APPROVED_TEMP_FILES, 1):
        temp_path = downloads_root / Path(temp_rel)

        if not temp_path.exists():
            results["skipped"].append((temp_rel, "File temporary tidak ditemukan"))
            print(f"[{idx:02d}] SKIPPED: {temp_rel} -> File tidak ditemukan")
            continue

        # Check lock
        is_locked = False
        try:
            with open(temp_path, "r+b") as test_f:
                pass
        except Exception:
            is_locked = True

        if is_locked:
            results["skipped"].append((temp_rel, "File sedang digunakan/terkunci oleh proses lain"))
            print(f"[{idx:02d}] SKIPPED: {temp_rel} -> Sedang terkunci / in-use!")
            continue

        file_size = temp_path.stat().st_size

        try:
            send2trash(str(temp_path))
            results["success_temp"].append((temp_rel, file_size))
            results["total_bytes_freed"] += file_size
            print(f"[{idx:02d}] SUCCESS: {temp_rel} ({format_bytes(file_size)}) -> Recycle Bin")
        except Exception as e:
            results["failed"].append((temp_rel, f"Gagal memindahkan ke Recycle Bin: {e}"))
            print(f"[{idx:02d}] FAILED: {temp_rel} -> send2trash error: {e}")

    # 3. Process 4 Empty Folders
    print("\n--- [3/3] Memproses 4 Folder Kosong Non-Struktur ---")
    for idx, dir_rel in enumerate(APPROVED_EMPTY_FOLDERS, 1):
        dir_path = downloads_root / Path(dir_rel)

        if not dir_path.exists():
            results["skipped"].append((dir_rel, "Direktori tidak ditemukan"))
            print(f"[{idx:02d}] SKIPPED: {dir_rel} -> Direktori tidak ditemukan")
            continue

        # Check if really empty
        try:
            children = list(dir_path.iterdir())
        except Exception as e:
            results["failed"].append((dir_rel, f"Gagal membaca isi direktori: {e}"))
            print(f"[{idx:02d}] FAILED: {dir_rel} -> Error iterdir: {e}")
            continue

        if len(children) > 0:
            results["skipped"].append((dir_rel, f"Direktori tidak kosong (berisi {len(children)} item)"))
            print(f"[{idx:02d}] SKIPPED: {dir_rel} -> Direktori TIDAK KOSONG!")
            continue

        try:
            send2trash(str(dir_path))
            results["success_dirs"].append(dir_rel)
            print(f"[{idx:02d}] SUCCESS: {dir_rel} -> Recycle Bin")
        except Exception as e:
            results["failed"].append((dir_rel, f"Gagal memindahkan ke Recycle Bin: {e}"))
            print(f"[{idx:02d}] FAILED: {dir_rel} -> send2trash error: {e}")

    print("\n=================================================================")
    print("                      RINGKASAN EKSEKUSI                         ")
    print("=================================================================")
    print(f"Duplikat Sukses Dibuang ke Recycle Bin : {len(results['success_duplicates'])} berkas")
    print(f"Temporary Sukses Dibuang               : {len(results['success_temp'])} berkas")
    print(f"Folder Kosong Sukses Dibuang           : {len(results['success_dirs'])} folder")
    print(f"Item Di-Skip (Gagal Validasi)          : {len(results['skipped'])} item")
    print(f"Item Gagal (Error Eksekusi)            : {len(results['failed'])} item")
    print(f"TOTAL RUANG BERHASIL DIBEBASKAN        : {format_bytes(results['total_bytes_freed'])}")
    print("=================================================================\n")

    return results


if __name__ == "__main__":
    run_conservative_cleanup()
