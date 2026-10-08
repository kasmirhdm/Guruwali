/* Admin GuruWali + Admin Sekolah */
(function(){
  "use strict";
  function $(id){return document.getElementById(id);}
  function api(m,p,b){var o={method:m,headers:{"Content-Type":"application/json"}};if(b)o.body=JSON.stringify(b);return fetch(p,o).then(function(r){return r.json().then(function(j){return{status:r.status,data:j};});});}
  function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
  function showNav(){
    var u=window.gwUser||null;
    // Jika belum ada data user, ambil dari API
    if(!u){
      api("GET","/api/me").then(function(r){
        if(r.data&&r.data.user){window.gwUser=r.data.user;showNav();}
      }).catch(function(){});
      return;
    }
    var pa=$("navPlatformAdmin"),sa=$("navSchoolAdmin");
    var isPA = !!(u&&u.is_platform_admin);
    if(pa)pa.classList.toggle("hidden",!isPA);
    if(sa)sa.classList.toggle("hidden",!u||isPA);
    // Sembunyikan semua menu generate untuk platform admin
    if(isPA){
      var hideSections=["beranda","perangkat","materi","soal","penilaian","media","alat","admin","dokumen","chat","riwayat","profil","upgrade"];
      hideSections.forEach(function(s){
        var el=document.querySelector('#appNav a[data-section="'+s+'"]');
        if(el)el.classList.add("hidden");
      });
      // Redirect ke platform-admin jika di section lain
      var h=(location.hash||"").replace("#","");
      if(h!=="platform-admin"&&h!=="")location.hash="#platform-admin";
    }
  }
  function loadSchool(){
    var box=$("schoolAdminContent");if(!box)return;
    api("GET","/api/school").then(function(r){
      if(r.status!==200||!r.data.school){
        box.innerHTML='<div class="admin-card" style="text-align:center;padding:32px"><h3 style="margin:0 0 8px">🏫 Belum tergabung sekolah</h3><p class="admin-muted" style="margin:0 0 20px">Minta kode undangan dari admin sekolah, lalu masukkan di bawah.</p>'+
        '<div style="max-width:320px;margin:0 auto"><input id="joinCode" placeholder="Kode undangan (8 karakter)" style="width:100%;padding:14px;margin-bottom:12px;border:2px solid #e2e8f0;border-radius:12px;font-size:18px;text-align:center;letter-spacing:3px;text-transform:uppercase;font-weight:700">'+
        '<button id="doJoinBtn" class="btn btn-primary" style="width:100%;padding:14px;font-size:16px">Gabung Sekolah</button>'+
        '<p id="joinMsg" style="font-size:13px;margin-top:8px"></p></div></div>';
        $("doJoinBtn").addEventListener("click",function(){
          var code=$("joinCode").value.trim().toUpperCase();
          if(!code){$("joinMsg").textContent="Masukkan kode undangan dulu.";return;}
          api("POST","/api/school/join",{code:code}).then(function(x){
            if(x.status===200){$("joinMsg").style.color="#16a34a";$("joinMsg").textContent="Berhasil bergabung! Memuat...";setTimeout(loadSchool,1000);}
            else{$("joinMsg").style.color="#ef4444";$("joinMsg").textContent=x.data.error||"Kode tidak valid.";}
          });
        });
        return;}
      var s=r.data.school,m=r.data.members||[],isAdmin=!!r.data.is_admin;
      if(!isAdmin){
        box.innerHTML='<div class="admin-card" style="border-top:4px solid #16a34a"><h3 style="margin:0 0 4px">✅ Anda Tergabung di Sekolah</h3>'+
        '<p class="admin-muted" style="margin:0 0 16px;font-size:13px">Berikut identitas sekolah tempat Anda bergabung:</p>'+
        '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px">'+
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;font-size:14px">'+
        '<div><span style="color:#666;font-size:12px">NAMA SEKOLAH</span><br><strong>'+esc(s.nama)+'</strong></div>'+
        '<div><span style="color:#666;font-size:12px">NPSN</span><br><strong>'+esc(s.npsn||"—")+'</strong></div>'+
        '<div><span style="color:#666;font-size:12px">KOTA/KABUPATEN</span><br><strong>'+esc(s.kota||"—")+'</strong></div>'+
        '<div><span style="color:#666;font-size:12px">ALAMAT</span><br><strong>'+esc(s.alamat||"—")+'</strong></div>'+
        '</div></div>'+
        '<div style="margin-top:16px;padding:12px;background:#eff6ff;border-radius:10px;font-size:14px"><strong>Kuota sekolah:</strong> '+(s.quota_used||0)+' / '+(s.quota_limit||0)+' dokumen '+(s.is_pro?'<span class="admin-badge pro">Pro</span>':'')+'</div>'+
        '<button onclick="if(confirm(\'Keluar dari sekolah ini?\')){fetch(\'/api/school/leave\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'}}).then(()=>location.reload())}" style="margin-top:12px;padding:8px 16px;border-radius:8px;border:1px solid #ef4444;color:#ef4444;background:#fff;cursor:pointer">Keluar dari Sekolah</button></div>';
        return;}
      var inviteCode = esc(s.invite_code||"");
      box.innerHTML='<div class="admin-hero" style="background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:#fff;border-radius:16px;padding:24px;margin-bottom:20px"><h2 style="margin:0 0 4px;color:#fff">🏫 '+esc(s.nama)+'</h2><p style="margin:0 0 16px;opacity:.85;font-size:14px">Admin Sekolah • GuruWali penuh tetap tersedia di menu utama.</p>'+
      '<div style="background:rgba(255,255,255,.15);border-radius:12px;padding:16px"><p style="margin:0 0 8px;font-size:13px;opacity:.9">KODE UNDANGAN GURU</p>'+
      '<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">'+
      '<span id="inviteCodeText" style="font-size:28px;font-weight:800;letter-spacing:4px;background:#fff;color:#1e3a8a;padding:10px 20px;border-radius:10px">'+(inviteCode||"—")+'</span>'+
      (inviteCode?'<button onclick="navigator.clipboard.writeText(\''+inviteCode+'\');this.textContent=\'Disalin!\';setTimeout(()=>this.textContent=\'Salin Kode\',1500)" style="padding:10px 18px;border-radius:10px;border:none;background:#16a34a;color:#fff;font-weight:700;cursor:pointer">Salin Kode</button>':'')+
      '<button class="btn btn-primary" id="regenInvite" style="background:#fff;color:#1e3a8a;border:none">'+(inviteCode?"Perbarui Kode":"Buat Kode")+'</button></div>'+
      '<p style="margin:12px 0 0;font-size:13px;opacity:.85">Bagikan kode ini ke guru-guru agar bisa bergabung ke sekolah.</p></div></div>'+
      '<div class="admin-grid"><div class="admin-card" style="border-top:4px solid #3b82f6"><h3 style="margin:0 0 4px">📋 Profil Sekolah</h3><p class="admin-muted" style="margin:0 0 16px;font-size:13px">Data ini tampil di kop surat dokumen.</p><form id="schoolForm"><div class="admin-form-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'+
      '<label style="display:block;font-size:13px;font-weight:600">Nama sekolah<input id="saNama" value="'+esc(s.nama)+'" required style="width:100%;padding:10px;margin-top:4px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px"></label>'+
      '<label style="display:block;font-size:13px;font-weight:600">NPSN<input id="saNpsn" value="'+esc(s.npsn||"")+'" style="width:100%;padding:10px;margin-top:4px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px"></label>'+
      '<label style="display:block;font-size:13px;font-weight:600">Kota/Kabupaten<input id="saKota" value="'+esc(s.kota||"")+'" style="width:100%;padding:10px;margin-top:4px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px"></label>'+
      '<label style="display:block;font-size:13px;font-weight:600">Telepon<input id="saTelp" value="'+esc(s.telp||"")+'" style="width:100%;padding:10px;margin-top:4px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px"></label>'+
      '<label style="display:block;font-size:13px;font-weight:600">Email<input id="saEmail" value="'+esc(s.email||"")+'" style="width:100%;padding:10px;margin-top:4px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px"></label>'+
      '<label style="display:block;font-size:13px;font-weight:600">Alamat<input id="saAlamat" value="'+esc(s.alamat||"")+'" style="width:100%;padding:10px;margin-top:4px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px"></label></div>'+
      '<p class="form-msg" id="schoolMsg" style="font-size:13px"></p><button class="btn btn-primary" style="margin-top:8px;padding:12px 28px;font-size:15px">💾 Simpan Sekolah</button></form></div>'+
      '<div class="admin-card"><h3>Kuota Sekolah</h3><p><strong>'+s.quota_used+' / '+s.quota_limit+'</strong></p><p class="admin-muted">'+(s.is_pro?"Paket Pro sekolah":"Paket sekolah standar")+'</p><p class="admin-muted">Semua guru anggota dapat menggunakan fasilitas GuruWali sesuai kebijakan kuota sekolah.</p></div></div>'+
      '<div class="admin-card"><h3>Anggota Guru</h3><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Nama</th><th>Email</th><th>Peran</th><th>Aksi</th></tr></thead><tbody>'+
      m.map(function(x){return'<tr><td>'+esc(x.nama||"—")+'</td><td>'+esc(x.email||"")+'</td><td><span class="admin-badge">'+esc(x.role||"guru")+'</span></td><td>'+(x.role==="admin"?"":'<button class="btn btn-ghost btn-small remove-member" data-id="'+x.user_id+'">Keluarkan</button>')+'</td></tr>';}).join("")+
      '</tbody></table></div></div>';
      $("schoolForm").addEventListener("submit",function(e){e.preventDefault();api("POST","/api/school/update",{nama:$("saNama").value,npsn:$("saNpsn").value,kota:$("saKota").value,telp:$("saTelp").value,email:$("saEmail").value,alamat:$("saAlamat").value}).then(function(x){$("schoolMsg").textContent=x.status===200?"Profil sekolah tersimpan.":(x.data.error||"Gagal menyimpan.");});});
      $("regenInvite").addEventListener("click",function(){api("POST","/api/school/invite-code").then(function(x){if(x.status===200)loadSchool();else alert(x.data.error||"Gagal.");});});
      box.querySelectorAll(".remove-member").forEach(function(b){b.addEventListener("click",function(){if(!confirm("Keluarkan guru ini dari sekolah?"))return;api("POST","/api/school/remove-member",{user_id:Number(b.dataset.id)}).then(loadSchool);});});
    });
  }
  function loadPlatform(){
    var d=$("platformAdminContent");if(!d)return;
    Promise.all([api("GET","/api/platform-admin/dashboard"),api("GET","/api/platform-admin/users"),api("GET","/api/platform-admin/schools"),api("GET","/api/platform-admin/audit")]).then(function(rs){
      if(rs[0].status!==200){d.innerHTML='<div class="admin-card"><h3>Akses ditolak</h3><p class="admin-muted">'+esc(rs[0].data.error||"Admin GuruWali hanya untuk platform admin.")+'</p></div>';return;}
      var x=rs[0].data.dashboard,u=rs[1].data.users||[],s=rs[2].data.schools||[],logs=rs[3].data.logs||[];
      d.innerHTML='<div class="admin-hero"><h2>Admin GuruWali</h2><p class="admin-muted">Pusat kendali seluruh platform. Pengaturan sensitif tetap divalidasi di server.</p></div><div class="admin-kpis">'+
      [["Pengguna",x.users],["Sekolah",x.schools],["Pengguna Pro",x.pro_users],["Sekolah Pro",x.pro_schools],["Dokumen",x.documents],["Anggota sekolah",x.members]].map(function(k){return'<div class="admin-kpi"><span>'+k[0]+'</span><strong>'+k[1]+'</strong></div>';}).join("")+'</div>'+
      '<div class="admin-grid"><div class="admin-card"><h3>Pengguna</h3><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Nama</th><th>Email</th><th>Sekolah</th><th>Pro</th><th>Aksi</th></tr></thead><tbody>'+
      u.map(function(a){return'<tr><td>'+esc(a.nama||"—")+'</td><td>'+esc(a.email)+'</td><td>'+esc(a.sekolah||"—")+'</td><td>'+(a.is_pro?'<span class="admin-badge pro">Pro</span>':'—')+'</td><td><button class="btn btn-ghost btn-small toggle-user-pro" data-id="'+a.id+'" data-enabled="'+(a.is_pro?0:1)+'">'+(a.is_pro?"Cabut Pro":"Jadikan Pro")+'</button></td></tr>';}).join("")+
      '</tbody></table></div></div><div class="admin-card"><h3>Sekolah</h3><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Sekolah</th><th>Admin</th><th>Anggota</th><th>Pro</th><th>Aksi</th></tr></thead><tbody>'+
      s.map(function(a){return'<tr><td>'+esc(a.nama)+'</td><td>'+esc(a.admin_nama||"—")+'</td><td>'+a.member_count+'</td><td>'+(a.is_pro?'<span class="admin-badge pro">Pro</span>':'—')+'</td><td><button class="btn btn-ghost btn-small toggle-school-pro" data-id="'+a.id+'" data-enabled="'+(a.is_pro?0:1)+'">'+(a.is_pro?"Cabut Pro":"Jadikan Pro")+'</button></td></tr>';}).join("")+
      '</tbody></table></div></div></div><div class="admin-card"><h3>Aktivitas Admin</h3><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>Waktu</th><th>Admin</th><th>Aksi</th><th>Target</th></tr></thead><tbody>'+
      logs.map(function(l){return'<tr><td>'+new Date(l.created_at*1000).toLocaleString("id-ID")+'</td><td>'+esc(l.actor_name||l.actor_email||"—")+'</td><td>'+esc(l.action)+'</td><td>'+esc(l.target_type||"")+' #'+(l.target_id||"")+'</td></tr>';}).join("")+
      '</tbody></table></div></div>';
      // Master Data CP/TP
      d.innerHTML+='<div class="admin-grid"><div class="admin-card"><h3>📚 Master CP (Capaian Pembelajaran)</h3><div id="masterCpList"><p class="admin-muted">Memuat...</p></div><h4 style="margin:16px 0 8px">Tambah CP</h4><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><input id="cpJenjang" placeholder="Jenjang (SD/SMP/SMA)" style="padding:8px;border:1px solid #ddd;border-radius:8px"><input id="cpFase" placeholder="Fase (A/B/C/D/E/F)" style="padding:8px;border:1px solid #ddd;border-radius:8px"><input id="cpMapel" placeholder="Mata Pelajaran" style="padding:8px;border:1px solid #ddd;border-radius:8px"><input id="cpKode" placeholder="Kode (opsional)" style="padding:8px;border:1px solid #ddd;border-radius:8px"></div><textarea id="cpDeskripsi" placeholder="Deskripsi CP..." style="width:100%;padding:8px;margin-top:8px;border:1px solid #ddd;border-radius:8px;min-height:60px"></textarea><button class="btn btn-primary" id="addCpBtn" style="margin-top:8px">+ Tambah CP</button></div><div class="admin-card"><h3>🎯 Master TP (Tujuan Pembelajaran)</h3><div id="masterTpList"><p class="admin-muted">Memuat...</p></div><h4 style="margin:16px 0 8px">Tambah TP</h4><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><input id="tpJenjang" placeholder="Jenjang" style="padding:8px;border:1px solid #ddd;border-radius:8px"><input id="tpFase" placeholder="Fase" style="padding:8px;border:1px solid #ddd;border-radius:8px"><input id="tpMapel" placeholder="Mapel" style="padding:8px;border:1px solid #ddd;border-radius:8px"><input id="tpKelas" placeholder="Kelas" style="padding:8px;border:1px solid #ddd;border-radius:8px"></div><textarea id="tpDeskripsi" placeholder="Deskripsi TP..." style="width:100%;padding:8px;margin-top:8px;border:1px solid #ddd;border-radius:8px;min-height:60px"></textarea><button class="btn btn-primary" id="addTpBtn" style="margin-top:8px">+ Tambah TP</button></div></div>';
      loadMasterCp(); loadMasterTp();
      $("addCpBtn").onclick=function(){var b={jenjang:$("cpJenjang").value,fase:$("cpFase").value,mapel:$("cpMapel").value,kode:$("cpKode").value,deskripsi:$("cpDeskripsi").value};if(!b.jenjang||!b.mapel||!b.deskripsi){alert("Lengkapi jenjang, mapel, dan deskripsi!");return;}api("POST","/api/platform-admin/master-cp/add",b).then(function(){loadMasterCp();$("cpJenjang").value="";$("cpFase").value="";$("cpMapel").value="";$("cpKode").value="";$("cpDeskripsi").value="";});};
      $("addTpBtn").onclick=function(){var b={jenjang:$("tpJenjang").value,fase:$("tpFase").value,mapel:$("tpMapel").value,kelas:$("tpKelas").value,deskripsi:$("tpDeskripsi").value};if(!b.jenjang||!b.mapel||!b.deskripsi){alert("Lengkapi jenjang, mapel, dan deskripsi!");return;}api("POST","/api/platform-admin/master-tp/add",b).then(function(){loadMasterTp();$("tpJenjang").value="";$("tpFase").value="";$("tpMapel").value="";$("tpKelas").value="";$("tpDeskripsi").value="";});};
      d.querySelectorAll(".toggle-user-pro").forEach(function(b){b.onclick=function(){api("POST","/api/platform-admin/user-pro",{user_id:Number(b.dataset.id),enabled:b.dataset.enabled==="1"}).then(loadPlatform);};});
      d.querySelectorAll(".toggle-school-pro").forEach(function(b){b.onclick=function(){api("POST","/api/platform-admin/school-pro",{school_id:Number(b.dataset.id),enabled:b.dataset.enabled==="1"}).then(loadPlatform);};});
    });
  }
  function loadMasterCp(){
    api("GET","/api/platform-admin/master-cp").then(function(r){
      var box=$("masterCpList");if(!box)return;
      var d=(r.data&&r.data.data)||[];
      if(!d.length){box.innerHTML='<p class="admin-muted">Belum ada data CP.</p>';return;}
      box.innerHTML='<div style="max-height:300px;overflow-y:auto">'+d.map(function(x){return'<div style="padding:8px;border-bottom:1px solid #eee;font-size:13px"><strong>'+esc(x.jenjang)+' - '+esc(x.fase)+' - '+esc(x.mapel)+'</strong>'+(x.kode?' <span class="admin-badge">'+esc(x.kode)+'</span>':'')+'<br><span style="color:#666">'+esc(x.deskripsi)+'</span><br><button class="btn btn-ghost btn-small" onclick="delCp('+x.id+')" style="margin-top:4px;color:#ef4444">Hapus</button></div>';}).join("")+'</div>';
    });
  }
  window.delCp=function(id){if(!confirm("Hapus CP ini?"))return;api("POST","/api/platform-admin/master-cp/delete",{id:id}).then(loadMasterCp);};
  function loadMasterTp(){
    api("GET","/api/platform-admin/master-tp").then(function(r){
      var box=$("masterTpList");if(!box)return;
      var d=(r.data&&r.data.data)||[];
      if(!d.length){box.innerHTML='<p class="admin-muted">Belum ada data TP.</p>';return;}
      box.innerHTML='<div style="max-height:300px;overflow-y:auto">'+d.map(function(x){return'<div style="padding:8px;border-bottom:1px solid #eee;font-size:13px"><strong>'+esc(x.jenjang)+' - '+esc(x.fase)+' - '+esc(x.mapel)+(x.kelas?' ('+esc(x.kelas)+')':'')+'</strong><br><span style="color:#666">'+esc(x.deskripsi)+'</span><br><button class="btn btn-ghost btn-small" onclick="delTp('+x.id+')" style="margin-top:4px;color:#ef4444">Hapus</button></div>';}).join("")+'</div>';
    });
  }
  window.delTp=function(id){if(!confirm("Hapus TP ini?"))return;api("POST","/api/platform-admin/master-tp/delete",{id:id}).then(loadMasterTp);};
  function init(){
    var p=$("navPlatformAdmin"),s=$("navSchoolAdmin");
    if(p)p.addEventListener("click",function(){setTimeout(loadPlatform,0);});
    if(s)s.addEventListener("click",function(){setTimeout(loadSchool,0);});
    window.gwAdmin={refresh:function(){showNav();loadSchool();loadPlatform();}};
    showNav();
  }
  document.addEventListener("DOMContentLoaded",init);
})();