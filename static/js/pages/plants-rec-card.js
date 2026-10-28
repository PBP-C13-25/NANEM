// Kartu "Rekomendasi tanaman": tampilkan 5 dulu, sisanya lewat tombol "Lihat lainnya".
// Dipakai di halaman hasil & detail riwayat.
// plus filter kategori (chip) kalau hasilnya punya lebih dari 1
// Tanpa JS semua tanaman tetap tampil (tidak ada yang hilang).
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-plants]").forEach((list) => {
    const visible = Number(list.dataset.visible) || 5;
    const items = Array.from(list.children);
    const button = list.parentElement.querySelector("[data-plants-more]");
    const filterBox = list.parentElement.querySelector("[data-plants-filter]");

    let activeCategory = "all";
    let expanded = false;

    const matchingItems = () =>
      items.filter(
        (item) =>
          activeCategory === "all" || item.dataset.category === activeCategory,
      );

    const render = () => {
      const matching = matchingItems();
      const extra = matching.slice(visible);

      items.forEach((item) => {
        const inCategory =
          activeCategory === "all" || item.dataset.category === activeCategory;
        const position = matching.indexOf(item);
        item.hidden = !inCategory || (position >= visible && !expanded);
      });

      if (!button) return;
      if (extra.length === 0) {
        button.hidden = true;
        return;
      }
      button.hidden = false;
      button.classList.toggle("is-expanded", expanded);
      button.setAttribute("aria-expanded", String(expanded));
      const label = button.querySelector("[data-plants-more-label]");
      label.textContent = expanded
        ? "Tampilkan lebih sedikit"
        : `Lihat ${extra.length} lainnya`;
    };

    // ---- Filter kategori (cuma muncul kalau >1 kategori beda di hasil) ----
    if (filterBox) {
      const categories = [
        ...new Set(items.map((item) => item.dataset.category).filter(Boolean)),
      ];

      if (categories.length > 0) {
        filterBox.hidden = false;

        const makeChip = (value, text) => {
          const chip = document.createElement("button");
          chip.type = "button";
          chip.className =
            "plants-filter__chip" + (value === "all" ? " is-active" : "");
          chip.textContent = text;
          chip.dataset.filterValue = value;
          chip.setAttribute("aria-pressed", String(value === "all"));
          chip.addEventListener("click", () => {
            activeCategory = value;
            expanded = false;
            filterBox.querySelectorAll(".plants-filter__chip").forEach((c) => {
              const isActive = c.dataset.filterValue === value;
              c.classList.toggle("is-active", isActive);
              c.setAttribute("aria-pressed", String(isActive));
            });
            render();
          });
          return chip;
        };

        filterBox.appendChild(makeChip("all", "Semua"));
        categories.forEach((category) => {
          const label = category.charAt(0).toUpperCase() + category.slice(1);
          filterBox.appendChild(makeChip(category, label));
        });
      }
    }

    // ---- Tombol "Lihat lainnya" ----
    if (button) {
      button.addEventListener("click", () => {
        expanded = !expanded;
        render();
        if (expanded) {
          const firstExtra = matchingItems()[visible];
          if (firstExtra)
            firstExtra.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      });
    }

    render();
  });
});
