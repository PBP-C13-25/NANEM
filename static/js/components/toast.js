// Toast Nanem — tutup otomatis & tombol X untuk components/toaster.html
document.addEventListener("DOMContentLoaded", () => {
  const removeToast = (toast) => {
    if (!toast || toast.classList.contains("is-leaving")) return;
    toast.classList.add("is-leaving");

    toast.addEventListener("animationend", () => toast.remove(), {
      once: true,
    });
    setTimeout(() => toast.remove(), 300);
  };

  document.querySelectorAll("[data-toast]").forEach((toast) => {
    const timeout = parseInt(toast.dataset.toastTimeout, 10) || 5000;
    let timer = setTimeout(() => removeToast(toast), timeout);

    // jeda timer saat kursor di atas toast, supaya sempat dibaca
    toast.addEventListener("mouseenter", () => clearTimeout(timer));
    toast.addEventListener("mouseleave", () => {
      timer = setTimeout(() => removeToast(toast), 2000);
    });

    toast
      .querySelector("[data-toast-close]")
      ?.addEventListener("click", () => removeToast(toast));
  });
});
