// Navbar Nanem: sidebar mobile + dropdown
// - tombol hamburger buka/tutup sidebar
// - klik latar gelap / tekan Esc -> tutup
// - klik di luar dropdown -> dropdown tertutup
document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector("[data-navbar]");
  if (!nav) return;

  const toggle = nav.querySelector("[data-navbar-toggle]");
  const desktop = window.matchMedia("(min-width: 1101px)");

  const setOpen = (open) => {
    nav.classList.toggle("is-open", open);
    document.body.classList.toggle("nav-open", open); // kunci scroll halaman
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Tutup menu" : "Buka menu");
  };

  const closeDropdowns = (except) => {
    nav.querySelectorAll("details[open]").forEach((d) => {
      if (d !== except) d.removeAttribute("open");
    });
  };

  toggle.addEventListener("click", () =>
    setOpen(!nav.classList.contains("is-open")),
  );

  // klik latar gelap -> tutup sidebar
  nav.querySelectorAll("[data-navbar-close]").forEach((el) => {
    el.addEventListener("click", () => setOpen(false));
  });

  // klik di luar dropdown -> tutup dropdown (cuma di desktop;
  // di sidebar mobile dropdown dibiarkan terbuka sampai diklik lagi)
  document.addEventListener("click", (e) => {
    if (!desktop.matches) return;
    closeDropdowns(e.target.closest("details"));
  });

  // Esc -> tutup semuanya
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeDropdowns();
      setOpen(false);
    }
  });

  // balik ke ukuran desktop -> reset sidebar
  desktop.addEventListener("change", (e) => {
    if (e.matches) setOpen(false);
  });
});
