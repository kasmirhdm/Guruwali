"""Template prompt Kurikulum Merdeka 2025 untuk GuruWali.

Ketentuan wajib yang dipakai SEMUA generator:
- Pendekatan Pembelajaran Mendalam: Memahami -> Mengaplikasi -> Merefleksi
- Profil Lulusan 8 dimensi: keimanan & ketakwaan, kewargaan, penalaran kritis,
  kreativitas, kolaborasi, kemandirian, kesehatan, komunikasi (BUKAN P5 6 dimensi)
- Istilah KKTP (BUKAN KKM)
- Struktur Modul Ajar resmi 2025: A. Identifikasi -> B. Desain Pembelajaran ->
  C. Pengalaman Belajar -> D. Asesmen (Awal/Proses/Akhir) -> E. Lampiran
- JANGAN PERNAH mengarang Capaian Pembelajaran (CP): pakai CP yang ditempel guru.
  Jika guru tidak menempel CP, tulis "[CP: diisi guru dari dokumen resmi]" dan lanjutkan.
"""
import re

SYSTEM_ID = (
    "ATURAN MATEMATIKA (SANGAT PENTING):\n"
    "1. JANGAN PERNAH pakai tanda dolar $ untuk matematika. SALAH: $x$, $2x+y$. BENAR: x, 2x + y = 9.000.\n"
    "2. Tulis variabel dan persamaan langsung tanpa pembungkus apapun.\n"
    "3. Gunakan karakter Unicode: \u00d7 \u00f7 \u00b1 \u2212 \u221a \u00b2 \u00b3 \u00b0 \u2260 \u2264 \u2265.\n"
    "4. Pecahan tulis biasa: 3/4.\n"
    "5. JANGAN pakai \\times, \\frac, \\sqrt atau perintah LaTeX/backslash apapun.\n"

    "Kamu adalah GURU AI, asisten profesional untuk guru Indonesia. "
    "Tugasmu menghasilkan bahan dan perangkat pembelajaran yang akurat, relevan, konsisten, "
    "praktis, dan siap digunakan.\n"
    "PRINSIP GLOBAL UNTUK SEMUA GENERATOR:\n"
    "1. Pahami seluruh input guru dan sesuaikan hasil dengan mata pelajaran, jenjang/fase, "
    "kelas, semester, materi, tujuan, alokasi waktu, dan konteks yang diberikan. Jangan mengada-adakan "
    "data yang tidak diberikan.\n"
    "2. Selaraskan CP -> TP -> aktivitas pembelajaran -> asesmen -> tindak lanjut. Jangan membuat "
    "komponen yang saling bertentangan.\n"
    "3. Gunakan Bahasa Indonesia yang baku, jelas, hangat, dan profesional. Hasil harus mudah "
    "disalin ke Word dan siap dipakai guru. Hindari pengulangan, filler, dan paragraf generik.\n"
    "4. Untuk konsep, fakta, rumus, contoh, dan perhitungan, lakukan pemeriksaan internal sebelum "
    "menjawab. Jangan memberikan kunci jawaban atau perhitungan yang tidak benar.\n"
    "5. Jangan mengarang Capaian Pembelajaran (CP), dasar hukum, nomor surat, data sekolah, atau "
    "fakta khusus yang tidak diberikan. Jika CP tidak diberikan, tulis '[CP: diisi guru dari dokumen resmi]' "
    "dan jangan berpura-pura mengetahui CP spesifik sekolah. Untuk data administrasi yang belum ada, "
    "gunakan placeholder yang jelas.\n"
    "6. Jika pengguna memberi soal, teks, atau data sumber, prioritaskan dan pertahankan informasi "
    "tersebut. Jangan mengubah angka, nama, atau maksud tanpa alasan. Jika ada informasi yang tidak "
    "cukup untuk menghasilkan bagian tertentu, nyatakan secara singkat bagian yang perlu dilengkapi.\n"
    "7. Jika menggunakan Pembelajaran Mendalam, terapkan secara nyata melalui Memahami -> Mengaplikasi "
    "-> Merefleksi; jangan hanya menuliskan nama tahap.\n"
    "8. Gunakan istilah KKTP, bukan KKM, dan gunakan dimensi Profil Lulusan yang relevan.\n"
    "9. Sesuaikan tingkat bahasa dan kompleksitas dengan peserta didik. Untuk matematika dan bidang "
    "lain yang membutuhkan langkah kerja, tampilkan prosedur yang runtut dan dapat diverifikasi.\n"
    "10. Sebelum mengirim hasil, lakukan pemeriksaan akhir: kelengkapan, konsistensi, kesesuaian "
    "waktu, kesesuaian level, kebenaran jawaban, dan keterhubungan antarbagian.\n"
    "11. Untuk soal matematika/IPA/akuntansi atau tugas yang memiliki perhitungan, hitung ulang setiap langkah secara mandiri. Untuk PG, pastikan tepat satu opsi yang benar, kunci cocok dengan hasil hitung, dan pembahasan menghasilkan hasil yang sama. Jika tidak ada opsi yang benar atau ada lebih dari satu opsi benar, wajib memperbaiki soal/opsinya sebelum mengirim. Jangan mempertahankan soal yang cacat hanya demi memenuhi jumlah.\n"
    "12. Untuk aljabar, persamaan, dan ekspresi numerik, lakukan verifikasi substitusi dengan setidaknya satu nilai yang valid bila relevan. Jangan menulis catatan seperti 'koreksi', 'opsi salah', 'kemungkinan ralat', atau menyatakan kunci yang bertentangan dengan perhitungan akhir; perbaiki kontennya terlebih dahulu.\n"    "13. Notasi matematika harus aman untuk Word/PDF dan mudah dibaca: jangan gunakan LaTeX seperti $...$, \\times, \\frac, \\sqrt atau perintah backslash. Gunakan karakter Unicode langsung seperti × ÷ ± − √ ² ³ ° bila tersedia; pecahan sederhana ditulis dengan format 3/4.\n"
    "Format keluaran memakai heading yang jelas (##, ###), tabel bila membantu, dan daftar berpoin. "
    "Jangan memakai emoji berlebihan."
)

DIMENSI_LULUSAN = (
    "keimanan dan ketakwaan, kewargaan, penalaran kritis, kreativitas, "
    "kolaborasi, kemandirian, kesehatan, komunikasi"
)


def _ctx(inputs):
    """Format input form menjadi konteks 'label: nilai'."""
    lines = []
    for k, v in inputs.items():
        v = str(v or "").strip()
        if v:
            lines.append(f"- {k}: {v}")
    return "\n".join(lines) if lines else "- (tidak ada input tambahan)"


# ----------------------------------------------------------------------------
# Template per tipe generator.
# Setiap entri: label (nama tampil), section, instr (instruksi detail),
# maxtokens, title (pola judul dokumen tersimpan; {...} diisi dari inputs).
# ----------------------------------------------------------------------------
TEMPLATES = {
    # ================= PERANGKAT AJAR =================
    "modul-ajar": {
        "label": "Modul Ajar",
        "section": "perangkat",
        "maxtokens": 8000,
        "title": "Modul Ajar {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan MODUL AJAR yang lengkap, koheren, dan siap digunakan guru dengan struktur:\n"
            "A. IDENTIFIKASI: identitas sekolah, mata pelajaran, fase/kelas, semester, materi/topik, "
            "alokasi waktu, kompetensi awal, karakteristik peserta didik, sarana-prasarana, target peserta didik, "
            "serta model/metode pembelajaran.\n"
            "B. DESAIN PEMBELAJARAN: CP hanya dari input guru; jika kosong tulis "
            "'[CP: diisi guru dari dokumen resmi]'. Turunkan TP yang operasional dan terukur dari CP/materi. "
            "Sertakan pemahaman bermakna, pertanyaan pemantik, dan dimensi Profil Lulusan yang benar-benar relevan.\n"
            "C. PENGALAMAN BELAJAR: susun pendahuluan, kegiatan inti, dan penutup dengan pembagian waktu yang "
            "jumlahnya tepat sama dengan alokasi waktu. Pada kegiatan inti, terapkan Memahami -> Mengaplikasi -> Merefleksi "
            "melalui aktivitas nyata guru dan peserta didik.\n"
            "D. ASESMEN: asesmen awal/diagnostik, formatif/proses, dan sumatif/akhir yang benar-benar mengukur TP. "
            "Sertakan KKTP, indikator ketercapaian, instrumen atau contoh butir, serta rubrik/pedoman penskoran bila relevan.\n"
            "E. TINDAK LANJUT: remedial, pengayaan, refleksi guru, dan refleksi peserta didik.\n"
            "F. LAMPIRAN: LKPD yang dapat langsung digunakan, materi/bahan ajar ringkas, kisi-kisi/soal evaluasi "
            "bila sesuai kebutuhan, kunci jawaban dan pedoman penskoran, glosarium, serta daftar pustaka. "
            "Pastikan LKPD, kegiatan, soal, asesmen, dan TP saling selaras. Jangan membuat modul hanya tampak lengkap; "
            "setiap bagian harus mempunyai fungsi nyata dalam pembelajaran."
        ),
    },
    "rpp": {
        "label": "RPP",
        "section": "perangkat",
        "maxtokens": 6000,
        "title": "RPP {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan RPP (Rencana Pelaksanaan Pembelajaran) dengan komponen: identitas "
            "(sekolah, kelas, mata pelajaran, materi, alokasi waktu), CP/TP (pakai CP dari guru; "
            "jika kosong tulis '[CP: diisi guru]'), tujuan pembelajaran dalam format ABCD, "
            "pemahaman bermakna dan pertanyaan pemantik, kegiatan pendahuluan-inti-penutup "
            "mengikuti tahapan Memahami -> Mengaplikasi -> Merefleksi, asesmen "
            "(diagnostik, formatif, sumatif) beserta KKTP, kegiatan pengayaan dan remedial, "
            "serta media/sumber belajar."
        ),
    },
    "atp": {
        "label": "ATP",
        "section": "perangkat",
        "maxtokens": 6000,
        "title": "ATP {mapel} Fase {fase}",
        "instr": (
            "Buatkan ALUR TUJUAN PEMBELAJARAN (ATP) untuk satu fase: susun TP-TP secara "
            "logis dan berurutan dari CP yang ditempel guru (jika CP kosong, tulis "
            "'[CP: diisi guru dari dokumen resmi]' lalu susun TP umum yang lazim untuk "
            "materi tersebut dan tandai perlu verifikasi). Setiap TP ditulis operasional "
            "dan terukur, dikelompokkan per semester/bab, sertakan perkiraan alokasi "
            "waktu (JP) per TP."
        ),
    },
    "tujuan-pembelajaran": {
        "label": "Tujuan Pembelajaran",
        "section": "perangkat",
        "maxtokens": 3000,
        "title": "TP {materi} - Kelas {kelas}",
        "instr": (
            "Turunkan TUJUAN PEMBELAJARAN (TP) dari CP/materi yang diberikan. Tulis 4-8 TP "
            "yang operasional, terukur, dan berurutan dari mudah ke sulit (mendukung tahapan "
            "Memahami -> Mengaplikasi -> Merefleksi). Setiap TP memakai kata kerja operasional "
            "yang tepat dan mencantumkan kondisi serta kriteria keberhasilannya."
        ),
    },
    "kktp": {
        "label": "KKTP",
        "section": "perangkat",
        "maxtokens": 4000,
        "title": "KKTP {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan KRITERIA KETERCAPAIAN TUJUAN PEMBELAJARAN (KKTP) untuk materi ini: "
            "rumuskan kriteria per TP dalam bentuk deskriptif (bukan angka mati), tentukan "
            "teknik asesmen yang sesuai untuk tiap kriteria, dan berikan contoh indikator "
            "tercapai/belum tercapai. Ingat: gunakan istilah KKTP, bukan KKM."
        ),
    },
    "program-tahunan": {
        "label": "Program Tahunan (Prota)",
        "section": "perangkat",
        "maxtokens": 6000,
        "title": "Prota {mapel} Kelas {kelas}",
        "instr": (
            "Buatkan PROGRAM TAHUNAN (Prota) dalam bentuk tabel: No | Materi/TP Pokok | "
            "Alokasi JP | Semester. Susun cakupan materi satu tahun ajaran secara logis "
            "berdasarkan input guru. Jangan menganggap jumlah JP, minggu efektif, atau hari efektif "
            "tertentu sebagai ketentuan resmi jika guru tidak memberikannya. Jika data tersebut "
            "tidak tersedia, gunakan perkiraan yang diberi label 'Perkiraan/Perlu disesuaikan' "
            "dan tambahkan catatan bahwa kalender/struktur kurikulum sekolah harus diverifikasi."
        ),
    },
    "program-semester": {
        "label": "Program Semester (Prosem)",
        "section": "perangkat",
        "maxtokens": 6000,
        "title": "Prosem {mapel} Kelas {kelas} Smt {semester}",
        "instr": (
            "Buatkan PROGRAM SEMESTER (Prosem/Promes) dalam bentuk tabel: Minggu ke | TP/Materi | "
            "Kegiatan | Asesmen | JP. Rincikan pembagian per minggu berdasarkan jumlah minggu "
            "efektif yang diberikan guru. Jangan menetapkan 16-18 minggu sebagai angka resmi jika "
            "tidak diberikan. Jika jumlah minggu efektif tidak tersedia, buat rancangan perkiraan "
            "dan beri label 'Perkiraan/Perlu disesuaikan dengan kalender pendidikan sekolah'."
        ),
    },
    "remedial": {
        "label": "Program Remedial",
        "section": "perangkat",
        "maxtokens": 4000,
        "title": "Remedial {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan PROGRAM REMEDIAL untuk peserta didik yang belum mencapai KKTP pada "
            "materi ini: identifikasi kemungkinan kesulitan belajar, bentuk remedial yang "
            "sesuai (pembelajaran ulang, bimbingan khusus, tugas terstruktur, tutor sebaya), "
            "jadwal pelaksanaan, dan instrumen penilaian ulang beserta KKTP-nya."
        ),
    },
    "pengayaan": {
        "label": "Program Pengayaan",
        "section": "perangkat",
        "maxtokens": 4000,
        "title": "Pengayaan {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan PROGRAM PENGAYAAN untuk peserta didik yang sudah melampaui KKTP: "
            "aktivitas pengayaan yang menantang dan bermakna (proyek mini, penelitian "
            "sederhana, eksplorasi lanjutan materi), mendukung dimensi Profil Lulusan "
            "(kreativitas, penalaran kritis, kemandirian), beserta rubrik penilaiannya."
        ),
    },
    # ================= MATERI =================
    "materi": {
        "label": "Materi Pembelajaran",
        "section": "materi",
        "maxtokens": 8000,
        "title": "Materi {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan MATERI PEMBELAJARAN yang lengkap dan akurat untuk guru sebagai bahan "
            "ajar: penjelasan konsep sesuai tingkat kedalaman yang dipilih guru (Ringkas, Sedang, atau Mendalam), "
            "kontekstual Indonesia, ilustrasi/deskripsi visual yang membantu, kesalahpahaman "
            "umum peserta didik beserta klarifikasinya, dan rangkuman poin penting di akhir. "
            "Akhiri dengan 5 pertanyaan pemantik diskusi kelas."
        ),
    },
    "ringkasan-materi": {
        "label": "Ringkasan Materi",
        "section": "materi",
        "maxtokens": 3000,
        "title": "Ringkasan {materi}",
        "instr": (
            "Buatkan RINGKASAN MATERI yang padat dan mudah dihafal: poin-poin kunci, "
            "definisi penting, rumus/fakta inti (jika ada), dan mind-map dalam bentuk teks "
            "berstruktur. Cocok untuk bahan review cepat sebelum asesmen."
        ),
    },
    "materi-siswa": {
        "label": "Materi Versi Siswa",
        "section": "materi",
        "maxtokens": 5000,
        "title": "Materi Siswa {materi} - Kelas {kelas}",
        "instr": (
            "Tulis ulang materi ini dalam BAHASA YANG RAMAH UNTUK SISWA sesuai jenjangnya: "
            "kalimat sederhana, analogi kehidupan sehari-hari, contoh yang dekat dengan dunia "
            "anak, dan ajakan berpikir (bukan sekadar hafalan). Hindari jargon tanpa penjelasan."
        ),
    },
    # ================= SOAL & EVALUASI =================
    "soal-pg": {
        "label": "Soal Pilihan Ganda",
        "section": "soal",
        "maxtokens": 8000,
        "title": "Soal PG {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan SOAL PILIHAN GANDA sesuai jumlah dan level kognitif yang dipilih guru. Sebelum menampilkan hasil, selesaikan dan verifikasi setiap soal secara internal. "
            "Setiap soal punya stimulus singkat (teks/gambar deskriptif/data), 4 opsi jawaban (A-D) dengan pengecoh yang "
            "masuk akal, dan sebaran level kognitif (C1-C6) yang merata termasuk beberapa soal HOTS. "
            "Untuk setiap PG, pastikan tepat satu opsi A-D yang benar; kunci harus sesuai hasil perhitungan dan pembahasan. "
            "Jika hasil hitung tidak cocok dengan opsi, ubah opsi atau ubah soal sampai valid. Setelah semua soal, sertakan KUNCI JAWABAN dan PEMBAHASAN singkat per soal "
            "secara otomatis."
        ),
    },
    "soal-uraian": {
        "label": "Soal Uraian",
        "section": "soal",
        "maxtokens": 6000,
        "title": "Soal Uraian {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan SOAL URAIAN sesuai jumlah yang diminta dengan stimulus yang menantang "
            "penalaran (studi kasus, data, kutipan). Setiap soal dilengkapi pedoman penskoran "
            "(skor per langkah/jawaban ideal) dan KUNCI JAWABAN berupa jawaban model beserta "
            "PEMBAHASANnya secara otomatis."
        ),
    },
    "soal-hots": {
        "label": "Soal HOTS",
        "section": "soal",
        "maxtokens": 6000,
        "title": "Soal HOTS {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan SOAL HOTS (level C4-C6: menganalisis, mengevaluasi, mencipta) sesuai jumlah "
            "yang diminta: berbasis stimulus autentik (kasus nyata, data, infografis deskriptif), "
            "menuntut penalaran tingkat tinggi dan kreativitas. Sertakan KUNCI JAWABAN (jawaban "
            "model dengan beberapa alternatif yang dapat diterima) dan PEMBAHASAN secara otomatis."
        ),
    },
    "kisi-kisi": {
        "label": "Kisi-kisi Soal",
        "section": "soal",
        "maxtokens": 5000,
        "title": "Kisi-kisi {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan KISI-KISI SOAL sebanyak jumlah soal yang diminta dan gunakan bentuk soal yang dipilih guru. Tabel: No | TP/Materi | Indikator Soal | "
            "Level Kognitif (C1-C6) | Bentuk Soal | Nomor Soal. Pastikan sebaran level kognitif "
            "seimbang dan mencakup semua TP penting dari materi ini."
        ),
    },
    "kunci-jawaban": {
        "label": "Kunci Jawaban",
        "section": "soal",
        "maxtokens": 4000,
        "title": "Kunci Jawaban {materi}",
        "instr": (
            "Berdasarkan soal yang ditempel guru pada input (jika ada), buatkan KUNCI JAWABAN "
            "yang akurat per nomor soal. Jika soal tidak ditempel, susun kunci jawaban umum "
            "berupa jawaban ideal per indikator materi ini dalam format daftar bernomor."
        ),
    },
    "pembahasan": {
        "label": "Pembahasan Soal",
        "section": "soal",
        "maxtokens": 5000,
        "title": "Pembahasan {materi}",
        "instr": (
            "Berdasarkan soal yang ditempel guru pada input (jika ada), buatkan PEMBAHASAN "
            "per soal: jelaskan konsep yang diuji, langkah penyelesaian yang benar, dan mengapa "
            "opsi lain salah (untuk PG). Jika soal tidak ditempel, buat pembahasan umum per "
            "indikator materi. Gunakan bahasa yang mudah dipahami siswa."
        ),
    },
    # ================= MEDIA =================
    "lkpd": {
        "label": "LKPD",
        "section": "media",
        "maxtokens": 6000,
        "title": "LKPD {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan LKPD (Lembar Kerja Peserta Didik) dengan 8 komponen: 1) judul dan identitas, "
            "2) petunjuk penggunaan, 3) kompetensi/TP yang dicapai, 4) informasi pendukung singkat, "
            "5) langkah kerja/tugas (mendukung tahapan Memahami -> Mengaplikasi -> Merefleksi), "
            "6) tabel data/pengamatan untuk diisi siswa, 7) pertanyaan diskusi, 8) rubrik penilaian. "
            "Aktivitas harus mendorong kolaborasi dan penalaran kritis."
        ),
    },
    "worksheet": {
        "label": "Worksheet",
        "section": "media",
        "maxtokens": 4000,
        "title": "Worksheet {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan WORKSHEET/latihan mandiri untuk siswa: instruksi yang jelas, variasi latihan "
            "(isian singkat, menjodohkan, benar-salah, uraian pendek) dari mudah ke sulit, "
            "kunci jawaban di bagian akhir terpisah, dan kolom skor + refleksi diri siswa."
        ),
    },
    "ppt-outline": {
        "label": "Outline PPT",
        "section": "media",
        "maxtokens": 4000,
        "title": "Outline PPT {materi}",
        "instr": (
            "Buatkan OUTLINE PPT presentasi pembelajaran sesuai jumlah slide yang diminta: "
            "untuk tiap slide tulis judul slide, poin-poin isi (maksimal 5 baris per slide), "
            "saran visual/ilustrasi, dan catatan narasi guru. Alur: pembuka yang memantik -> "
            "konsep inti bertahap -> contoh -> aktivitas -> penutup reflektif."
        ),
    },
    # ================= ALAT BANTU =================
    "rubrik": {
        "label": "Rubrik Penilaian",
        "section": "alat",
        "maxtokens": 5000,
        "title": "Rubrik {materi} - Kelas {kelas}",
        "instr": (
            "Buatkan RUBRIK PENILAIAN untuk aspek yang disebutkan guru: tabel dengan kriteria per "
            "aspek dan 4 level capaian (Sangat Baik, Baik, Cukup, Perlu Bimbingan) beserta "
            "deskriptornya yang operasional. Sertakan cara menghitung skor akhir dan "
            "kaitannya dengan KKTP."
        ),
    },
    "ice-breaking": {
        "label": "Ice Breaking",
        "section": "alat",
        "maxtokens": 3000,
        "title": "Ice Breaking Kelas {kelas}",
        "instr": (
            "Buatkan 5 ide ICE BREAKING yang seru, sesuai jenjang dan durasi yang diminta: "
            "setiap ide berisi nama permainan, langkah pelaksanaan, dan manfaatnya "
            "(fokus, kebersamaan, semangat). Jika ada tema materi, kaitkan permainannya "
            "dengan tema tersebut."
        ),
    },
    "refleksi": {
        "label": "Pertanyaan Refleksi",
        "section": "alat",
        "maxtokens": 3000,
        "title": "Refleksi {materi}",
        "instr": (
            "Buatkan 10 PERTANYAAN REFLEKSI untuk sasaran yang dipilih (murid/guru): "
            "mendorong murid/guru memikirkan kembali proses belajar (tahap Merefleksi dari "
            "Pembelajaran Mendalam), jujur, dan spesifik — bukan pertanyaan basa-basi. "
            "Kelompokkan menjadi refleksi perasaan, pemahaman, dan rencana tindak lanjut."
        ),
    },
    "jurnal-mengajar": {
        "label": "Jurnal Mengajar",
        "section": "alat",
        "maxtokens": 4000,
        "title": "Jurnal Mengajar {materi} - {tanggal}",
        "instr": (
            "Buatkan TEMPLATE JURNAL MENGAJAR yang siap diisi guru: identitas pembelajaran "
            "(tanggal, kelas, materi), tujuan, ringkasan kegiatan yang dilakukan, hal yang "
            "berjalan baik, kendala yang dihadapi, respons/karakteristik peserta didik yang "
            "menonjol, dan rencana tindak lanjut. Sertakan contoh pengisian satu paragraf "
            "sebagai ilustrasi."
        ),
    },
    # ================= ADMINISTRASI =================
    "surat-tugas": {
        "label": "Surat Tugas",
        "section": "admin",
        "maxtokens": 3000,
        "title": "Surat Tugas {keperluan}",
        "instr": (
            "Buatkan SURAT TUGAS resmi sekolah dengan format baku: kop surat (tulis "
            "'[KOP SEKOLAH]' sebagai placeholder), nomor surat '[Nomor: .../..../{tahun}]', "
            "dasar/menimbang, isi penugasan (nama, NIP jika ada, keperluan, tanggal, tempat), "
            "tembusan hanya jika penerima tembusan diberikan guru; jika tidak, tulis '[Tembusan: diisi jika diperlukan]'. "
            "Nomor surat, dasar/menimbang, dan pejabat penandatangan yang belum diberikan harus berupa placeholder, "
            "bukan data yang dibuat AI. Gunakan bahasa "
            "administrasi yang formal."
        ),
    },
    "berita-acara": {
        "label": "Berita Acara",
        "section": "admin",
        "maxtokens": 3000,
        "title": "Berita Acara {kegiatan}",
        "instr": (
            "Buatkan BERITA ACARA kegiatan dengan format resmi: judul, nomor '[Nomor: ...]', "
            "hari/tanggal, tempat, pihak yang hadir hanya berdasarkan daftar yang diberikan guru; jika tidak ada, "
            "gunakan '[Pihak yang hadir: diisi sesuai daftar hadir]'. Uraian jalannya kegiatan harus bersumber "
            "dari informasi guru, bukan kejadian yang dikarang. Hasil/keputusan gunakan poin yang ditempel guru; "
            "jika kosong, gunakan placeholder '[Hasil/keputusan: diisi]'. Blok tanda tangan para "
            "pihak. Bahasa formal dan kronologis."
        ),
    },
    "proposal": {
        "label": "Proposal Kegiatan",
        "section": "admin",
        "maxtokens": 6000,
        "title": "Proposal {kegiatan}",
        "instr": (
            "Buatkan PROPOSAL KEGIATAN sekolah yang lengkap dan persuasif: latar belakang "
            "(pakai yang ditempel guru), dasar hukum hanya jika diberikan guru; jika tidak, tulis '[Dasar hukum: diisi sesuai ketentuan sekolah]' tanpa mengarang, tujuan, sasaran peserta, "
            "waktu dan tempat, susunan panitia (struktur umum), rincian anggaran (tabel "
            "komponen + estimasi biaya dalam rupiah yang wajar), jadwal kegiatan, dan penutup. "
            "Akhiri dengan lembar pengesahan."
        ),
    },
    # ================= CHAT =================
    "chat-bebas": {
        "label": "Chat AI",
        "section": "chat",
        "maxtokens": 4000,
        "title": "Chat {pesan}",
        "instr": (
            "Jawab pertanyaan guru berikut dengan helpful, akurat, dan relevan dengan konteks "
            "pendidikan Indonesia dan Kurikulum Merdeka. Jika pertanyaan membutuhkan dokumen "
            "terstruktur (modul, soal, surat), tawarkan untuk dibuatkan lewat generator "
            "yang sesuai."
        ),
    },
}

# Urutan 11 dokumen untuk fitur "SATU INPUT -> 11 DOKUMEN"
PAKET_LENGKAP = [
    "modul-ajar",
    "materi",
    "lkpd",
    "kisi-kisi",
    "soal-pg",
    "kunci-jawaban",
    "pembahasan",
    "rubrik",
    "remedial",
    "pengayaan",
    "ppt-outline",
]


def build_prompt(gen_type, inputs):
    """Bangun prompt lengkap: system + instruksi tipe + data input form."""
    tpl = TEMPLATES.get(gen_type)
    if not tpl:
        raise ValueError(f"Tipe generator tidak dikenal: {gen_type}")
    data = _ctx(inputs)
    tahun = str(inputs.get("tahun") or __import__("datetime").datetime.now().year)
    extra = ""
    signature_types = {"modul-ajar", "rpp", "atp", "program-tahunan", "program-semester",
                       "jurnal-mengajar", "surat-tugas", "berita-acara", "proposal"}
    kop_types = {"surat-tugas", "berita-acara", "proposal"}
    if gen_type in kop_types:
        extra += (
            "\nATURAN KOP DOKUMEN:\n"
            "Dokumen ini termasuk dokumen yang umumnya menggunakan kop sekolah. "
            "Jika kop_mode bukan 'tanpa', buat kop di bagian paling atas sebelum judul dokumen. "
            "Gunakan data kop yang diberikan apa adanya: [JUDUL KOP], [SUBJUDUL KOP], nama sekolah, "
            "alamat, NPSN, telepon, email, dan informasi kontak lain. Jangan mengarang data yang kosong; "
            "gunakan placeholder [JUDUL KOP], [SUBJUDUL KOP], [NAMA SEKOLAH], [ALAMAT SEKOLAH], [NPSN], [TELEPON], [EMAIL]. "
            "Bungkus kop dengan marker [[KOP]] dan [[/KOP]], satu baris per informasi. Setelah kop, buat garis pemisah yang jelas. JANGAN tulis judul ganda. Mulai dokumen LANGSUNG dengan blok KOP. Untuk kop_mode 'admin', jangan menambahkan kop "
            "ke dokumen non-administrasi; untuk 'semua', ikuti aturan ini pada dokumen formal."
        )
    if gen_type in signature_types:
        extra += (
            "\nATURAN TANDA TANGAN DOKUMEN:\n"
            "Dokumen ini termasuk dokumen yang lazim memerlukan pengesahan. Jika data identitas "
            "sekolah/guru tersedia, gunakan data tersebut apa adanya. Jangan mengarang nama, NIP, "
            "nomor surat, atau jabatan. Ikuti signature_mode dari data guru. "
            "Gunakan placeholder [NAMA KEPALA SEKOLAH], [NIP KEPALA SEKOLAH], [NAMA GURU], "
            "[NIP GURU], [JABATAN GURU], [KOTA], dan [TANGGAL] bila datanya belum tersedia. "
            "Untuk mode guru-kepala, buat dua blok tanda tangan; untuk guru-saja hanya blok guru; "
            "untuk kepala-saja hanya blok kepala sekolah; untuk tanpa-tanda-tangan jangan membuat "
            "blok tanda tangan. Bungkus blok tanda tangan dengan marker [[TTD]] dan [[/TTD]], gunakan | untuk memisahkan kolom kiri dan kanan. Jangan membuat tanda tangan fiktif atau gambar tanda tangan."
        )
    if gen_type == "proposal":
        extra += (
            "\nLEMBAR PENGESAHAN: sediakan tempat tanda tangan pihak yang relevan, "
            "dengan kepala sekolah sebagai pengesah bila mode mengizinkan."
        )
    if gen_type == "chat-bebas":
        extra = f"\nPertanyaan guru: {inputs.get('pesan', '')}\n"
    instr = tpl["instr"].replace("{tahun}", tahun)
    return (
        f"{instr}\n\n"
        f"DATA DARI GURU:\n{data}\n{extra}\n"
        "Tulis hasil akhirnya saja dalam Bahasa Indonesia yang rapi. "
        "Jangan mengulang instruksi ini."
    )


def make_title(gen_type, inputs):
    """Judul otomatis untuk dokumen tersimpan."""
    tpl = TEMPLATES.get(gen_type, {})
    pattern = tpl.get("title", "{label}")
    safe = {k: str(v or "").strip()[:60] for k, v in (inputs or {}).items()}
    safe.setdefault("label", tpl.get("label", gen_type))
    try:
        title = pattern.format(**safe)
    except (KeyError, IndexError):
        title = tpl.get("label", gen_type)
    title = re.sub(r"\{[^}]*\}", "", title)  # sisa placeholder yang tak terisi
    title = re.sub(r"\s+-\s*(Kelas|Fase|Smt)\s*$", "", title)  # label menggantung di akhir
    title = re.sub(r"\s{2,}", " ", title).strip(" -")
    return title or tpl.get("label", gen_type)


def max_tokens_for(gen_type):
    return TEMPLATES.get(gen_type, {}).get("maxtokens", 4000)
