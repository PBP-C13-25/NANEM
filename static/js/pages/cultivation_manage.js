const form = document.getElementById("kelola-filters");

if (form) {
  const searchInput = form.querySelector(".search-field__input");
  let timer;
  let controller;

  const buildUrl = (page) => {
    const url = new URL(window.location.pathname, window.location.origin);
    new FormData(form).forEach((value, key) => {
      const text = String(value).trim();
      if (text) url.searchParams.set(key, text);
    });
    if (page) url.searchParams.set("page", page);
    return url;
  };

  const load = async (url) => {
    controller?.abort();
    controller = new AbortController();

    try {
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) throw new Error("bad response");
      const html = await response.text();
      const doc = new DOMParser().parseFromString(html, "text/html");
      const current = document.getElementById("kelola-results");
      const fresh = doc.getElementById("kelola-results");
      if (current && fresh) current.replaceWith(fresh);
      history.replaceState(null, "", url);
    } catch (err) {
      if (err.name !== "AbortError") {
        window.showToast("error", "Pencarian gagal. Coba lagi.");
      }
    }
  };

  const runSearch = () => load(buildUrl());

  searchInput?.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(runSearch, 300);
  });

  form.querySelectorAll("select").forEach((select) => {
    select.addEventListener("change", () => {
      clearTimeout(timer);
      runSearch();
    });
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    clearTimeout(timer);
    runSearch();
  });

  form.querySelector("[data-kelola-reset]")?.addEventListener("click", (e) => {
    e.preventDefault();
    clearTimeout(timer);
    form.querySelectorAll("select").forEach((select) => {
      select.value = "";
    });
    if (searchInput) {
      searchInput.value = "";
      searchInput.dispatchEvent(new Event("input", { bubbles: true }));
      clearTimeout(timer);
    }
    runSearch();
  });

  document.addEventListener("click", (e) => {
    const link = e.target.closest("#kelola-results .plant-admin__pagination a");
    if (!link) return;
    e.preventDefault();
    load(new URL(link.href, window.location.origin));
  });
}