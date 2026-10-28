// Komponen kolom pencarian (components/search_field.html)
// - tombol X muncul kalau input ada isinya
// - klik X:
//     halaman AJAX (data-search-live) -> kosongkan input + kirim event "input"
//                                        (JS halaman yang memperbarui hasilnya)
//     halaman biasa                   -> ikuti link X (buka halaman tanpa ?q=)
// Pakai event delegation, jadi tetap jalan untuk elemen yang muncul belakangan.
document.addEventListener("input", (e) => {
  const input = e.target.closest(".search-field__input");
  if (!input) return;
  const clear = input
    .closest(".search-field")
    .querySelector("[data-search-clear]");
  if (clear) clear.hidden = !input.value;
});

document.addEventListener("click", (e) => {
  const clear = e.target.closest(".search-field [data-search-clear]");
  if (!clear) return;

  const field = clear.closest(".search-field");
  if (!field.hasAttribute("data-search-live")) return; // biarkan link jalan normal

  e.preventDefault();
  const input = field.querySelector(".search-field__input");
  input.value = "";
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.focus();
});
