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

    const likeBtn = document.getElementById('like-btn');
    
    if (likeBtn) {
        likeBtn.addEventListener('click', async () => {
            const postId = likeBtn.dataset.id;
            const likeCountSpan = document.getElementById('like-count');
            const likeIcon = document.getElementById('like-icon');
            const csrfTokenInput = document.querySelector('[name=csrfmiddlewaretoken]');
            
            if (!csrfTokenInput) {
                console.error('CSRF token tidak ditemukan di halaman HTML!');
                return;
            }

            try {
                const response = await fetch(`/collection/${postId}/like/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfTokenInput.value,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const data = await response.json();

                    likeCountSpan.textContent = data.total_likes;

                    if (data.liked) {
                        likeBtn.classList.add('is-liked');
                        if (likeIconWrapper) likeIconWrapper.classList.add('is-active');
                    } else {
                        likeBtn.classList.remove('is-liked');
                        if (likeIconWrapper) likeIconWrapper.classList.remove('is-active');
                    }
                } else {
                    console.error('Server merespon dengan status:', response.status);
                }
            } catch (error) {
                console.error('Error saat melakukan request like:', error);
            }
        });
    }
    
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