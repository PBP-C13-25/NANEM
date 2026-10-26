// Toast Nanem — tutup otomatis & tombol X untuk components/toaster.html
// - toast dari Django (components/toaster.html) & dari JS (window.showToast)
// - hilang sendiri, garis waktu di bawah ikut memendek
// - berhenti sementara saat kursor di atas toast
(() => {
  const ICONS = {
    success: '<path d="M20 6 9 17l-5-5"/>',
    error: '<path d="M18 6 6 18M6 6l12 12"/>',
    warning: '<path d="M12 7v6M12 17h.01"/>',
    info: '<path d="M12 11v6M12 7h.01"/>',
  };
  const TITLES = {
    success: "Berhasil!",
    error: "Gagal!",
    warning: "Perhatian!",
    info: "Info",
  };

  const svg = (paths) =>
    `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;

  const removeToast = (toast) => {
    if (!toast.isConnected || toast.classList.contains("is-leaving")) return;
    toast.style.setProperty("--toast-h", `${toast.offsetHeight}px`); // tinggi awal untuk animasi susut
    toast.classList.add("is-leaving");

    const onEnd = (e) => {
      if (e.target !== toast) return;
      toast.removeEventListener("animationend", onEnd);
      toast.remove();
    };
    toast.addEventListener("animationend", onEnd);

    setTimeout(() => toast.remove(), 500);
  };

  // pasang timer, garis waktu, jeda saat hover, dan tombol X
  const setupToast = (toast) => {
    const duration = parseInt(toast.dataset.toastTimeout, 10) || 5000;
    toast.style.setProperty("--toast-duration", `${duration}ms`);

    let remaining = duration;
    let startedAt = Date.now();
    let timer = setTimeout(() => removeToast(toast), remaining);

    toast.addEventListener("mouseenter", () => {
      clearTimeout(timer);
      remaining -= Date.now() - startedAt;
      toast.classList.add("is-paused");
    });
    toast.addEventListener("mouseleave", () => {
      startedAt = Date.now();
      timer = setTimeout(() => removeToast(toast), Math.max(remaining, 800));
      toast.classList.remove("is-paused");
    });

    toast
      .querySelector("[data-toast-close]")
      ?.addEventListener("click", () => removeToast(toast));
  };

  const getToaster = () => {
    let toaster = document.querySelector(".toaster");
    if (!toaster) {
      toaster = document.createElement("ul");
      toaster.className = "toaster";
      toaster.setAttribute("aria-live", "polite");
      document.body.appendChild(toaster);
    }
    return toaster;
  };

  // Munculkan toast dari JavaScript, mis. setelah AJAX:
  window.showToast = (level, text) => {
    const lvl = ICONS[level] ? level : "info";
    const toast = document.createElement("li");
    toast.className = `toast toast--${lvl}`;
    toast.setAttribute("role", lvl === "error" ? "alert" : "status");
    toast.dataset.toast = "";
    toast.dataset.toastTimeout = lvl === "error" ? "8000" : "5000";
    toast.innerHTML = `
            <span class="toast__icon">${svg(ICONS[lvl])}</span>
            <div class="toast__body">
                <p class="toast__title">${TITLES[lvl]}</p>
                <p class="toast__text"></p>
            </div>
            <button type="button" class="toast__close" data-toast-close aria-label="Tutup notifikasi">${svg(ICONS.error)}</button>
            <span class="toast__progress" aria-hidden="true"></span>`;
    toast.querySelector(".toast__text").textContent = text; // aman dari HTML injection

    getToaster().appendChild(toast);
    setupToast(toast);
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-toast]").forEach(setupToast);
  });
})();
