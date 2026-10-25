// Form rekomendasi
// 1. Loading: saat form dikirim, tampilkan modal loading sampai halaman berikutnya terbuka
// 2. GPS: isi latitude & longitude dari lokasi browser
//    - tombol "Pakai lokasi saya sekarang" cuma muncul kalau browser mendukung geolocation
//    - browser akan minta izin lokasi ke user
//    - hasilnya mengisi input latitude & longitude (user masih bisa ubah manual)

// ---------- 1. Modal loading saat submit ----------
// Form tetap dikirim biasa oleh browser (bukan fetch). Selama server mengambil
// data Open-Meteo, halaman ini masih tampil, jadi modal loading kelihatan.
// - valid   -> server redirect ke halaman hasil, modal ikut hilang
// - invalid -> server render ulang form + pesan error, modal ikut hilang
// Jadi views.py tidak perlu diubah.
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-recommend-form]");
  if (!form) return;

  const loading = document.getElementById(form.dataset.loading);
  const submitBtn = form.querySelector('button[type="submit"]');

  form.addEventListener("submit", () => {
    submitBtn.disabled = true; // cegah klik dobel
    if (loading && typeof loading.showModal === "function" && !loading.open) {
      loading.showModal();
    }
  });

  // User tekan "Back" dari halaman hasil: browser bisa memulihkan halaman ini
  // persis seperti terakhir (modal masih terbuka). Kembalikan ke keadaan normal.
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    submitBtn.disabled = false;
    if (loading && loading.open) loading.close();
  });
});

// ---------- 2. GPS ----------
document.addEventListener("DOMContentLoaded", () => {
  const box = document.querySelector("[data-location]");
  const LABEL = "Pakai lokasi saya sekarang";
  if (!box) return;

  const button = box.querySelector("[data-location-gps]");
  const label = box.querySelector("[data-location-label]");
  const status = box.querySelector("[data-location-status]");
  const hint = box.querySelector("[data-location-hint]");
  const latInput = box.querySelector('input[name="latitude"]');
  const lngInput = box.querySelector('input[name="longitude"]');

  // browser lama / koneksi tidak aman (http selain localhost): tombol tetap tersembunyi
  if (!("geolocation" in navigator) || !window.isSecureContext) {
    if (hint) hint.textContent = "Isi koordinat lahanmu:";
    return;
  }
  button.hidden = false;

  const setStatus = (text, type) => {
    status.textContent = text;
    status.dataset.type = type;
    status.hidden = !text;
  };

  const setLoading = (loading) => {
    button.disabled = loading;
    button.classList.toggle("is-loading", loading);
    label.textContent = loading ? "Mencari lokasi…" : LABEL;
  };

  const ERRORS = {
    1: "Izin lokasi ditolak. Aktifkan izin lokasi di pengaturan browser, atau isi koordinat manual.",
    2: "Lokasi tidak bisa ditemukan. Pastikan GPS/lokasi perangkat menyala.",
    3: "Terlalu lama mencari lokasi. Coba lagi.",
  };

  button.addEventListener("click", () => {
    setLoading(true);
    setStatus("", "");

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;

        // 6 angka di belakang koma ≈ ketelitian 10 cm, sudah lebih dari cukup
        latInput.value = latitude.toFixed(6);
        lngInput.value = longitude.toFixed(6);

        // kabari Django/JS lain bahwa nilainya berubah
        latInput.dispatchEvent(new Event("input", { bubbles: true }));
        lngInput.dispatchEvent(new Event("input", { bubbles: true }));

        setLoading(false);
        setStatus(
          `Lokasi terisi (akurasi ± ${Math.round(accuracy)} m).`,
          "success",
        );
      },
      (error) => {
        setLoading(false);
        setStatus(ERRORS[error.code] || "Gagal mengambil lokasi.", "error");
      },
      {
        enableHighAccuracy: true, // pakai GPS kalau ada
        timeout: 10000, // maksimal 10 detik
        maximumAge: 60000, // boleh pakai lokasi dari 1 menit terakhir
      },
    );
  });
});
