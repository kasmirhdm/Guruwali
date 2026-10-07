"""Import data Dapodik (CSV) untuk auto-isi profil guru & sekolah."""
import csv
import io
import time
import db


def parse_dapodik_csv(csv_text):
    """Parse CSV Dapodik. Kolom yang dikenali (case-insensitive):
    nama, nip, mapel/mata_pelajaran, jenjang, sekolah/nama_sekolah,
    npsn, alamat, kota, jabatan, nama_kepala, nip_kepala
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    # Normalisasi header
    field_map = {}
    for h in (reader.fieldnames or []):
        key = h.strip().lower().replace(' ', '_')
        field_map[key] = h

    def get(row, *names):
        for n in names:
            if n in field_map and row.get(field_map[n]):
                return row[field_map[n]].strip()
        return ''

    results = []
    for row in reader:
        results.append({
            'nama': get(row, 'nama', 'nama_lengkap', 'nama_guru'),
            'nip': get(row, 'nip'),
            'mapel': get(row, 'mapel', 'mata_pelajaran', 'bidang_studi'),
            'jenjang': get(row, 'jenjang', 'bentuk_pendidikan'),
            'sekolah': get(row, 'sekolah', 'nama_sekolah', 'satuan_pendidikan'),
            'npsn': get(row, 'npsn'),
            'alamat': get(row, 'alamat', 'alamat_sekolah', 'jalan'),
            'kota': get(row, 'kota', 'kabupaten', 'kab_kota'),
            'jabatan': get(row, 'jabatan', 'jabatan_guru', 'status_kepegawaian'),
            'nama_kepala': get(row, 'nama_kepala', 'kepala_sekolah'),
            'nip_kepala': get(row, 'nip_kepala', 'nip_kepsek'),
        })
    return results


def apply_to_profile(user_id, data):
    """Terapkan data Dapodik ke profil user."""
    conn = db.get_conn()
    try:
        updates = []
        params = []
        mapping = {
            'nama': 'nama', 'nip': 'nip_guru', 'mapel': 'mapel',
            'jenjang': 'jenjang', 'sekolah': 'sekolah', 'npsn': 'npsn',
            'alamat': 'alamat_sekolah', 'kota': 'kota_sekolah',
            'jabatan': 'jabatan_guru', 'nama_kepala': 'nama_kepala',
            'nip_kepala': 'nip_kepala',
        }
        for src, col in mapping.items():
            if data.get(src):
                updates.append(f"{col} = ?")
                params.append(data[src])
        if not updates:
            return False
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
        # Log import
        conn.execute(
            "INSERT INTO dapodik_imports (user_id, filename, rows_imported, created_at)"
            " VALUES (?, ?, ?, ?)",
            (user_id, 'dapodik.csv', 1, int(time.time())),
        )
        conn.commit()
        return True
    finally:
        conn.close()
