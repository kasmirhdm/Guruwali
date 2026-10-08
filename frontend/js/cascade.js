/* GuruWali — cascading dropdown untuk form generator (minim ketik).
   Dimuat setelah master-data.js, sebelum app.js. Mengekspos global GWCascade.
   enhance(form): ubah field jenjang/kelas/mapel/materi/cp/alokasi/durasi/tanggal
   berbasis nama field, lalu pasang cascading antar-field. */
var GWCascade = (function () {
  "use strict";

  var M = (typeof GWMaster !== "undefined") ? GWMaster : null;
  var dlCounter = 0;

  function field(form, name) {
    return form.querySelector('[name="' + name + '"]');
  }

  function mkOption(text, value) {
    var o = document.createElement("option");
    o.textContent = text;
    o.value = (value === undefined) ? text : value;
    return o;
  }

  function fillSelect(sel, options, placeholder) {
    while (sel.firstChild) sel.removeChild(sel.firstChild);
    if (placeholder) sel.appendChild(mkOption(placeholder, ""));
    options.forEach(function (o) { sel.appendChild(mkOption(o)); });
    if (!placeholder && options.length) sel.value = options[0];
  }

  /* Ganti <input> menjadi <select> dengan nama/atribut yang sama */
  function toSelect(input, options, placeholder) {
    var sel = document.createElement("select");
    sel.setAttribute("name", input.getAttribute("name") || "");
    if (input.id) sel.id = input.id;
    if (input.required) sel.required = true;
    if (input.className) sel.className = input.className;
    if (placeholder) sel.setAttribute("data-ph", placeholder);
    fillSelect(sel, options, placeholder);
    input.parentNode.replaceChild(sel, input);
    return sel;
  }

  function phOf(sel) {
    return (sel && sel.getAttribute("data-ph")) || null;
  }

  function currentJenjang(form) {
    var j = field(form, "jenjang");
    return (j && j.value) || "SD";
  }

  function updateKelas(form) {
    var k = field(form, "kelas");
    if (!k || k.tagName !== "SELECT") return;
    var list = M.KELAS[currentJenjang(form)] || [];
    var prev = k.value;
    fillSelect(k, list, phOf(k));
    if (list.indexOf(prev) >= 0) k.value = prev;
    updateFase(form);
  }

  function updateMapel(form) {
    var m = field(form, "mapel");
    if (!m || m.tagName !== "SELECT") return;
    var kelas = field(form, "kelas");
    var list = M.mapelList ? M.mapelList(currentJenjang(form), kelas ? kelas.value : "") : (M.MAPEL[currentJenjang(form)] || []);
    var prev = m.value;
    fillSelect(m, list, phOf(m));
    if (list.indexOf(prev) >= 0) m.value = prev;
    updateMateri(form);
    updateCpPicker(form);
  }

  function updateAlokasi(form) {
    var al = field(form, "alokasi");
    if (!al || al.tagName !== "SELECT") return;
    var j = currentJenjang(form);
    var list = (M.ALOKASI && M.ALOKASI[j]) || [];
    /* fallback: jika ALOKASI masih array lama */
    if (!list.length && Array.isArray(M.ALOKASI)) list = M.ALOKASI;
    var prev = al.value;
    fillSelect(al, list, phOf(al));
    if (list.indexOf(prev) >= 0) al.value = prev;
  }

  function updateFase(form) {
    var k = field(form, "kelas");
    var fase = k ? M.faseOf(k.value) : "";
    form.querySelectorAll(".gw-fase-badge").forEach(function (b) {
      b.textContent = fase || "–";
    });
    var fs = field(form, "fase");
    if (fs && fs.tagName === "SELECT" && fase) fs.value = fase;
    updateCpPicker(form);
  }

  function updateMateri(form) {
    var sel = form.querySelector(".gw-materi-sel");
    var custom = form.querySelector(".gw-materi-custom");
    var m = field(form, "mapel");
    var s = field(form, "semester");
    var j = field(form, "jenjang");
    var k = field(form, "kelas");
    if (!sel) return;
    var mapel = m ? m.value : "";
    var jenjang = j ? j.value : "";
    var kelas = k ? k.value : "";
    var sem = "";
    if (s) {
      var sv = s.value || "";
      if (/^1/.test(sv)) sem = "1";
      else if (/^2/.test(sv)) sem = "2";
      else if (/ganjil/i.test(sv)) sem = "1";
      else if (/genap/i.test(sv)) sem = "2";
    }
    var cur = sel.value;
    while (sel.firstChild) sel.removeChild(sel.firstChild);
    var ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "— Pilih materi —";
    sel.appendChild(ph);
    var coverage = M.coverage ? M.coverage(mapel, jenjang, kelas, sem) : { exact: false, materi: false, cp: false };
    var rows = M.materiList(mapel, jenjang, kelas, sem);
    rows.forEach(function (pair) {
      var o = document.createElement("option");
      o.value = pair[0];
      o.textContent = pair[0];
      sel.appendChild(o);
    });
    if (!rows.length) {
      var empty = document.createElement("option");
      empty.value = "";
      empty.textContent = coverage.exact ? "— Belum ada materi terstruktur —" : "— Data materi belum tersedia untuk kombinasi ini —";
      empty.disabled = true;
      sel.appendChild(empty);
    }
    var c = document.createElement("option");
    c.value = "__custom__";
    c.textContent = "✎ Ketik manual...";
    sel.appendChild(c);
    // pertahankan pilihan sebelumnya jika masih ada
    var vals = Array.prototype.map.call(sel.options, function (o) { return o.value; });
    if (cur && vals.indexOf(cur) !== -1) {
      sel.value = cur;
    } else if (custom && custom.value && cur === "__custom__") {
      sel.value = "__custom__";
    }
    wireMateriSel(form);
  }

  function wireMateriSel(form) {
    var sel = form.querySelector(".gw-materi-sel");
    var custom = form.querySelector(".gw-materi-custom");
    if (!sel || !custom || sel.getAttribute("data-wired")) return;
    sel.setAttribute("data-wired", "1");
    sel.addEventListener("change", function () {
      if (sel.value === "__custom__") {
        custom.classList.remove("hidden");
        custom.value = "";
        custom.focus();
      } else {
        custom.classList.add("hidden");
        custom.value = sel.value;
      }
      // sinkronkan CP dengan materi yang dipilih
      syncCpWithMateri(form);
    });
    if (custom) custom.addEventListener("input", function () {
      if (sel.value === "__custom__") syncCpWithMateri(form);
    });
  }

  // Isi dropdown CP umum dengan CP yang sesuai materi terpilih (jika ada di data riset)
  function syncCpWithMateri(form) {
    var sel = form.querySelector(".gw-materi-sel");
    var custom = form.querySelector(".gw-materi-custom");
    if (!sel) return;
    var materi = sel.value === "__custom__" ? (custom ? custom.value : "") : sel.value;
    if (!materi) return;
    var m = field(form, "mapel"), s = field(form, "semester"),
        j = field(form, "jenjang"), k = field(form, "kelas");
    var cp = M.cpForMateri(m ? m.value : "", j ? j.value : "", k ? k.value : "",
      (function () { var sv = s ? s.value || "" : "";
        if (/^1/.test(sv)) return "1"; if (/^2/.test(sv)) return "2";
        if (/ganjil/i.test(sv)) return "1"; if (/genap/i.test(sv)) return "2"; return ""; })(),
      materi);
    if (!cp) return;
    // masukkan ke dropdown CP picker sebagai opsi teratas + isi textarea jika kosong
    var pick = form.querySelector(".gw-cp-pick");
    if (pick && pick.tagName === "SELECT") {
      var exists = Array.prototype.some.call(pick.options, function (o) { return o.value === cp; });
      if (!exists) {
        var o = document.createElement("option");
        o.value = cp;
        o.textContent = "★ " + (cp.length > 80 ? cp.substring(0, 80) + "…" : cp);
        pick.insertBefore(o, pick.firstChild.nextSibling);
      }
      pick.value = cp;
    }
    var ta = field(form, "cp");
    if (ta && ta.tagName === "TEXTAREA" && !ta.value.trim()) ta.value = cp;
  }

  function updateCpPicker(form) {
    var pick = form.querySelector(".gw-cp-pick");
    if (!pick) return;
    var m = field(form, "mapel");
    var k = field(form, "kelas");
    var list = M.cpList(m ? m.value : "", k ? M.faseOf(k.value) : "");
    while (pick.firstChild) pick.removeChild(pick.firstChild);
    pick.appendChild(mkOption("— Pilih CP umum (opsional) —", ""));
    if (!list.length) {
      var cov = M.coverage ? M.coverage(m ? m.value : "", "", k ? k.value : "", "") : null;
      pick.appendChild(mkOption("CP belum tersedia — isi/tempel CP secara manual", ""));
      pick.options[pick.options.length - 1].disabled = true;
      return;
    }
    list.forEach(function (cp, i) {
      pick.appendChild(mkOption("CP " + (i + 1) + ": " + cp.slice(0, 80) + "…", cp));
    });
  }

  function enhanceCp(form) {
    var ta = field(form, "cp");
    if (!ta || ta.tagName !== "TEXTAREA") return;
    if (form.querySelector(".gw-cp-helper")) return;
    var wrap = document.createElement("div");
    wrap.className = "gw-cp-helper";
    var badge = document.createElement("span");
    badge.className = "gw-fase-badge";
    badge.textContent = "–";
    var pick = document.createElement("select");
    pick.className = "gw-cp-pick";
    pick.setAttribute("aria-label", "Pilih CP umum");
    var lab = document.createElement("span");
    lab.className = "gw-cp-lab";
    lab.textContent = "Fase: ";
    lab.appendChild(badge);
    wrap.appendChild(lab);
    wrap.appendChild(pick);
    ta.parentNode.insertBefore(wrap, ta);
    pick.addEventListener("change", function () {
      if (pick.value) ta.value = pick.value;
    });
    updateCpPicker(form);
    updateFase(form);
  }


  /* --- Master Kurikulum platform: guru memilih TP dengan checkbox --- */
  function enhanceMasterTP(form) {
    if (form.querySelector(".gw-tp-master")) return;
    var j=field(form,"jenjang"), s=field(form,"semester"), m=field(form,"mapel"), mt=field(form,"materi");
    if(!j || !s || !m || !mt) return;
    var wrap=document.createElement("div");
    wrap.className="gw-tp-master";
    wrap.style.cssText="margin:10px 0;padding:12px;border:1px solid #dbeafe;border-radius:12px;background:#f8fbff;";
    wrap.innerHTML='<div style="font-weight:700;margin-bottom:6px">🎯 Tujuan Pembelajaran</div><div class="gw-tp-hint" style="font-size:12px;color:#64748b;margin-bottom:8px">Pilih TP yang ingin digunakan.</div><div class="gw-tp-list"><span style="font-size:12px;color:#64748b">Pilih materi terlebih dahulu.</span></div>';
    var hidden=document.createElement("textarea");
    hidden.name="tp";
    hidden.className="gw-tp-selected";
    hidden.style.display="none";
    wrap.appendChild(hidden);
    mt.parentNode.parentNode.insertBefore(wrap, mt.parentNode.nextSibling);

    function load(){
      var params=new URLSearchParams({jenjang:j.value||"",semester:s.value||"",mapel:m.value||"",materi:mt.value||""});
      var list=wrap.querySelector(".gw-tp-list");
      if(!j.value||!s.value||!m.value||!mt.value||mt.value==="__custom__"){
        list.innerHTML='<span style="font-size:12px;color:#64748b">Pilih materi yang tersedia di Master Kurikulum.</span>'; hidden.value=""; return;
      }
      list.innerHTML='<span style="font-size:12px;color:#64748b">Memuat TP...</span>';
      fetch("/api/master-curriculum?"+params.toString()).then(function(r){return r.json();}).then(function(r){
        var rows=r.data||[], tps=[];
        rows.forEach(function(row){(row.tp||[]).forEach(function(tp){tps.push({materi:row.materi,cp:row.cp.deskripsi,kode:tp.kode,deskripsi:tp.deskripsi});});});
        if(!tps.length){list.innerHTML='<span style="font-size:12px;color:#64748b">Belum ada TP untuk kombinasi ini.</span>';hidden.value="";return;}
        list.innerHTML=tps.map(function(tp,i){
          var text=(tp.kode?tp.kode+": ":"")+tp.deskripsi;
          return '<label style="display:flex;gap:8px;align-items:flex-start;padding:8px 4px;border-bottom:1px solid #e5e7eb;cursor:pointer"><input type="checkbox" class="gw-tp-check" value="'+esc(text)+'" style="margin-top:3px"><span>'+esc(text)+'</span></label>';
        }).join("");
        list.querySelectorAll(".gw-tp-check").forEach(function(cb){cb.addEventListener("change",sync);});
      }).catch(function(){list.innerHTML='<span style="font-size:12px;color:#dc2626">Gagal memuat Master Kurikulum.</span>';});
    }
    function sync(){hidden.value=Array.prototype.map.call(wrap.querySelectorAll(".gw-tp-check:checked"),function(x){return x.value;}).join("\n");}
    [j,s,m].forEach(function(el){el.addEventListener("change",load);});
    mt.addEventListener("change",load);
    mt.addEventListener("input",load);
    load();
  }

  function enhance(form) {
    if (!M || !form || form.getAttribute("data-cascade")) return;
    form.setAttribute("data-cascade", "1");

    /* --- jenjang: pastikan select --- */
    var j = field(form, "jenjang");
    if (j && j.tagName !== "SELECT") j = toSelect(j, M.JENJANG, null);
    if (j && !j.value) j.value = M.JENJANG[0];

    /* --- kelas: jadi select cascading --- */
    var k = field(form, "kelas");
    if (k && k.tagName !== "SELECT") k = toSelect(k, [], k.required ? null : "— Pilih —");

    /* --- mapel: jadi select cascading --- */
    var m = field(form, "mapel");
    if (m && m.tagName !== "SELECT") m = toSelect(m, [], m.required ? null : "— Pilih —");

    /* --- semester: opsi baku --- */
    var s = field(form, "semester");
    if (s && s.tagName === "SELECT") {
      var prevS = s.value;
      fillSelect(s, M.SEMESTER, s.required ? null : "— Pilih —");
      if (M.SEMESTER.indexOf(prevS) >= 0) s.value = prevS;
    }

    /* --- materi: datalist saran --- */
    var mt = field(form, "materi");
    if (mt && mt.tagName === "INPUT") {
      dlCounter++;
      var dl = document.createElement("datalist");
      var dlId = "gw-materi-dl-" + dlCounter;
      dl.id = dlId;
      form.appendChild(dl);
      mt.setAttribute("list", dlId);
      mt.setAttribute("placeholder", "Pilih saran atau ketik bebas…");
    }

    /* --- alokasi waktu: dropdown (opsi mengikuti jenjang, diisi updateAlokasi) --- */
    var al = field(form, "alokasi");
    if (al && al.tagName === "INPUT") {
      toSelect(al, [], al.required ? null : "— Pilih —");
    }

    /* --- durasi: dropdown --- */
    var du = field(form, "durasi");
    if (du && du.tagName === "INPUT") {
      toSelect(du, M.DURASI, du.required ? null : "— Pilih —");
    }

    /* --- tanggal: date picker --- */
    var tg = field(form, "tanggal");
    if (tg && tg.tagName === "INPUT") tg.setAttribute("type", "date");

    /* --- wiring --- */
    if (j) j.addEventListener("change", function () { updateKelas(form); updateMapel(form); updateAlokasi(form); });
    if (k && k.tagName === "SELECT") k.addEventListener("change", function () { updateFase(form); updateMateri(form); });
    if (m && m.tagName === "SELECT") m.addEventListener("change", function () { updateMateri(form); updateCpPicker(form); });
    var sm = field(form, "semester");
    if (sm) sm.addEventListener("change", function () { updateMateri(form); });

    /* --- isi awal --- */
    updateKelas(form);
    updateMapel(form);
    updateAlokasi(form);
    enhanceCp(form);
    enhanceMasterTP(form);
  }

  return { enhance: enhance };
})();
