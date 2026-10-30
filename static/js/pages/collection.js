document.addEventListener('DOMContentLoaded', () => {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;

            // Reset class active
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Aktifkan tab yang diklik
            button.classList.add('active');
            const activeContent = document.getElementById(`tab-${targetTab}`);
            if (activeContent) {
                activeContent.classList.add('active');
            }
        });
    });

    const likeButtons = document.querySelectorAll(".btn-like");

    likeButtons.forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault(); 

            const postId = btn.dataset.id;

            // Ambil token CSRF
            const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
            const csrfToken = csrfInput ? csrfInput.value : '';

            const iconWrapper = btn.querySelector(".icon-like-wrapper");
            const likeCountSpan = btn.querySelector(".like-count");

            try {
                const response = await fetch(`/collection/${postId}/like/`, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    },
                });

                if (response.ok) {
                    const data = await response.json();
                    console.log("Response dari Server:", data); // Cek data di Console Browser (F12)

                    // Sesuaikan key JSON (Mendukung data.is_liked atau data.liked)
                    const isLiked = data.is_liked !== undefined ? data.is_liked : data.liked;
                    const count = data.like_count !== undefined ? data.like_count : data.count;

                    // Toggle Class untuk Warna & Ikon
                    if (isLiked) {
                        btn.classList.add("is-liked");
                        if (iconWrapper) iconWrapper.classList.add("is-active");
                    } else {
                        btn.classList.remove("is-liked");
                        if (iconWrapper) iconWrapper.classList.remove("is-active");
                    }
                    
                    // Update Angka Like
                    if (likeCountSpan && count !== undefined) {
                        likeCountSpan.textContent = count;
                    }
                } else {
                    console.error("Server merespon dengan status error:", response.status);
                }
            } catch (error) {
                console.error("Gagal mengirim request like:", error);
            }
        });
    });
    
    const fileInput = document.getElementById('id_photo');
    const uploadZone = document.getElementById('upload-zone');
    const placeholder = document.getElementById('upload-placeholder');
    const preview = document.getElementById('upload-preview');
    const previewImg = document.getElementById('preview-img');
    const removeBtn = document.getElementById('remove-img-btn');

    if (fileInput && uploadZone) {
        // Reset tampilan awal
        if (!fileInput.value) {
            preview.classList.add('is-hidden');
            placeholder.classList.remove('is-hidden');
        }

        // Tampilkan preview saat file dipilih
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    previewImg.src = event.target.result;
                    placeholder.classList.add('is-hidden');
                    preview.classList.remove('is-hidden');
                };
                reader.readAsDataURL(file);
            }
        });

        // Tombol Hapus Gambar
        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                fileInput.value = '';
                previewImg.removeAttribute('src');
                preview.classList.add('is-hidden');
                placeholder.classList.remove('is-hidden');
            });
        }
    }

});