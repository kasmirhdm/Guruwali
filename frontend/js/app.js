/* GuruWali frontend — vanilla JS. Generator per seksi + chat + paket lengkap. */
(function () {
  "use strict";

  var state = { user: null, quota: null };

  function api(method, path, body) {
    var opts = { method: method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    return fetch(path, opts).then(function (r) {
      return r.json().then(function (j) { return { status: r.status, data: j }; });
    });
  }

  function $(id) { return document.getElementById(id); }

  function msg(el, text, cls) {
    el.textContent = text;
    el.className = "form-msg " + (cls || "");
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* ============ icon SVG premium (outline, gaya Lucide) ============ */
  var ICON_PATHS = {
    book: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>',
    user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    folder: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    clipboardCheck: '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><polyline points="9 14 11 16 15 12"/>',
    messageCircle: '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
    zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    fileText: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    copy: '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1-2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    check: '<polyline points="20 6 9 17 4 12"/>',
    checkCircle: '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    xCircle: '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
    sparkles: '<path d="M12 3l1.9 5.7a2 2 0 0 0 1.3 1.3L21 12l-5.7 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.7a2 2 0 0 0-1.3-1.3L3 12l5.7-1.9a2 2 0 0 0 1.3-1.3L12 3z"/>',
    loader: '<path d="M21 12a9 9 0 1 1-6.22-8.56"/>',
    star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'
  };
  function icon(name, size, filled) {
    var s = size || 18;
    var fill = filled ? ' fill="currentColor" stroke="currentColor"' : ' fill="none" stroke="currentColor"';
    return '<svg class="ic" width="' + s + '" height="' + s + '" viewBox="0 0 24 24"' + fill +
      ' stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      ICON_PATHS[name] + "</svg>";
  }

  /* ============ Model AI: smart routing + override manual ============ */
  var modelState = {
    list: [],
    override: (function () { try { return localStorage.getItem("gw_model") || ""; } catch (e) { return ""; } })()
  };

  function currentModelOverride() { return modelState.override || ""; }

  function initModelSelect() {
    var sel = $("modelSelect");
    if (!sel || sel.getAttribute("data-init")) return;
    sel.setAttribute("data-init", "1");
    sel.addEventListener("change", function () {
      modelState.override = sel.value || "";
      try {
        if (modelState.override) localStorage.setItem("gw_model", modelState.override);
        else localStorage.removeItem("gw_model");
      } catch (e) {}
    });
  }

  function loadModels() {
    var sel = $("modelSelect");
    if (!sel) return;
    api("GET", "/api/models").then(function (res) {
      if (res.status !== 200 || !res.data.models) return;
      modelState.list = res.data.models;
      var html = '<option value="">Otomatis (disarankan)</option>';
      res.data.models.forEach(function (m) {
        html += '<option value="' + esc(m.id) + '"' +
          (modelState.override === m.id ? " selected" : "") + ">" +
          esc(m.label) + "</option>";
      });
      sel.innerHTML = html;
      sel.classList.remove("hidden");
      // override tersimpan tapi tak ada di daftar (mis. ganti provider) -> reset ke Otomatis
      if (modelState.override && !res.data.models.some(function (m) { return m.id === modelState.override; })) {
        modelState.override = "";
        try { localStorage.removeItem("gw_model"); } catch (e) {}
        sel.value = "";
      }
    });
  }

  /* ================= navigasi 12 seksi ================= */
  var SECTIONS = ["beranda", "perangkat", "materi", "soal", "penilaian", "media",
                  "alat", "admin", "dokumen", "chat", "riwayat", "profil"];

  function showSection(name) {
    if (SECTIONS.indexOf(name) < 0) name = "beranda";
    SECTIONS.forEach(function (s) {
      var el = $("sec-" + s);
      if (el) el.classList.toggle("hidden", s !== name);
    });
    var links = document.querySelectorAll("#appNav a");
    links.forEach(function (a) {
      a.classList.toggle("active", a.getAttribute("data-section") === name);
    });
    $("appNav").classList.remove("open");
    if (name === "riwayat") loadDocs();
    if (name === "beranda") { loadRecent(); refreshQuotaUI(); }
  }

  function route() {
    var h = (location.hash || "#beranda").replace("#", "");
    if (h === "daftar") { showAuth("register"); return; }
    showSection(h);
  }

  /* ================= auth ================= */
  function showAuth(which) {
    $("authBox").classList.remove("hidden");
    document.querySelectorAll(".app-section").forEach(function (s) { s.classList.add("hidden"); });
    setAuthTab(which);
  }
  function hideAuth() { $("authBox").classList.add("hidden"); }

  function setAuthTab(which) {
    var login = which !== "register";
    $("tabMasuk").classList.toggle("active", login);
    $("tabDaftar").classList.toggle("active", !login);
    $("loginForm").classList.toggle("hidden", !login);
    $("registerForm").classList.toggle("hidden", login);
  }

  function refreshAuthUI() {
    var logged = !!state.user;
    $("authBox").classList.toggle("hidden", logged);
    $("logoutBtn").classList.toggle("hidden", !logged);
    var badge = $("userBadge");
    badge.classList.toggle("hidden", !logged);
    if (logged) badge.innerHTML = icon("user", 16) + " " + esc(state.user.nama || state.user.email);
    if (logged) { hideAuth(); route(); fillProfile(); buildQuickAccess(); buildGenerators(); loadModels(); }
    else { showAuth("login"); var ms = $("modelSelect"); if (ms) ms.classList.add("hidden"); }
  }

  function loadMe() {
    return api("GET", "/api/me").then(function (res) {
      state.user = res.status === 200 ? res.data.user : null;
      if (state.user) state.quota = {
        used: state.user.quota_used, limit: state.user.quota_limit, is_pro: state.user.is_pro
      };
      refreshAuthUI();
    }).catch(function () {
      state.user = null; refreshAuthUI();
    });
  }

  /* ================= dokumen ================= */
  function docItem(d) {
    var date = new Date(d.updated_at * 1000).toLocaleDateString("id-ID");
    var fav = icon("star", 18, !!d.is_favorite);
    return '<div class="doc-item" data-id="' + d.id + '">' +
      '<div><div class="doc-type">' + esc(d.type) + '</div>' +
      '<div class="doc-title">' + esc(d.title) + '</div>' +
      '<div class="doc-date">' + date + '</div></div>' +
      '<div class="doc-actions">' +
      '<button class="icon-btn fav-btn" title="Favorit">' + fav + '</button>' +
      '<button class="icon-btn word-btn" title="Download Word">' + icon("download", 18) + '</button>' +
      '<button class="icon-btn pdf-btn" title="Download PDF">' + icon("fileText", 18) + '</button>' +
      '<button class="icon-btn del-btn" title="Hapus">' + icon("trash", 18) + '</button>' +
      '</div></div>';
  }

  function bindDocButtons(box) {
    box.querySelectorAll(".doc-item").forEach(function (el) {
      var id = el.getAttribute("data-id");
      el.querySelector(".fav-btn").addEventListener("click", function () {
        api("POST", "/api/documents/" + id + "/favorite").then(loadDocsIfVisible);
      });
      el.querySelector(".del-btn").addEventListener("click", function () {
        if (!confirm("Hapus dokumen ini?")) return;
        api("DELETE", "/api/documents/" + id).then(loadDocsIfVisible);
      });
      el.querySelector(".word-btn").addEventListener("click", function () {
        dlExport(id, "docx");
      });
      el.querySelector(".pdf-btn").addEventListener("click", function () {
        dlExport(id, "pdf");
      });
    });
  }

  function loadDocsIfVisible() {
    if (!$("sec-riwayat").classList.contains("hidden")) loadDocs();
    if (!$("sec-beranda").classList.contains("hidden")) loadRecent();
  }

  function loadDocs() {
    var type = $("filterType").value;
    var fav = $("filterFav").checked ? "&favorite=1" : "";
    var q = "/api/documents?" + (type ? "type=" + encodeURIComponent(type) : "") + fav;
    api("GET", q).then(function (res) {
      var box = $("docList");
      if (res.status !== 200 || !res.data.documents.length) {
        box.innerHTML = '<p class="muted">Belum ada dokumen.</p>';
        return;
      }
      box.innerHTML = res.data.documents.map(docItem).join("");
      bindDocButtons(box);
    });
  }

  function loadRecent() {
    api("GET", "/api/documents").then(function (res) {
      var box = $("recentDocs");
      if (res.status !== 200 || !res.data.documents.length) {
        box.innerHTML = '<p class="muted">Belum ada dokumen.</p>';
        return;
      }
      box.innerHTML = res.data.documents.slice(0, 5).map(docItem).join("");
      bindDocButtons(box);
    });
  }

  /* ================= beranda ================= */
  var QUICK = [
    ["perangkat", "folder", "Perangkat Ajar", "Modul Ajar, RPP, ATP…"],
    ["materi", "book", "Materi", "Materi & ringkasan"],
    ["soal", "clipboardCheck", "Soal & Evaluasi", "PG, uraian, HOTS…"],
    ["chat", "messageCircle", "Chat AI", "Tanya AI guru"],
  ];
  function buildQuickAccess() {
    $("quickAccess").innerHTML = QUICK.map(function (q) {
      return '<a class="card" href="#' + q[0] + '" style="text-decoration:none;color:inherit">' +
        '<h3>' + icon(q[1], 22) + " " + q[2] + "</h3><p>" + q[3] + "</p></a>";
    }).join("");
  }

  function refreshQuotaUI() {
    var q = state.quota;
    var txt = q ? (q.used + " / " + q.limit + (q.is_pro ? " (Pro)" : "")) : "";
    if ($("pkQuota")) $("pkQuota").value = txt;
  }

  /* ================= profil ================= */
  function fillProfile() {
    if (!state.user) return;
    $("pfNama").value = state.user.nama || "";
    $("pfSekolah").value = state.user.sekolah || "";
    $("pfMapel").value = state.user.mapel || "";
    $("pfJenjang").value = state.user.jenjang || "";
    $("pfQuota").value = state.user.quota_used + " / " + state.user.quota_limit +
      (state.user.is_pro ? " (Pro)" : "");
  }

  /* ============================================================
     GENERATOR — form unik per tipe, dirender dinamis dari registry
     field: [name, label, kind, opts, required, placeholder]
     kind: text | number | select | textarea
     ============================================================ */
  var JENJANG = ["SD", "SMP", "SMA", "SMK"];
  var FASE = ["A", "B", "C", "D", "E", "F"];
  var SEMESTER = ["Ganjil", "Genap"];
  var MODEL = ["Problem Based Learning", "Project Based Learning",
               "Discovery Learning", "Inkuiri", "Kooperatif", "Pembelajaran Mendalam"];

  function base(mapelReq) {
    return [
      ["jenjang", "Jenjang", "select", JENJANG, 1],
      ["semester", "Semester", "select", SEMESTER, 1],
      ["mapel", "Mata pelajaran", "text", "", mapelReq === false ? 0 : 1, ""],
      ["kelas", "Kelas", "text", "", 1, "cth: 7"],
      ["materi", "Materi pokok", "materi", "", 1, ""]
    ];
  }
  var CP_FIELD = ["cp", "Capaian Pembelajaran (tempel dari dokumen resmi)", "textarea", "",
                  0, "Tempel CP di sini. Jika kosong, AI TIDAK akan mengarang CP."];

  var GENERATORS = {
    /* ---- Perangkat Ajar ---- */
    "modul-ajar": { sec: "perangkat", label: "Modul Ajar",
      desc: "Modul Ajar lengkap template 2025 (A–E) + Pembelajaran Mendalam.",
      fields: base().concat([CP_FIELD,
        ["alokasi", "Alokasi waktu", "text", "", 0, "cth: 3 x 40 menit"],
        ["model", "Model pembelajaran", "select", MODEL, 0]]) },
    "rpp": { sec: "perangkat", label: "RPP",
      desc: "Rencana Pelaksanaan Pembelajaran + asesmen & KKTP.",
      fields: base().concat([CP_FIELD,
        ["alokasi", "Alokasi waktu", "text", "", 0, "cth: 2 x 40 menit"]]) },
    "atp": { sec: "perangkat", label: "ATP",
      desc: "Alur Tujuan Pembelajaran per fase, berurutan + alokasi JP.",
      fields: [
        ["jenjang", "Jenjang", "select", JENJANG, 1],
        ["semester", "Semester", "select", SEMESTER, 0],
        ["mapel", "Mata pelajaran", "text", "", 1, ""],
        ["fase", "Fase", "select", FASE, 1],
        CP_FIELD] },
    "tujuan-pembelajaran": { sec: "perangkat", label: "Tujuan Pembelajaran",
      desc: "TP operasional & terukur dari CP/materi.",
      fields: base().concat([CP_FIELD]) },
    "kktp": { sec: "perangkat", label: "KKTP",
      desc: "Kriteria Ketercapaian Tujuan Pembelajaran (pengganti KKM).",
      fields: base() },
    "program-tahunan": { sec: "perangkat", label: "Program Tahunan (Prota)",
      desc: "Tabel cakupan materi satu tahun ajaran.",
      fields: [
        ["mapel", "Mata pelajaran", "text", "", 1, ""],
        ["jenjang", "Jenjang", "select", JENJANG, 1],
        ["kelas", "Kelas", "text", "", 1, "cth: 7"]] },
    "program-semester": { sec: "perangkat", label: "Program Semester (Prosem)",
      desc: "Rincian mingguan satu semester.",
      fields: [
        ["mapel", "Mata pelajaran", "text", "", 1, ""],
        ["jenjang", "Jenjang", "select", JENJANG, 1],
        ["kelas", "Kelas", "text", "", 1, "cth: 7"],
        ["semester", "Semester", "select", SEMESTER, 1]] },
    "remedial": { sec: "perangkat", label: "Program Remedial",
      desc: "Program untuk peserta didik belum mencapai KKTP.",
      fields: base() },
    "pengayaan": { sec: "perangkat", label: "Program Pengayaan",
      desc: "Aktivitas menantang untuk yang sudah melampaui KKTP.",
      fields: base() },
    /* ---- Materi ---- */
    "materi": { sec: "materi", label: "Materi Pembelajaran",
      desc: "Bahan ajar lengkap untuk guru + pertanyaan pemantik.",
      fields: base().concat([
        ["kedalaman", "Kedalaman", "select", ["Ringkas", "Sedang", "Mendalam"], 0]]) },
    "ringkasan-materi": { sec: "materi", label: "Ringkasan Materi",
      desc: "Poin kunci padat untuk review cepat.",
      fields: [
        ["materi", "Materi pokok", "materi", "", 1, ""],
        ["jenjang", "Jenjang", "select", JENJANG, 1]] },
    "materi-siswa": { sec: "materi", label: "Materi Versi Siswa",
      desc: "Materi dengan bahasa ramah sesuai jenjang.",
      fields: [
        ["materi", "Materi pokok", "materi", "", 1, ""],
        ["jenjang", "Jenjang", "select", JENJANG, 1],
        ["kelas", "Kelas", "text", "", 1, "cth: 7"]] },
    /* ---- Soal & Evaluasi ---- */
    "soal-pg": { sec: "soal", label: "Soal Pilihan Ganda",
      desc: "PG + kunci jawaban & pembahasan otomatis.",
      fields: base().concat([
        ["jumlah", "Jumlah soal", "number", 10, 0],
        ["level", "Level kognitif", "select", ["Campuran C1-C6", "C1-C3 (LOTS)", "C4-C6 (HOTS)"], 0]]) },
    "soal-uraian": { sec: "soal", label: "Soal Uraian",
      desc: "Uraian + pedoman penskoran, kunci & pembahasan otomatis.",
      fields: base().concat([
        ["jumlah", "Jumlah soal", "number", 5, 0]]) },
    "soal-hots": { sec: "soal", label: "Soal HOTS",
      desc: "Soal C4-C6 berbasis stimulus autentik.",
      fields: base().concat([
        ["jumlah", "Jumlah soal", "number", 5, 0]]) },
    "kisi-kisi": { sec: "soal", label: "Kisi-kisi Soal",
      desc: "Tabel kisi-kisi: TP, indikator, level, bentuk soal.",
      fields: base().concat([
        ["jumlah", "Jumlah soal", "number", 10, 0],
        ["bentuk", "Bentuk soal", "select", ["Campuran", "Pilihan Ganda", "Uraian"], 0]]) },
    "kunci-jawaban": { sec: "soal", label: "Kunci Jawaban",
      desc: "Kunci dari soal yang ditempel.",
      fields: [
        ["mapel", "Mata pelajaran", "text", "", 0, ""],
        ["soal", "Tempel soal di sini", "textarea", "", 1, "Tempel teks soal…"]] },
    "pembahasan": { sec: "soal", label: "Pembahasan Soal",
      desc: "Pembahasan per soal dengan bahasa siswa.",
      fields: [
        ["mapel", "Mata pelajaran", "text", "", 0, ""],
        ["soal", "Tempel soal di sini", "textarea", "", 1, "Tempel teks soal…"]] },
    /* ---- Media ---- */
    "lkpd": { sec: "media", label: "LKPD",
      desc: "Lembar Kerja Peserta Didik 8 komponen.",
      fields: base().concat([
        ["alokasi", "Alokasi waktu", "text", "", 0, "cth: 2 x 40 menit"]]) },
    "worksheet": { sec: "media", label: "Worksheet",
      desc: "Latihan mandiri bervariasi + kunci.",
      fields: base() },
    "ppt-outline": { sec: "media", label: "Outline PPT",
      desc: "Kerangka slide + narasi guru.",
      fields: [
        ["mapel", "Mata pelajaran", "text", "", 1, ""],
        ["kelas", "Kelas", "text", "", 1, "cth: 7"],
        ["materi", "Materi pokok", "materi", "", 1, ""],
        ["jumlah", "Jumlah slide", "number", 10, 0]] },
    "gambar-ilustrasi": { sec: "media", label: "Ilustrasi Gambar AI",
      desc: "Generate ilustrasi untuk media pembelajaran (2 kuota).",
      imageGen: true,
      fields: [
        ["prompt", "Deskripsi gambar", "textarea", "", 1, "cth: Anak SD belajar fotosintesis di kebun sekolah"],
        ["style", "Gaya gambar", "select",
          ["Kartun edukasi", "Realistis", "Sketsa", "Flat design", "Infografis sederhana"], 0]] },
    /* ---- Alat Bantu ---- */
    "rubrik": { sec: "alat", label: "Rubrik Penilaian",
      desc: "Rubrik 4 level + cara skor & kaitan KKTP.",
      fields: [
        ["mapel", "Mata pelajaran", "text", "", 0, ""],
        ["kelas", "Kelas", "text", "", 0, "cth: 7"],
        ["materi", "Materi/tugas yang dinilai", "text", "", 1, ""],
        ["aspek", "Aspek yang dinilai", "textarea", "", 1, "cth: kelengkapan isi, kreativitas, kerja sama…"]] },
    "ice-breaking": { sec: "alat", label: "Ice Breaking",
      desc: "5 ide permainan pembuka yang seru.",
      fields: [
        ["jenjang", "Jenjang", "select", JENJANG, 1],
        ["kelas", "Kelas", "text", "", 0, "cth: 7"],
        ["durasi", "Durasi", "text", "", 0, "cth: 10 menit"],
        ["tema", "Tema materi (opsional)", "text", "", 0, ""]] },
    "refleksi": { sec: "alat", label: "Pertanyaan Refleksi",
      desc: "10 pertanyaan refleksi tahap Merefleksi.",
      fields: [
        ["materi", "Materi pokok", "materi", "", 1, ""],
        ["jenjang", "Jenjang", "select", JENJANG, 1],
        ["sasaran", "Untuk", "select", ["Murid", "Guru"], 1]] },
    "jurnal-mengajar": { sec: "alat", label: "Jurnal Mengajar",
      desc: "Template jurnal + contoh pengisian.",
      fields: [
        ["mapel", "Mata pelajaran", "text", "", 1, ""],
        ["kelas", "Kelas", "text", "", 1, "cth: 7"],
        ["materi", "Materi pokok", "materi", "", 1, ""],
        ["tanggal", "Tanggal", "text", "", 0, "cth: 2026-10-08"]] },
    /* ---- Administrasi ---- */
    "surat-tugas": { sec: "admin", label: "Surat Tugas",
      desc: "Surat tugas resmi format baku.",
      fields: [
        ["nama", "Nama yang ditugaskan", "text", "", 1, ""],
        ["nip", "NIP (opsional)", "text", "", 0, ""],
        ["keperluan", "Keperluan tugas", "text", "", 1, ""],
        ["tanggal", "Tanggal", "text", "", 1, "cth: 10 Oktober 2026"],
        ["tempat", "Tempat", "text", "", 0, ""]] },
    "berita-acara": { sec: "admin", label: "Berita Acara",
      desc: "Berita acara kegiatan format resmi.",
      fields: [
        ["kegiatan", "Nama kegiatan", "text", "", 1, ""],
        ["tanggal", "Tanggal", "text", "", 1, "cth: 10 Oktober 2026"],
        ["tempat", "Tempat", "text", "", 0, ""],
        ["hasil", "Hasil/keputusan kegiatan", "textarea", "", 1, "Tulis poin-poin hasil…"]] },
    "proposal": { sec: "admin", label: "Proposal Kegiatan",
      desc: "Proposal lengkap + anggaran & pengesahan.",
      fields: [
        ["kegiatan", "Nama kegiatan", "text", "", 1, ""],
        ["latar", "Latar belakang", "textarea", "", 1, "Tulis latar belakang…"],
        ["tujuan", "Tujuan kegiatan", "textarea", "", 0, ""],
        ["tanggal", "Waktu pelaksanaan", "text", "", 0, ""]] }
  };

  var PAKET_TYPES = ["modul-ajar", "materi", "lkpd", "kisi-kisi", "soal-pg",
                     "kunci-jawaban", "pembahasan", "rubrik", "remedial",
                     "pengayaan", "ppt-outline"];

  function fieldHTML(f) {
    var name = f[0], label = f[1], kind = f[2], opts = f[3],
        req = f[4] ? " required" : "", ph = f[5] || "";
    var h = "<label>" + esc(label) + (f[4] ? " *" : "");
    if (kind === "select") {
      h += '<select name="' + name + '"' + req + ">";
      if (!f[4]) h += '<option value="">— Pilih —</option>';
      opts.forEach(function (o) { h += "<option>" + esc(o) + "</option>"; });
      h += "</select>";
    } else if (kind === "materi") {
      // Dropdown materi tersaring mapel+semester + opsi ketik manual (mobile-friendly)
      h += '<select class="gw-materi-sel"' + req + '><option value="">— Pilih materi —</option></select>';
      h += '<input type="text" name="' + name + '" class="gw-materi-custom hidden" placeholder="Ketik materi manual..."' + req + ">";
    } else if (kind === "textarea") {
      h += '<textarea name="' + name + '" rows="3" placeholder="' + esc(ph) + '"' + req + "></textarea>";
    } else if (kind === "number") {
      h += '<input type="number" name="' + name + '" value="' + esc(opts) + '" min="1" max="50">';
    } else {
      h += '<input type="text" name="' + name + '" placeholder="' + esc(ph) + '"' + req + ">";
    }
    return h + "</label>";
  }

  function buildGenerators() {
    // bangun kartu generator per seksi (sekali saja)
    ["perangkat", "materi", "soal", "media", "alat", "admin"].forEach(function (sec) {
      var box = $("gen-" + sec);
      if (!box || box.getAttribute("data-built")) return;
      box.setAttribute("data-built", "1");
      Object.keys(GENERATORS).forEach(function (type) {
        var g = GENERATORS[type];
        if (g.sec !== sec) return;
        var card = document.createElement("div");
        card.className = "gen-card";
        card.innerHTML =
          '<div class="gen-head" data-type="' + type + '">' +
          "<div><strong>" + esc(g.label) + "</strong>" +
          '<p class="muted small">' + esc(g.desc) + "</p></div>" +
          '<span class="gen-toggle">▾</span></div>' +
          '<form class="gen-form hidden" data-type="' + type + '">' +
          g.fields.map(fieldHTML).join("") +
          '<p class="form-msg"></p>' +
          '<button class="btn btn-primary" type="submit">' + icon("sparkles", 18) + " Buatkan " + esc(g.label) + "</button>" +
          "</form>";
        box.appendChild(card);
      });
      box.querySelectorAll(".gen-head").forEach(function (head) {
        head.addEventListener("click", function () {
          var form = head.parentNode.querySelector(".gen-form");
          form.classList.toggle("hidden");
          head.querySelector(".gen-toggle").textContent =
            form.classList.contains("hidden") ? "▾" : "▴";
        });
      });
      box.querySelectorAll(".gen-form").forEach(function (form) {
        if (typeof GWCascade !== "undefined") GWCascade.enhance(form);
        form.addEventListener("submit", function (e) {
          e.preventDefault();
          var type = form.getAttribute("data-type");
          var params = {};
          new FormData(form).forEach(function (v, k) { params[k] = v; });
          var msgEl = form.querySelector(".form-msg");
          if (GENERATORS[type] && GENERATORS[type].imageGen) {
            runGenerateImage(params, GENERATORS[type].sec, msgEl);
          } else {
            runGenerate(type, params, GENERATORS[type].sec, msgEl, true);
          }
        });
      });
    });
  }

  /* ---------- hasil generate ---------- */
  function dlExport(id, fmt) {
    window.location.href = "/api/documents/" + id + "/export?format=" + fmt;
  }

  function renderResult(sec, title, content, doc, modelLabel) {
    var box = $("res-" + sec);
    box.innerHTML =
      '<div class="result-panel"><h3>' + esc(title) + "</h3>" +
      (modelLabel ? '<span class="model-badge" title="Model AI yang dipakai">' + icon("zap", 13) + " " + esc(modelLabel) + "</span>" : "") +
      '<pre class="result-content">' + esc(content) + "</pre>" +
      '<div class="result-actions">' +
      '<button class="btn btn-ghost btn-copy">' + icon("copy", 16) + " Salin</button>" +
      (doc ? '<button class="btn btn-ghost btn-word">' + icon("download", 16) + " Word</button>" +
             '<button class="btn btn-ghost btn-pdf">' + icon("download", 16) + " PDF</button>" : "") +
      (doc ? '<span class="muted small">' + icon("check", 14) + " Tersimpan otomatis di Riwayat</span>"
            : '<span class="muted small">Tidak tersimpan otomatis</span>') +
      "</div></div>";
    box.querySelector(".btn-copy").addEventListener("click", function () {
      navigator.clipboard.writeText(content).then(function () {
        box.querySelector(".btn-copy").innerHTML = icon("check", 16) + " Tersalin!";
      });
    });
    if (doc) {
      box.querySelector(".btn-word").addEventListener("click", function () {
        dlExport(doc.id, "docx");
      });
      box.querySelector(".btn-pdf").addEventListener("click", function () {
        dlExport(doc.id, "pdf");
      });
    }
    box.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function runGenerate(type, params, sec, msgEl, save) {
    if (msgEl) msg(msgEl, "AI sedang menulis…", "");
    var box = $("res-" + sec);
    box.innerHTML = '<div class="result-panel"><p class="muted"><span class="spin">' + icon("loader", 16) + "</span> AI sedang menulis " +
      esc((GENERATORS[type] || {}).label || type) + "… mohon tunggu.</p></div>";
    return api("POST", "/api/generate", { type: type, params: params, save: save !== false, model: currentModelOverride() })
      .then(function (res) {
        if (res.status === 200) {
          if (res.data.quota) {
            state.quota = res.data.quota;
            state.user.quota_used = res.data.quota.used;
            refreshQuotaUI(); fillProfile();
          }
          var title = (res.data.document && res.data.document.title) ||
                      ((GENERATORS[type] || {}).label || type);
          renderResult(sec, title, res.data.content, res.data.document || null, res.data.model_label);
          if (msgEl) msg(msgEl, "", "");
          loadRecent();
          return res.data;
        }
        var err = res.data.error || "Gagal generate.";
        box.innerHTML = '<div class="result-panel"><p class="form-msg error">' + esc(err) + "</p></div>";
        if (msgEl) msg(msgEl, err, "error");
        return null;
      })
      .catch(function () {
        box.innerHTML = '<div class="result-panel"><p class="form-msg error">Koneksi gagal.</p></div>';
        return null;
      });
  }

  function runGenerateImage(params, sec, msgEl) {
    if (msgEl) msg(msgEl, "AI sedang menggambar…", "");
    var box = $("res-" + sec);
    box.innerHTML = '<div class="result-panel"><p class="muted"><span class="spin">' + icon("loader", 16) + "</span> AI sedang menggambar ilustrasi… mohon tunggu.</p></div>";
    return api("POST", "/api/generate-image", { prompt: params.prompt, style: params.style })
      .then(function (res) {
        if (res.status === 200) {
          if (res.data.quota) {
            state.quota = res.data.quota;
            state.user.quota_used = res.data.quota.used;
            refreshQuotaUI(); fillProfile();
          }
          var doc = res.data.document || null;
          var title = (doc && doc.title) || "Ilustrasi AI";
          var html = '<div class="result-panel"><h3>' + esc(title) + "</h3>" +
            '<img src="' + esc(res.data.image_url) + '" alt="Ilustrasi AI" style="max-width:100%;border-radius:12px;margin:12px 0;">' +
            '<div><a class="btn btn-primary btn-small" href="' + esc(res.data.image_url) + '" download>Unduh Gambar</a></div></div>';
          box.innerHTML = html;
          if (msgEl) msg(msgEl, "", "");
          loadRecent();
          return res.data;
        }
        var err = (res.data && res.data.error) || "Gagal generate gambar.";
        box.innerHTML = '<div class="result-panel"><p class="form-msg error">' + esc(err) + "</p></div>";
        if (msgEl) msg(msgEl, err, "error");
        return null;
      })
      .catch(function () {
        box.innerHTML = '<div class="result-panel"><p class="form-msg error">Koneksi gagal.</p></div>';
        return null;
      });
  }

  /* ================= chat ================= */
  var chatHistory = [];

  function chatMsg(role, text, saveBtn, typing) {
    var box = $("chatBox");
    var div = document.createElement("div");
    div.className = "chat-msg " + role;
    div.innerHTML = "<div><strong>" + (role === "user" ? "Anda" : "GuruWali AI") +
      "</strong></div><pre>" + (typing ? '<span class="spin">' + icon("loader", 16) + "</span> " : "") +
      esc(text) + "</pre>";
    if (saveBtn) {
      var btn = document.createElement("button");
      btn.className = "btn btn-ghost btn-small";
      btn.innerHTML = icon("save", 16) + " Simpan ke Riwayat";
      btn.addEventListener("click", function () {
        api("POST", "/api/documents", {
          type: "chat-bebas",
          title: "Chat: " + text.slice(0, 50),
          content: text
        }).then(function (res) {
          btn.innerHTML = res.status === 200 ? icon("check", 16) + " Tersimpan" : "Gagal menyimpan";
          loadRecent();
        });
      });
      div.appendChild(btn);
    }
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  function initChat() {
    var form = $("chatForm");
    if (!form || form.getAttribute("data-init")) return;
    form.setAttribute("data-init", "1");
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var input = $("chatInput");
      var pesan = input.value.trim();
      if (!pesan) return;
      input.value = "";
      chatMsg("user", pesan, false);
      chatHistory.push({ role: "user", content: pesan });
      chatMsg("ai", "Mengetik…", false, true);
      var typing = $("chatBox").lastChild;
      api("POST", "/api/generate", {
        type: "chat-bebas", params: { pesan: pesan }, save: false, model: currentModelOverride()
      }).then(function (res) {
        typing.remove();
        if (res.status === 200) {
          if (res.data.quota) {
            state.quota = res.data.quota;
            state.user.quota_used = res.data.quota.used;
            refreshQuotaUI(); fillProfile();
          }
          chatHistory.push({ role: "assistant", content: res.data.content });
          chatMsg("ai", res.data.content, true);
        } else {
          chatMsg("ai", (res.data.error || "Gagal."), false);
        }
      });
    });
  }

  /* ================= paket lengkap: 1 input -> 11 dokumen ================= */
  var PAKET_LABELS = {
    "modul-ajar": "Modul Ajar", "materi": "Materi", "lkpd": "LKPD",
    "kisi-kisi": "Kisi-kisi", "soal-pg": "Soal", "kunci-jawaban": "Kunci Jawaban",
    "pembahasan": "Pembahasan", "rubrik": "Rubrik", "remedial": "Remedial",
    "pengayaan": "Pengayaan", "ppt-outline": "Outline PPT"
  };

  function initPackage() {
    var form = $("packageForm");
    if (!form || form.getAttribute("data-init")) return;
    form.setAttribute("data-init", "1");
    if (typeof GWCascade !== "undefined") GWCascade.enhance(form);
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      var params = {
        mapel: $("pkMapel").value.trim(),
        jenjang: $("pkJenjang").value,
        kelas: $("pkKelas").value.trim(),
        semester: $("pkSemester") ? $("pkSemester").value : "",
        materi: $("pkMateri").value.trim(),
        alokasi: $("pkAlokasi").value.trim(),
        cp: $("pkCp").value.trim()
      };
      if (!params.mapel || !params.kelas || !params.materi) {
        msg($("pkMsg"), "Mata pelajaran, kelas, dan materi wajib diisi.", "error");
        return;
      }
      btn.disabled = true;
      msg($("pkMsg"), "", "");
      var prog = $("packageProgress");
      prog.classList.remove("hidden");
      prog.innerHTML = "<h4>Progres pembuatan:</h4>" + PAKET_TYPES.map(function (t, i) {
        return '<div class="pkg-row" id="pkg-' + i + '"><span class="spin">' + icon("loader", 16) + "</span> " +
               esc((i + 1) + ". " + PAKET_LABELS[t]) + "</div>";
      }).join("");
      var done = 0, failed = 0, lastSoal = "";
      function step(i) {
        if (i >= PAKET_TYPES.length) {
          btn.disabled = false;
          msg($("pkMsg"), "Selesai: " + done + " dokumen berhasil" +
              (failed ? ", " + failed + " gagal" : "") + ". Lihat di Riwayat.", done ? "ok" : "error");
          loadRecent(); refreshQuotaUI();
          return;
        }
        var t = PAKET_TYPES[i];
        var row = $("pkg-" + i);
        var p = Object.assign({}, params);
        // kunci & pembahasan memakai soal yang baru dibuat agar konsisten
        if ((t === "kunci-jawaban" || t === "pembahasan") && lastSoal) p.soal = lastSoal;
        api("POST", "/api/generate", { type: t, params: p, save: true, model: currentModelOverride() }).then(function (res) {
          if (res.status === 200) {
            done++;
            row.classList.add("ok"); var sp = row.querySelector("span"); sp.classList.remove("spin"); sp.innerHTML = icon("checkCircle", 18);
            if (t === "soal-pg" && res.data.content) lastSoal = res.data.content.slice(0, 6000);
            if (res.data.quota) {
              state.quota = res.data.quota;
              state.user.quota_used = res.data.quota.used;
            }
          } else {
            failed++;
            row.classList.add("fail"); var sp2 = row.querySelector("span"); sp2.classList.remove("spin"); sp2.innerHTML = icon("xCircle", 18);
            row.title = res.data.error || "gagal";
            if (res.status === 402) { // kuota habis -> hentikan
              msg($("pkMsg"), res.data.error || "Kuota habis.", "error");
              btn.disabled = false;
              refreshQuotaUI();
              return;
            }
          }
          refreshQuotaUI();
          setTimeout(function () { step(i + 1); }, 1500);
        });
      }
      step(0);
    });
  }

  /* ================= events ================= */
  document.addEventListener("DOMContentLoaded", function () {
    // nav
    initModelSelect();
    document.querySelectorAll("#appNav a").forEach(function (a) {
      a.addEventListener("click", function () { setTimeout(route, 0); });
    });
    $("navToggle").addEventListener("click", function () {
      $("appNav").classList.toggle("open");
    });
    window.addEventListener("hashchange", route);

    // auth tabs
    $("tabMasuk").addEventListener("click", function () { setAuthTab("login"); });
    $("tabDaftar").addEventListener("click", function () { setAuthTab("register"); });

    $("loginForm").addEventListener("submit", function (e) {
      e.preventDefault();
      api("POST", "/api/login", {
        email: $("loginEmail").value, password: $("loginPass").value
      }).then(function (res) {
        if (res.status === 200) { state.user = res.data.user; refreshAuthUI(); }
        else msg($("loginMsg"), res.data.error || "Gagal masuk.", "error");
      });
    });

    $("registerForm").addEventListener("submit", function (e) {
      e.preventDefault();
      api("POST", "/api/register", {
        email: $("regEmail").value, password: $("regPass").value,
        nama: $("regNama").value, sekolah: $("regSekolah").value,
        mapel: $("regMapel").value, jenjang: $("regJenjang").value
      }).then(function (res) {
        if (res.status === 200) { state.user = res.data.user; refreshAuthUI(); }
        else msg($("regMsg"), res.data.error || "Gagal daftar.", "error");
      });
    });

    $("logoutBtn").addEventListener("click", function () {
      api("POST", "/api/logout").then(function () {
        state.user = null; state.quota = null; refreshAuthUI();
      });
    });

    $("profileForm").addEventListener("submit", function (e) {
      e.preventDefault();
      api("PUT", "/api/me", {
        nama: $("pfNama").value, sekolah: $("pfSekolah").value,
        mapel: $("pfMapel").value, jenjang: $("pfJenjang").value
      }).then(function (res) {
        if (res.status === 200) {
          state.user = res.data.user; fillProfile();
          msg($("pfMsg"), "Profil tersimpan.", "ok");
        } else msg($("pfMsg"), res.data.error || "Gagal menyimpan.", "error");
      });
    });

    $("refreshDocs").addEventListener("click", loadDocs);
    $("filterFav").addEventListener("change", loadDocs);
    $("filterType").addEventListener("change", loadDocs);

    // isi filter jenis dokumen dari registry generator
    var seen = {};
    Object.keys(GENERATORS).forEach(function (t) {
      if (seen[t]) return; seen[t] = 1;
      var o = document.createElement("option");
      o.value = t; o.textContent = GENERATORS[t].label;
      $("filterType").appendChild(o);
    });

    initChat();
    initPackage();
    loadMe();
  });
})();
