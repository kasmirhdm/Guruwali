/* GuruWali — Manajemen Akun Sekolah */
const GWSchool = {
  data: null,

  async load() {
    if (!window.gwUser) { this.hide(); return; }
    try {
      const r = await fetch('/api/school', {credentials: 'include'});
      const d = await r.json();
      this.data = d.school ? d : null;
      this.render();
      // Setelah data sekolah tersedia, evaluasi ulang panel Dapodik.
      if (window.GWDapodik && window.gwUser) window.GWDapodik.show();
    } catch(e) { /* silent */ }
  },

  hide() {
    const el = document.getElementById('gw-school-section');
    if (el) el.remove();
  },

  render() {
    // Tampilan manajemen sekolah utama berada di menu "Admin Sekolah"
    // (frontend/js/admin.js). Di sini hanya dipertahankan sebagai store data
    // agar signatureParams(), Dapodik, dan komponen lain mendapat data terbaru.
    if (!window.gwUser) { this.hide(); return; }
    return this.data;
  },

  esc(s) { const d = document.createElement('div'); d.textContent = s||''; return d.innerHTML; },

  showCreate() {
    document.getElementById('gw-school-form').innerHTML = `
      <div style="margin-top:12px;padding:12px;background:#fff;border-radius:8px">
        <input id="gw-s-nama" placeholder="Nama Sekolah *" style="width:100%;padding:10px;margin-bottom:8px;border:1px solid #ddd;border-radius:8px">
        <input id="gw-s-npsn" placeholder="NPSN" style="width:100%;padding:10px;margin-bottom:8px;border:1px solid #ddd;border-radius:8px">
        <input id="gw-s-kota" placeholder="Kota/Kabupaten" style="width:100%;padding:10px;margin-bottom:8px;border:1px solid #ddd;border-radius:8px">
        <button onclick="GWSchool.doCreate()" style="padding:10px 16px;border-radius:8px;border:none;background:#2563eb;color:#fff;font-weight:600">Buat</button>
      </div>`;
  },

  async doCreate() {
    const nama = document.getElementById('gw-s-nama').value.trim();
    if (!nama) { alert('Nama sekolah wajib diisi'); return; }
    const r = await fetch('/api/school/create', {method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({nama, npsn: document.getElementById('gw-s-npsn').value.trim(),
        kota: document.getElementById('gw-s-kota').value.trim()})});
    const d = await r.json();
    if (d.school) { this.load(); } else { alert(d.error || 'Gagal'); }
  },

  showJoin() {
    document.getElementById('gw-school-form').innerHTML = `
      <div style="margin-top:12px;padding:12px;background:#fff;border-radius:8px">
        <input id="gw-s-code" placeholder="Kode undangan (8 karakter)" style="width:100%;padding:10px;margin-bottom:8px;border:1px solid #ddd;border-radius:8px;text-transform:uppercase">
        <button onclick="GWSchool.doJoin()" style="padding:10px 16px;border-radius:8px;border:none;background:#16a34a;color:#fff;font-weight:600">Gabung</button>
      </div>`;
  },

  async doJoin() {
    const code = document.getElementById('gw-s-code').value.trim();
    const r = await fetch('/api/school/join', {method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({code})});
    const d = await r.json();
    if (d.school) { alert(d.message); this.load(); } else { alert(d.error || 'Gagal'); }
  },

  async genCode() {
    const r = await fetch('/api/school/invite-code', {method:'POST', credentials:'include'});
    const d = await r.json();
    if (d.invite_code) {
      document.getElementById('gw-invite-code').innerHTML =
        `Kode undangan: <b style="font-size:18px;letter-spacing:2px">${d.invite_code}</b>
         <button onclick="navigator.clipboard.writeText('${d.invite_code}')" style="margin-left:8px;padding:4px 10px;border-radius:6px;border:1px solid #ddd;background:#fff;font-size:12px">Salin</button>
         <br><small style="color:#888">Bagikan kode ini ke guru-guru di sekolahmu</small>`;
    }
  },

  async transfer(uid) {
    if (!confirm('Jadikan guru ini sebagai Admin Sekolah? Anda akan menjadi Guru biasa.')) return;
    const r = await fetch('/api/school/transfer-admin', {method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({user_id: uid})});
    const d = await r.json();
    alert(d.message || d.error || 'Gagal');
    if (d.ok) this.load();
  },

  async remove(uid) {
    if (!confirm('Keluarkan anggota ini?')) return;
    const r = await fetch('/api/school/remove-member', {method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({user_id: uid})});
    const d = await r.json();
    alert(d.message); this.load();
  },

  async leave() {
    if (!confirm('Keluar dari sekolah?')) return;
    await fetch('/api/school/leave', {method:'POST', credentials:'include'});
    this.load();
  }
};

// Section sekolah hanya dibuat setelah pengguna berhasil masuk.
document.addEventListener('DOMContentLoaded', () => GWSchool.load());

// --- Dapodik Import UI ---
var GWDapodik = {
  hide: function() {
    var el = document.getElementById('gw-dapodik-section');
    if (el) el.remove();
  },
  show: function() {
    if (!window.gwUser) { this.hide(); return; }
    // Hanya tampil untuk admin sekolah (operator sekolah)
    var isAdmin = (typeof GWSchool !== 'undefined' && GWSchool.data && GWSchool.data.is_admin);
    if (!isAdmin) { this.hide(); return; }
    var el = document.getElementById('gw-dapodik-section');
    if (!el) {
      el = document.createElement('div');
      el.id = 'gw-dapodik-section';
      el.style.cssText = 'padding:16px;margin:16px 0;border:1px solid #e0e0e0;border-radius:12px;background:#f0fdf4;';
      var main = document.querySelector('main') || document.body;
      main.appendChild(el);
    }
    el.innerHTML =
      '<h3 style="margin:0 0 8px">Import Dapodik</h3>' +
      '<p style="color:#666;font-size:13px">Upload file CSV dari Dapodik untuk auto-isi profil dan data sekolah.</p>' +
      '<input type="file" id="gw-dapodik-file" accept=".csv" style="margin-bottom:8px"><br>' +
      '<button onclick="GWDapodik.doImport()" style="padding:10px 16px;border-radius:8px;border:none;background:#16a34a;color:#fff;font-weight:600">Import</button>' +
      '<div id="gw-dapodik-result" style="margin-top:8px;font-size:14px"></div>' +
      '<p style="font-size:12px;color:#666">Cara: Dapodik - Data GTK - Export Excel - Save As CSV - Upload di sini</p>';
  },
  doImport: function() {
    var f = document.getElementById('gw-dapodik-file').files[0];
    if (!f) { alert('Pilih file CSV dulu'); return; }
    var reader = new FileReader();
    reader.onload = function(e) {
      document.getElementById('gw-dapodik-result').innerHTML = 'Mengimport...';
      fetch('/api/dapodik/import', {method:'POST', credentials:'include',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({csv: e.target.result})})
      .then(function(r){ return r.json(); })
      .then(function(d){
        document.getElementById('gw-dapodik-result').innerHTML =
          d.ok ? 'Berhasil: ' + d.message : 'Gagal: ' + (d.error || 'Unknown');
        if (d.ok && typeof GWSchool !== 'undefined') GWSchool.load();
      });
    };
    reader.readAsText(f);
  }
};
document.addEventListener('DOMContentLoaded', function(){ GWDapodik.show(); });
