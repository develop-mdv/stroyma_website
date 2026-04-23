document.addEventListener('DOMContentLoaded', function () {

    // --- UI Controls Logic ---
    const facadeNameLabel = document.getElementById('activeFacadeName');
    const baseNameLabel = document.getElementById('activeBaseName');
    const root = document.documentElement;

    let currentFacadeColor = '';
    let currentBaseTexture = '';

    // Handle Facade Color Click
    document.querySelectorAll('.color-swatch').forEach(swatch => {
        swatch.addEventListener('click', function () {
            const color = this.dataset.color;
            const name = this.dataset.name;
            const target = this.dataset.target;

            root.style.setProperty('--house-facade', color);

            document.querySelectorAll(`.color-swatch[data-target="${target}"]`).forEach(s => {
                s.classList.remove('selected');
                const icon = s.querySelector('.check-icon');
                if (icon) icon.style.opacity = '0';
            });
            this.classList.add('selected');
            const myIcon = this.querySelector('.check-icon');
            if (myIcon) myIcon.style.opacity = '1';

            if (facadeNameLabel) facadeNameLabel.textContent = name;
            currentFacadeColor = color;
        });
    });

    // Handle Base Texture Click
    document.querySelectorAll('.texture-swatch').forEach(swatch => {
        swatch.addEventListener('click', function () {
            const image = this.dataset.image;
            const name = this.dataset.name;
            const target = this.dataset.target;

            root.style.setProperty('--house-base', `url('${image}')`);

            document.querySelectorAll(`.texture-swatch[data-target="${target}"]`).forEach(s => {
                s.classList.remove('selected');
                const icon = s.querySelector('.check-icon');
                if (icon) icon.style.opacity = '0';
            });
            this.classList.add('selected');
            const myIcon = this.querySelector('.check-icon');
            if (myIcon) myIcon.style.opacity = '1';

            if (baseNameLabel) baseNameLabel.textContent = name;
            currentBaseTexture = image;
        });
    });

    // Reset Button
    const resetBtn = document.getElementById('resetConfigBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            root.style.setProperty('--house-facade', '#F8F5EF');
            root.style.setProperty('--house-base', 'none');

            document.querySelectorAll('.color-swatch, .texture-swatch').forEach(s => {
                s.classList.remove('selected');
                const icon = s.querySelector('.check-icon');
                if (icon) icon.style.opacity = '0';
            });

            if (facadeNameLabel) facadeNameLabel.textContent = 'Не выбран';
            if (baseNameLabel) baseNameLabel.textContent = 'Не выбрана';
        });
    }

    // --- ZOOM LENS (ЛУПА) LOGIC ---
    const container = document.getElementById('houseContainer');
    const visualsWrapper = document.getElementById('visualsWrapper');
    const zoomLens = document.getElementById('zoomLens');
    const lensContent = document.getElementById('lensContent');
    const ZOOM_SCALE = 2.5;

    if (!container || !visualsWrapper || !zoomLens || !lensContent) return;

    let lensActive = false;
    let activePointerType = null;
    let activePointerId = null;

    function showLens() {
        lensContent.innerHTML = visualsWrapper.innerHTML;
        zoomLens.style.opacity = '1';
        lensActive = true;
    }

    function hideLens() {
        zoomLens.style.opacity = '0';
        lensActive = false;
        activePointerType = null;
        activePointerId = null;
    }

    function updateLens(clientX, clientY) {
        const rect = container.getBoundingClientRect();
        const x = clientX - rect.left;
        const y = clientY - rect.top;

        const lensWidth = zoomLens.offsetWidth;
        const lensHeight = zoomLens.offsetHeight;

        // На тач — смещаем лупу выше пальца, чтобы палец её не закрывал
        const verticalOffset = activePointerType === 'touch' ? -90 : 0;

        zoomLens.style.left = `${x - lensWidth / 2}px`;
        zoomLens.style.top = `${y - lensHeight / 2 + verticalOffset}px`;

        lensContent.style.width = `${rect.width}px`;
        lensContent.style.height = `${rect.height}px`;

        const moveX = (lensWidth / 2) - (x * ZOOM_SCALE);
        const moveY = (lensHeight / 2) - (y * ZOOM_SCALE);

        lensContent.style.transform = `translate(${moveX}px, ${moveY}px) scale(${ZOOM_SCALE})`;
    }

    // Pointer Events — работают для мыши, тача и пера
    container.addEventListener('pointerenter', function (e) {
        if (e.pointerType === 'mouse') {
            activePointerType = 'mouse';
            showLens();
            updateLens(e.clientX, e.clientY);
        }
    });

    container.addEventListener('pointerdown', function (e) {
        if (e.pointerType === 'touch' || e.pointerType === 'pen') {
            activePointerType = e.pointerType;
            activePointerId = e.pointerId;
            try { container.setPointerCapture(e.pointerId); } catch (err) { /* no-op */ }
            showLens();
            updateLens(e.clientX, e.clientY);
            e.preventDefault();
        }
    }, { passive: false });

    container.addEventListener('pointermove', function (e) {
        if (!lensActive) return;
        if (activePointerType === 'mouse' && e.pointerType !== 'mouse') return;
        if ((activePointerType === 'touch' || activePointerType === 'pen') && e.pointerId !== activePointerId) return;
        updateLens(e.clientX, e.clientY);
        if (activePointerType !== 'mouse') e.preventDefault();
    }, { passive: false });

    container.addEventListener('pointerup', function (e) {
        if (activePointerType === 'touch' || activePointerType === 'pen') {
            if (e.pointerId === activePointerId) {
                try { container.releasePointerCapture(e.pointerId); } catch (err) { /* no-op */ }
                hideLens();
            }
        }
    });

    container.addEventListener('pointercancel', function (e) {
        if (activePointerType === 'touch' || activePointerType === 'pen') {
            if (e.pointerId === activePointerId) {
                hideLens();
            }
        }
    });

    container.addEventListener('pointerleave', function (e) {
        if (e.pointerType === 'mouse' && activePointerType === 'mouse') {
            hideLens();
        }
    });
});
