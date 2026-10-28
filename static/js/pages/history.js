// AJAX untuk modal ubah nama & hapus di halaman Riwayat
// Optimistic UI: DOM diubah LANGSUNG begitu user submit, request jalan di
// background. Kalau server balikin gagal/error, baru di-rollback ke keadaan
// semula + toast error. Ini bikin UI kerasa instan.
document.addEventListener("submit", async (e) => {
  const form = e.target.closest("form[data-ajax]");
  if (!form) return; // form biasa -> biarkan jalan normal

  e.preventDefault();
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;

  const row = document.getElementById(form.dataset.target);
  const dialog = form.closest("dialog");
  let rollback = () => {};

  if (form.dataset.ajax === "rename") {
    const nameEl = row.querySelector("[data-name]");
    const oldName = nameEl.textContent;
    const newName = new FormData(form).get("land_name");
    nameEl.textContent = newName;
    rollback = () => {
      nameEl.textContent = oldName;
    };
  } else if (form.dataset.ajax === "delete") {
    const nextSibling = row.nextSibling;
    const parent = row.parentElement;
    row.remove();
    rollback = () => {
      parent.insertBefore(row, nextSibling);
    };
  }

  dialog?.close();

  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form), // sudah termasuk csrfmiddlewaretoken
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      rollback();
      window.showToast("error", data.message || "Gagal menyimpan.");
      return;
    }

    if (form.dataset.ajax === "delete") {
      // kalau semua riwayat sudah dihapus, muat ulang biar empty state tampil
      if (!document.querySelector(".history-row")) {
        location.reload();
        return;
      }
      updateCount();
    }

    window.showToast("success", data.message);
  } catch (err) {
    rollback();
    window.showToast("error", "Tidak bisa terhubung ke server. Coba lagi.");
  } finally {
    button.disabled = false;
  }
});

// Perbarui jumlah teks klo ada riwayat yg dihapus
function updateCount() {
  const count = document.getElementById("history-count");
  if (!count) return;
  const total = document.querySelectorAll(".history-row").length;
  const q = new URL(window.location.href).searchParams.get("q");
  count.textContent = q
    ? `${total} lahan cocok dengan "${q}"`
    : `${total} lahan tersimpan`;
}

// ===== Pencarian dengan debounce =====
const searchInput = document.querySelector('.history-search input[name="q"]');

if (searchInput) {
  let timer;
  let controller;

  const runSearch = async () => {
    const url = new URL(window.location.href);
    const q = searchInput.value.trim();
    if (q) url.searchParams.set("q", q);
    else url.searchParams.delete("q");

    controller?.abort(); // batalkan pencarian sebelumnya yang belum selesai
    controller = new AbortController();

    try {
      const response = await fetch(url, { signal: controller.signal });
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, "text/html");

      // ganti daftar hasil + teks jumlah
      ["history-results", "history-count"].forEach((id) => {
        const current = document.getElementById(id);
        const fresh = doc.getElementById(id);
        if (current && fresh) current.replaceWith(fresh);
      });

      history.replaceState(null, "", url); // URL ikut berubah, bisa di-refresh/dibagikan
    } catch (err) {
      if (err.name !== "AbortError") {
        window.showToast("error", "Pencarian gagal. Coba lagi.");
      }
    }
  };

  // tombol X buat hapus pencarian
  const clearBtn = searchInput.form.querySelector("[data-search-clear]");
  const toggleClear = () => {
    if (clearBtn) clearBtn.hidden = !searchInput.value;
  };

  searchInput.addEventListener("input", () => {
    toggleClear();
    clearTimeout(timer);
    timer = setTimeout(runSearch, 300); // tunggu 300 ms setelah ketikan terakhir
  });

  // klik X for kosongin kolom & tampilkan semua riwayat (tanpa reload)
  clearBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    searchInput.value = "";
    toggleClear();
    clearTimeout(timer);
    runSearch();
    searchInput.focus();
  });

  // tekan Enter -> langsung cari, tanpa reload halaman
  searchInput.form.addEventListener("submit", (e) => {
    e.preventDefault();
    clearTimeout(timer);
    runSearch();
  });
}
