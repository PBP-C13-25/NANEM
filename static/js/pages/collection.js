// static/js/pages/collection.js

document.addEventListener('DOMContentLoaded', () => {
    const likeBtn = document.getElementById('like-btn');
    
    if (likeBtn) {
        likeBtn.addEventListener('click', async () => {
            const postId = likeBtn.dataset.id;
            const likeCountSpan = document.getElementById('like-count');
            const likeIcon = document.getElementById('like-icon');

            try {
                const response = await fetch(`/collection/${postId}/like/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
                        'Content-Type': 'application/json'
                    }
                });

                if (response.ok) {
                    const data = await response.json();
                    likeCountSpan.textContent = data.total_likes;
                    likeIcon.textContent = data.liked ? '❤️' : '🤍';
                    
                    // Memanggil fungsi toast dari toast.js
                    window.showToast('success', data.liked ? 'Menyukai postingan' : 'Batal menyukai postingan');
                } else {
                    window.showToast('error', 'Gagal memproses permintaan.');
                }
            } catch (error) {
                console.error('Error:', error);
                window.showToast('error', 'Terjadi kesalahan pada server.');
            }
        });
    }
});