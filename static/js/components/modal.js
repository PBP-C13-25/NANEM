// Modal Nanem — buka/tutup <dialog class="modal">.
//
// Cara pakai:
//   Pemicu : <a href="/halaman-cadangan/" data-modal-open="id-modal">Hapus</a>
//   Modal  : <dialog class="modal" id="id-modal"> ... </dialog>
//   Tutup  : elemen apa pun di dalam modal dengan atribut data-modal-close
//
// Pemicu sengaja berupa link ke halaman cadangan: kalau JS gagal dimuat,
// user tetap diarahkan ke halaman itu, jadi fitur tidak rusak.

document.addEventListener("DOMContentLoaded", () => {
  // Buka modal
  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-modal-open]");
    if (!trigger) return;

    const modal = document.getElementById(trigger.dataset.modalOpen);
    if (!modal || typeof modal.showModal !== "function") return; // fallback: ikuti link

    e.preventDefault();
    modal.showModal();

    // fokus ke input pertama kalau ada (mis. modal ubah nama)
    const firstInput = modal.querySelector(
      'input:not([type="hidden"]), select, textarea',
    );
    if (firstInput) {
      firstInput.focus();
      if (firstInput.select) firstInput.select();
    }
  });

  // Tutup lewat tombol [data-modal-close]
  document.addEventListener("click", (e) => {
    const closer = e.target.closest("[data-modal-close]");
    if (!closer) return;
    const modal = closer.closest("dialog");
    if (modal) {
      e.preventDefault();
      modal.close();
    }
  });

  // Modal statis (mis. loading) tidak boleh ditutup user lewat Esc
  document
    .querySelectorAll("dialog.modal[data-modal-static]")
    .forEach((modal) => {
      modal.addEventListener("cancel", (e) => e.preventDefault());
    });

  // Tutup kalau klik area gelap di luar kotak modal (kecuali modal statis).
  // Dipasang di document supaya modal yang baru muncul (mis. setelah pencarian) ikut kena.
  document.addEventListener("click", (e) => {
    const modal = e.target;
    if (!(modal instanceof HTMLDialogElement)) return;
    if (!modal.matches(".modal") || modal.hasAttribute("data-modal-static"))
      return;
    const r = modal.getBoundingClientRect();
    const outside =
      e.clientX < r.left ||
      e.clientX > r.right ||
      e.clientY < r.top ||
      e.clientY > r.bottom;
    if (outside) modal.close();
  });

  // Tombol Esc sudah otomatis menutup <dialog> biasa, tidak perlu kode tambahan.

  // Modal yang ada error validasi dari server langsung dibuka lagi
  document
    .querySelectorAll("dialog.modal[data-modal-autoopen]")
    .forEach((modal) => {
      modal.showModal();
    });
});
