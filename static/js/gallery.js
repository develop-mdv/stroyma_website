document.addEventListener('DOMContentLoaded', () => {
    const links = Array.from(document.querySelectorAll('[data-fancybox="gallery"]'));
    if (!links.length || typeof HTMLDialogElement === 'undefined') return;
    const dialog = document.createElement('dialog');
    dialog.className = 'image-gallery-dialog';
    dialog.setAttribute('aria-label', 'Просмотр фотографий');
    dialog.innerHTML = '<button type="button" class="image-gallery-close" aria-label="Закрыть">×</button><figure><img alt=""><figcaption aria-live="polite"></figcaption></figure><div class="image-gallery-controls"><button type="button" data-direction="-1" aria-label="Предыдущее фото">←</button><button type="button" data-direction="1" aria-label="Следующее фото">→</button></div>';
    document.body.appendChild(dialog);
    const img = dialog.querySelector('img');
    const caption = dialog.querySelector('figcaption');
    let index = 0;
    function show(next) {
        index = (next + links.length) % links.length;
        img.src = links[index].href;
        img.alt = links[index].querySelector('img')?.alt || 'Фотография';
        caption.textContent = `${index + 1} / ${links.length} · ${img.alt}`;
    }
    links.forEach((link, position) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            show(position);
            dialog.showModal();
        });
    });
    dialog.querySelector('.image-gallery-close').addEventListener('click', () => dialog.close());
    dialog.querySelectorAll('[data-direction]').forEach(button => {
        button.disabled = links.length < 2;
        button.addEventListener('click', () => show(index + Number(button.dataset.direction)));
    });
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('keydown', event => {
        if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
            event.preventDefault();
            show(index + (event.key === 'ArrowLeft' ? -1 : 1));
        }
    });
});
