// AJAX untuk modal ubah nama & hapus di halaman Riwayat
document.addEventListener("submit", async (e) => {
  const form = e.target.closest("form[data-ajax]");
  if (!form) return; // form biasa -> biarkan jalan normal

  e.preventDefault();
  const button = form.querySelector('[type="submit"]');
  button.disabled = true;

  try {
    const response = await fetch(form.action, {
      method: "POST",
      body: new FormData(form), // sudah termasuk csrfmiddlewaretoken
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    const data = await response.json();

    if (!response.ok || !data.ok) {
      window.showToast("error", data.message || "Gagal menyimpan.");
      return;
    }

    form.closest("dialog")?.close();
    const row = document.getElementById(form.dataset.target);

    if (form.dataset.ajax === "rename") {
      row.querySelector("[data-name]").textContent = data.land_name;
    } else if (form.dataset.ajax === "delete") {
      row.remove();
      // kalau semua riwayat sudah dihapus, muat ulang biar empty state tampil
      if (!document.querySelector(".history-row")) {
        location.reload();
        return;
      }
      updateCount();
    }

    window.showToast("success", data.message);
  } catch (err) {
    window.showToast("error", "Tidak bisa terhubung ke server. Coba lagi.");
  } finally {
    button.disabled = false;
  }
});

// Perbarui teks jumlah setelah ada riwayat yang dihapus
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
const searchInput = document.querySelector(
  ".history-search .search-field__input",
);

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

      // ganti daftar hasil + teks jumlah dengan versi terbaru
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

  // ketik (atau klik X di komponen search-field) -> cari setelah 300 ms
  searchInput.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(runSearch, 300); // tunggu 300 ms setelah ketikan terakhir
  });

  // tekan Enter -> langsung cari, tanpa reload halaman
  searchInput.form.addEventListener("submit", (e) => {
    e.preventDefault();
    clearTimeout(timer);
    runSearch();
  });
}
