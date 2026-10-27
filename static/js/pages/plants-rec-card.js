// Kartu "Rekomendasi tanaman": tampilkan 5 dulu, sisanya lewat tombol "Lihat lainnya".
// Dipakai di halaman hasil & detail riwayat.
// Tanpa JS semua tanaman tetap tampil (tidak ada yang hilang).
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-plants]").forEach((list) => {
    const visible = Number(list.dataset.visible) || 5;
    const items = Array.from(list.children);
    const extra = items.slice(visible);
    const button = list.parentElement.querySelector("[data-plants-more]");
    if (!button || extra.length === 0) return; // 5 atau kurang: tidak perlu tombol

    const label = button.querySelector("[data-plants-more-label]");
    let expanded = false;

    const render = () => {
      extra.forEach((item) => (item.hidden = !expanded));
      button.classList.toggle("is-expanded", expanded);
      button.setAttribute("aria-expanded", String(expanded));
      label.textContent = expanded
        ? "Tampilkan lebih sedikit"
        : `Lihat ${extra.length} lainnya`;
    };

    button.hidden = false;
    render();

    button.addEventListener("click", () => {
      expanded = !expanded;
      render();
      // saat dibuka, arahkan ke tanaman pertama yang baru muncul
      if (expanded)
        extra[0].scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
});
