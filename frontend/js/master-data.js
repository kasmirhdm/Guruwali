/* GuruWali — master data untuk dropdown cascading (minim ketik).
   Dimuat sebelum cascade.js dan app.js. Mengekspos global GWMaster. */
var GWMaster = {
  JENJANG: ["SD", "SMP", "SMA", "SMK"],

  KELAS: {
    SD: ["1", "2", "3", "4", "5", "6"],
    SMP: ["7", "8", "9"],
    SMA: ["10", "11", "12"],
    SMK: ["10", "11", "12"]
  },

  /* Mata pelajaran Kurikulum Merdeka per jenjang */
  MAPEL: {
    SD: [
      "Pendidikan Agama & Budi Pekerti", "PPKn", "Bahasa Indonesia",
      "Matematika", "IPAS", "PJOK", "Seni Rupa", "Seni Musik",
      "Seni Tari", "Seni Teater", "Bahasa Inggris", "Muatan Lokal"
    ],
    SMP: [
      "Pendidikan Agama & Budi Pekerti", "PPKn", "Bahasa Indonesia",
      "Matematika", "IPA", "IPS", "Bahasa Inggris", "Informatika",
      "PJOK", "Seni Rupa", "Seni Musik", "Prakarya", "Muatan Lokal"
    ],
    SMA: [
      "Pendidikan Agama & Budi Pekerti", "PPKn", "Bahasa Indonesia",
      "Matematika", "Sejarah", "Bahasa Inggris", "PJOK",
      "Seni Rupa", "Seni Musik", "Fisika", "Kimia", "Biologi",
      "Ekonomi", "Geografi", "Sosiologi", "Informatika",
      "Bahasa Asing", "Muatan Lokal"
    ],
    SMK: [
      "Pendidikan Agama & Budi Pekerti", "PPKn", "Bahasa Indonesia",
      "Matematika", "Sejarah", "Bahasa Inggris", "Informatika", "PJOK",
      "Seni Rupa", "Seni Musik", "Seni Tari", "Seni Teater",
      "Mata Pelajaran Kejuruan / Produktif", "Koding dan Kecerdasan Artifisial", "Muatan Lokal"
    ]
  },

  SEMESTER: ["1 (Ganjil)", "2 (Genap)"],

  mapelList: function (jenjang, kelas) {
    var list = (this.MAPEL[jenjang] || []).slice();
    var k = parseInt(kelas, 10);
    if ((jenjang === "SD" && k >= 5) || (jenjang === "SMP" && k >= 7) ||
        ((jenjang === "SMA" || jenjang === "SMK") && k >= 10)) {
      if (list.indexOf("Koding dan Kecerdasan Artifisial") < 0) list.push("Koding dan Kecerdasan Artifisial");
    }
    return list;
  },

  /* Alokasi waktu per jenjang (1 JP: SD=35 mnt, SMP=40 mnt, SMA/SMK=45 mnt) */
  ALOKASI: {
    SD: ["1 × 35 menit", "2 × 35 menit", "3 × 35 menit", "4 × 35 menit",
         "5 × 35 menit", "6 × 35 menit"],
    SMP: ["1 × 40 menit", "2 × 40 menit", "3 × 40 menit", "4 × 40 menit",
          "5 × 40 menit", "6 × 40 menit"],
    SMA: ["1 × 45 menit", "2 × 45 menit", "3 × 45 menit", "4 × 45 menit"],
    SMK: ["1 × 45 menit", "2 × 45 menit", "3 × 45 menit", "4 × 45 menit"]
  },

  DURASI: ["5 menit", "10 menit", "15 menit", "20 menit", "30 menit", "45 menit", "60 menit"],

  /* Materi pokok per mapel per semester (dipilih via datalist, tetap bisa ketik bebas).
     Format: "Mapel": { "1": [...sem ganjil...], "2": [...sem genap...] } */
  MATERI: {
    "Matematika": {
      "1": ["Bilangan bulat", "Pecahan", "Bentuk aljabar", "Persamaan linear satu variabel",
        "Perbandingan dan skala", "Pola bilangan", "Koordinat kartesius", "Relasi dan fungsi",
        "Bilangan berpangkat dan bentuk akar", "Persamaan kuadrat"],
      "2": ["Himpunan", "Bangun datar (segitiga & segiempat)", "Statistika dasar", "Peluang",
        "Teorema Pythagoras", "Bangun ruang sisi datar", "Fungsi kuadrat",
        "Transformasi geometri", "Bangun ruang sisi lengkung"]
    },
    "IPA": {
      "1": ["Klasifikasi makhluk hidup", "Sel dan jaringan", "Sistem organ manusia",
        "Zat dan perubahannya", "Energi dan perubahannya", "Asam, basa, dan garam"],
      "2": ["Gaya dan gerak", "Listrik statis dan dinamis", "Kemagnetan", "Tata surya",
        "Ekosistem", "Pencemaran lingkungan", "Pewarisan sifat", "Bioteknologi"]
    },
    "IPAS": {
      "1": ["Bagian tumbuhan dan fungsinya", "Benda dan sifatnya", "Daur air",
        "Gaya dan gerak sederhana", "Lingkungan sehat"],
      "2": ["Rantai makanan", "Energi alternatif", "Sistem organ manusia",
        "Ekosistem dan pelestariannya"]
    },
    "Bahasa Indonesia": {
      "1": ["Teks deskripsi", "Teks narasi", "Puisi rakyat", "Ejaan dan tanda baca",
        "Tata bahasa (SPOK)"],
      "2": ["Teks eksposisi", "Teks argumentasi", "Cerpen", "Drama", "Pidato",
        "Surat resmi", "Karya ilmiah"]
    },
    "Bahasa Inggris": {
      "1": ["Greeting and introduction", "Describing people", "Simple present tense",
        "Descriptive text"],
      "2": ["Past tense", "Future tense", "Recount text", "Procedure text", "Narrative text"]
    },
    "PPKn": {
      "1": ["Pancasila", "UUD 1945", "Bhinneka Tunggal Ika", "Hak dan kewajiban warga"],
      "2": ["Demokrasi", "Sistem pemerintahan", "Otonomi daerah", "Globalisasi"]
    },
    "IPS": {
      "1": ["Peta dan globe", "Interaksi sosial", "Kenampakan alam", "Potensi SDA Indonesia"],
      "2": ["Kegiatan ekonomi", "Sejarah kemerdekaan Indonesia", "ASEAN"]
    },
    "Informatika": {
      "1": ["Berpikir komputasional", "Algoritma dan flowchart", "Data dan representasi"],
      "2": ["Pemrograman dasar", "Jaringan komputer", "Keamanan digital"]
    },
    "PJOK": {
      "1": ["Gerak dasar lokomotor", "Permainan bola besar", "Kebugaran jasmani", "Pola hidup sehat"],
      "2": ["Permainan bola kecil", "Atletik dasar", "Senam lantai", "Renang dasar"]
    },
    "Sejarah": {
      "1": ["Manusia purba", "Kerajaan Hindu-Buddha", "Kerajaan Islam"],
      "2": ["Kolonialisme", "Pergerakan nasional", "Proklamasi kemerdekaan", "Orde Baru dan Reformasi"]
    },
    "Fisika": {
      "1": ["Besaran dan satuan", "Gerak lurus", "Hukum Newton", "Usaha dan energi"],
      "2": ["Tekanan", "Getaran dan gelombang", "Optik", "Listrik dinamis"]
    },
    "Kimia": {
      "1": ["Struktur atom", "Sistem periodik", "Ikatan kimia", "Stoikiometri"],
      "2": ["Larutan", "Asam basa", "Redoks", "Hidrokarbon"]
    },
    "Biologi": {
      "1": ["Sel", "Jaringan tumbuhan dan hewan", "Sistem pencernaan", "Sistem peredaran darah"],
      "2": ["Sistem saraf", "Fotosintesis", "Genetika", "Evolusi", "Ekologi"]
    },
    "Ekonomi": {
      "1": ["Kebutuhan dan kelangkaan", "Pasar", "Uang dan bank"],
      "2": ["Inflasi", "APBN dan APBD", "Kewirausahaan", "Akuntansi dasar"]
    },
    "Geografi": {
      "1": ["Peta dan penginderaan jauh", "Litosfer", "Atmosfer"],
      "2": ["Hidrosfer", "Biosfer", "Antroposfer", "Mitigasi bencana"]
    },
    "Sosiologi": {
      "1": ["Interaksi sosial", "Kelompok sosial", "Stratifikasi sosial"],
      "2": ["Mobilitas sosial", "Konflik sosial", "Lembaga sosial", "Penelitian sosial"]
    },
    "Prakarya": {
      "1": ["Kerajinan bahan lunak", "Kerajinan bahan keras"],
      "2": ["Rekayasa", "Budidaya tanaman", "Pengolahan makanan"]
    },
    "Seni Rupa": {
      "1": ["Menggambar", "Apresiasi karya seni"],
      "2": ["Melukis", "Seni kriya"]
    },
    "Seni Musik": {
      "1": ["Bernyanyi", "Alat musik ritmis"],
      "2": ["Alat musik melodis", "Apresiasi musik"]
    }
  },

  /* Ringkasan CP umum per mapel per fase (opsional — textarea tetap bisa ditempel manual) */
  CP: {
    "Matematika": {
      A: ["Peserta didik dapat membaca, menulis, dan membandingkan bilangan cacah sampai 100 serta melakukan penjumlahan dan pengurangan.",
          "Peserta didik dapat mengenal bangun datar sederhana dan mengukur panjang dengan satuan tidak baku."],
      B: ["Peserta didik dapat berhitung bilangan cacah sampai 1.000, memahami pecahan sederhana, dan memecahkan masalah sehari-hari.",
          "Peserta didik dapat mengukur panjang, berat, dan waktu dengan satuan baku serta mengenal bangun datar dan ruang."],
      C: ["Peserta didik dapat berhitung bilangan bulat, pecahan, dan desimal serta menggunakannya dalam pemecahan masalah.",
          "Peserta didik dapat menentukan keliling dan luas bangun datar serta volume bangun ruang sederhana."],
      D: ["Peserta didik dapat melakukan operasi aljabar, menyelesaikan persamaan linear satu variabel, serta menggunakan perbandingan dan skala.",
          "Peserta didik dapat menyajikan dan menganalisis data dalam tabel/diagram serta menentukan peluang kejadian sederhana."],
      E: ["Peserta didik dapat menggunakan konsep fungsi, trigonometri, dan geometri untuk memecahkan masalah.",
          "Peserta didik dapat menganalisis data dan membuat inferensi sederhana menggunakan statistika."],
      F: ["Peserta didik dapat menggunakan konsep limit, turunan, dan integral dalam pemecahan masalah.",
          "Peserta didik dapat memodelkan fenomena dengan matriks, vektor, dan logika matematika."]
    },
    "Bahasa Indonesia": {
      A: ["Peserta didik dapat menyimak dan menceritakan kembali isi teks pendek serta menulis kalimat sederhana dengan ejaan tepat.",
          "Peserta didik dapat membaca nyaring teks pendek dengan lafal dan intonasi yang tepat."],
      B: ["Peserta didik dapat menemukan informasi dalam teks serta menulis paragraf deskripsi dan narasi sederhana.",
          "Peserta didik dapat membacakan puisi rakyat dengan ekspresi yang tepat."],
      C: ["Peserta didik dapat menganalisis struktur teks deskripsi, narasi, dan eksposisi serta menulis teks sesuai strukturnya.",
          "Peserta didik dapat berpidato singkat dengan bahasa santun dan sistematis."],
      D: ["Peserta didik dapat menganalisis teks eksposisi, argumentasi, dan karya sastra serta menulis teks argumentasi yang logis.",
          "Peserta didik dapat menyampaikan gagasan lisan dan tulis dengan kaidah kebahasaan yang tepat."],
      E: ["Peserta didik dapat menganalisis teks sastra dan non-sastra serta menulis karya ilmiah sederhana.",
          "Peserta didik dapat berdiskusi dan berdebat dengan argumen kritis dan santun."],
      F: ["Peserta didik dapat mengevaluasi berbagai teks serta menghasilkan karya tulis ilmiah dan sastra secara kreatif.",
          "Peserta didik dapat berkomunikasi dalam forum formal dengan bahasa Indonesia yang baik dan benar."]
    },
    "IPAS": {
      A: ["Peserta didik dapat mengidentifikasi bagian tubuh tumbuhan dan hewan serta kebutuhan makhluk hidup.",
          "Peserta didik dapat menjaga kebersihan lingkungan sekitar dan menjelaskan pentingnya hidup sehat."],
      B: ["Peserta didik dapat menjelaskan daur air, rantai makanan, dan perubahan wujud benda di lingkungan sekitar.",
          "Peserta didik dapat melakukan percobaan sederhana tentang gaya dan energi."],
      C: ["Peserta didik dapat menganalisis ekosistem, pencemaran lingkungan, dan upaya pelestariannya.",
          "Peserta didik dapat menjelaskan sistem organ manusia dan cara memelihara kesehatannya."]
    },
    "IPA": {
      D: ["Peserta didik dapat melakukan penyelidikan ilmiah sederhana tentang sistem organ, energi, dan zat serta mengomunikasikan hasilnya.",
          "Peserta didik dapat menganalisis konsep gaya, gerak, listrik, dan kemagnetan dalam kehidupan sehari-hari."]
    },
    "PPKn": {
      A: ["Peserta didik dapat menyebutkan simbol dan sila Pancasila serta menerapkannya dalam kehidupan sehari-hari.",
          "Peserta didik dapat menunjukkan sikap toleransi dan gotong royong di rumah dan sekolah."],
      B: ["Peserta didik dapat menjelaskan makna Bhinneka Tunggal Ika dan menghargai keberagaman.",
          "Peserta didik dapat menyebutkan hak dan kewajiban sebagai warga sekolah."],
      C: ["Peserta didik dapat menjelaskan nilai-nilai Pancasila dalam kehidupan berbangsa dan bernegara.",
          "Peserta didik dapat mempraktikkan musyawarah dalam pengambilan keputusan."],
      D: ["Peserta didik dapat menganalisis perumusan Pancasila dan UUD 1945 serta mengamalkan nilai-nilainya.",
          "Peserta didik dapat menjelaskan sistem demokrasi dan otonomi daerah di Indonesia."],
      E: ["Peserta didik dapat menganalisis ideologi negara dan konstitusi serta berpartisipasi aktif sebagai warga negara.",
          "Peserta didik dapat mengevaluasi dinamika demokrasi Indonesia dari masa ke masa."],
      F: ["Peserta didik dapat menganalisis isu kewarganegaraan kontemporer dan menawarkan solusi yang konstitusional.",
          "Peserta didik dapat menunjukkan karakter warga negara yang baik dalam kehidupan bermasyarakat."]
    },
    "Bahasa Inggris": {
      B: ["Peserta didik dapat menyapa, memperkenalkan diri, dan mendeskripsikan benda/hewan dalam bahasa Inggris sederhana.",
          "Peserta didik dapat memahami instruksi pendek dalam bahasa Inggris."],
      C: ["Peserta didik dapat mendeskripsikan orang, tempat, dan kegiatan menggunakan simple present tense.",
          "Peserta didik dapat menulis teks deskriptif pendek dengan tata bahasa yang tepat."],
      D: ["Peserta didik dapat menggunakan tenses dasar (present, past, future) dalam teks recount dan descriptive.",
          "Peserta didik dapat bercakap-cakap tentang kegiatan sehari-hari dengan pelafalan yang jelas."],
      E: ["Peserta didik dapat menganalisis teks naratif dan prosedural serta menulis teks fungsional pendek.",
          "Peserta didik dapat berdiskusi dan mempresentasikan pendapat dalam bahasa Inggris."],
      F: ["Peserta didik dapat memahami teks otentik dan menghasilkan teks argumentatif dalam bahasa Inggris.",
          "Peserta didik dapat berkomunikasi lisan dalam berbagai konteks formal dan informal."]
    },
    "IPS": {
      D: ["Peserta didik dapat membaca peta, menjelaskan interaksi sosial, dan menganalisis kegiatan ekonomi masyarakat.",
          "Peserta didik dapat menjelaskan potensi sumber daya alam Indonesia dan upaya pelestariannya."]
    },
    "Informatika": {
      D: ["Peserta didik dapat menerapkan berpikir komputasional untuk memecahkan masalah dan membuat algoritma sederhana.",
          "Peserta didik dapat menggunakan aplikasi perkantoran dan menjaga keamanan data pribadi di dunia digital."],
      E: ["Peserta didik dapat membuat program sederhana dan menganalisis jaringan komputer.",
          "Peserta didik dapat mengelola data serta memahami etika dan hukum di dunia digital."],
      F: ["Peserta didik dapat mengembangkan aplikasi sederhana dan mengevaluasi keamanan sistem informasi.",
          "Peserta didik dapat memanfaatkan teknologi untuk kewirausahaan digital secara bertanggung jawab."]
    }
  },

  "Koding dan Kecerdasan Artifisial": {
    C: ["Peserta didik memahami pola, algoritma, data, dan penggunaan teknologi AI secara aman dan bertanggung jawab."],
    D: ["Peserta didik menerapkan berpikir komputasional, dasar pemrograman, data, dan konsep AI untuk memecahkan masalah sederhana secara bertanggung jawab."],
    E: ["Peserta didik merancang solusi koding dan AI sederhana, menggunakan data secara tepat, serta menjelaskan risiko, etika, dan dampak penggunaan AI."],
    F: ["Peserta didik mengembangkan solusi koding dan AI yang lebih terstruktur, mengevaluasi hasilnya, dan mempertimbangkan keamanan, etika, bias, serta dampaknya."]
  },

  /* Fase dari nomor kelas: A:1-2, B:3-4, C:5-6, D:7-9, E:10, F:11-12 */
  faseOf: function (kelas) {
    var k = parseInt(kelas, 10);
    if (isNaN(k)) return "";
    if (k <= 2) return "A";
    if (k <= 4) return "B";
    if (k <= 6) return "C";
    if (k <= 9) return "D";
    if (k === 10) return "E";
    return "F";
  },

  cpList: function (mapel, fase) {
    if (this.CP[mapel] && this.CP[mapel][fase]) return this.CP[mapel][fase];
    return [];
  },

  coverage: function (mapel, jenjang, kelas, semester) {
    var alias = {
      "PPKn": jenjang === "SMA" || jenjang === "SMK" ? "PPKn-SMA" : "PPKn",
      "Informatika": (jenjang === "SMA" || jenjang === "SMK") ? "Informatika-SMA" : "Informatika",
      "Bahasa Inggris": jenjang === "SD" ? "Bahasa Inggris-SD" : (jenjang === "SMK" ? "Bahasa Inggris-SMK" : "Bahasa Inggris"),
      "Matematika": jenjang === "SMK" ? "Matematika-SMK" : "Matematika",
      "Bahasa Indonesia": jenjang === "SMK" ? "Bahasa Indonesia-SMK" : "Bahasa Indonesia",
      "PJOK": jenjang === "SMK" ? "PJOK-SMK" : "PJOK",
      "Sejarah": jenjang === "SMK" ? "Sejarah-SMK" : "Sejarah",
      "Koding dan Kecerdasan Artifisial": "Koding dan Kecerdasan Artifisial"
    };
    var key = alias[mapel] || mapel;
    var out = { mapel: mapel || "", jenjang: jenjang || "", kelas: kelas || "", semester: semester || "", materi: false, cp: false, exact: false };
    try {
      if (typeof GWMateri !== "undefined" && GWMateri[key] && GWMateri[key][jenjang] && GWMateri[key][jenjang][kelas]) {
        var node = GWMateri[key][jenjang][kelas];
        var rows = semester && node[semester] ? node[semester] : (node["1"] || []).concat(node["2"] || []);
        out.exact = true;
        out.materi = rows.length > 0;
        out.cp = rows.some(function (row) { return Array.isArray(row) && row[1] && String(row[1]).trim(); });
      }
    } catch (e) {}
    if (!out.cp) {
      var fase = this.faseOf(kelas);
      out.cp = !!(this.CP[key] && this.CP[key][fase]) || !!(this.CP[mapel] && this.CP[mapel][fase]);
    }
    return out;
  },

  materiList: function (mapel, jenjang, kelas, semester) {
    // Alias mapel: nama di form -> key di GWMateri
    var alias = {
      "PPKn": jenjang === "SMA" || jenjang === "SMK" ? "PPKn-SMA" : "PPKn",
      "Informatika": (jenjang === "SMA" || jenjang === "SMK") ? "Informatika-SMA" : "Informatika",
      "Bahasa Inggris": jenjang === "SD" ? "Bahasa Inggris-SD" : (jenjang === "SMK" ? "Bahasa Inggris-SMK" : "Bahasa Inggris"),
      "Matematika": jenjang === "SMK" ? "Matematika-SMK" : "Matematika",
      "Bahasa Indonesia": jenjang === "SMK" ? "Bahasa Indonesia-SMK" : "Bahasa Indonesia",
      "PJOK": jenjang === "SMK" ? "PJOK-SMK" : "PJOK",
      "Sejarah": jenjang === "SMK" ? "Sejarah-SMK" : "Sejarah",
      "Koding dan Kecerdasan Artifisial": "Koding dan Kecerdasan Artifisial"
    };
    var key = alias[mapel] || mapel;
    // Data riset (GWMateri): "Mapel" -> "Jenjang" -> "Kelas" -> "1"/"2" -> [[materi, CP], ...]
    try {
      if (typeof GWMateri !== "undefined" && GWMateri[key]) {
        var jm = GWMateri[key];
        // SMK memakai data SMA
        var node = jm[jenjang];
        if (node) {
          var kn = kelas ? node[kelas] : null;
          if (kn) {
            if (semester && kn[semester]) return kn[semester];
            // gabung semua semester
            var all = [];
            ["1", "2"].forEach(function (s) { if (kn[s]) all = all.concat(kn[s]); });
            if (all.length) return all;
          }
        }
      }
    } catch (e) {}
    // Jangan fallback lintas jenjang/kelas; data generik berisiko salah konteks.
    return [];
  },

  // CP yang sesuai dengan materi terpilih (untuk dropdown CP)
  cpForMateri: function (mapel, jenjang, kelas, semester, materi) {
    var list = this.materiList(mapel, jenjang, kelas, semester);
    for (var i = 0; i < list.length; i++) {
      if (list[i][0] === materi && list[i][1]) return list[i][1];
    }
    return "";
  }
};
