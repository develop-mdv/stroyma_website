document.addEventListener('DOMContentLoaded', function() {
    
    // --- UI Controls Logic ---
    const facadeNameLabel = document.getElementById('activeFacadeName');
    const baseNameLabel = document.getElementById('activeBaseName');
    const root = document.documentElement;

    let currentFacadeColor = '';
    let currentBaseTexture = '';

    // Handle Facade Color Click
    document.querySelectorAll('.color-swatch').forEach(swatch => {
        swatch.addEventListener('click', function() {
            const color = this.dataset.color;
            const name = this.dataset.name;
            const target = this.dataset.target;

            // Apply via CSS variable to whole document (affects main house and cloned loupe house)
            root.style.setProperty('--house-facade', color);

            // Update UI
            document.querySelectorAll(`.color-swatch[data-target="${target}"]`).forEach(s => {
                s.classList.remove('selected');
                const icon = s.querySelector('.check-icon');
                if(icon) icon.style.opacity = '0';
            });
            this.classList.add('selected');
            const myIcon = this.querySelector('.check-icon');
            if(myIcon) myIcon.style.opacity = '1';

            facadeNameLabel.textContent = name;
            currentFacadeColor = color;
        });
    });

    // Handle Base Texture Click
    document.querySelectorAll('.texture-swatch').forEach(swatch => {
        swatch.addEventListener('click', function() {
            const image = this.dataset.image;
            const name = this.dataset.name;
            const target = this.dataset.target;

            root.style.setProperty('--house-base', `url('${image}')`);

            // Update UI
            document.querySelectorAll(`.texture-swatch[data-target="${target}"]`).forEach(s => {
                s.classList.remove('selected');
                const icon = s.querySelector('.check-icon');
                if(icon) icon.style.opacity = '0';
            });
            this.classList.add('selected');
            const myIcon = this.querySelector('.check-icon');
            if(myIcon) myIcon.style.opacity = '1';

            baseNameLabel.textContent = name;
            currentBaseTexture = image;
        });
    });

    // Reset Button
    document.getElementById('resetConfigBtn')?.addEventListener('click', () => {
        root.style.setProperty('--house-facade', '#F8F5EF');
        root.style.setProperty('--house-base', 'none');
        
        // Clear UI Classes
        document.querySelectorAll('.color-swatch, .texture-swatch').forEach(s => {
            s.classList.remove('selected');
            const icon = s.querySelector('.check-icon');
            if(icon) icon.style.opacity = '0';
        });

        facadeNameLabel.textContent = 'Не выбран';
        baseNameLabel.textContent = 'Не выбрана';
    });

    // --- ZOOM LENS (ЛУПА) LOGIC ---
    const container = document.getElementById('houseContainer');
    const visualsWrapper = document.getElementById('visualsWrapper');
    const zoomLens = document.getElementById('zoomLens');
    const lensContent = document.getElementById('lensContent');
    const ZOOM_SCALE = 2.5;

    container.addEventListener('mouseenter', function() {
        // Clone exactly whatever is in visualsWrapper for picture-perfect syncing!
        lensContent.innerHTML = visualsWrapper.innerHTML;
        zoomLens.style.opacity = '1';
    });

    container.addEventListener('mousemove', function(e) {
        const rect = container.getBoundingClientRect();
        
        // Clamp mouse position within container relative bounds
        let x = e.clientX - rect.left;
        let y = e.clientY - rect.top;

        // Position the lens physical div at cursor
        const lensWidth = zoomLens.offsetWidth;
        const lensHeight = zoomLens.offsetHeight;
        zoomLens.style.left = `${x - lensWidth / 2}px`;
        zoomLens.style.top = `${y - lensHeight / 2}px`;

        // The content container inside the lens must be the same size as the outer visuals
        lensContent.style.width = `${rect.width}px`;
        lensContent.style.height = `${rect.height}px`;

        // Mathematical offset for scaling from the top-left origin
        const moveX = (lensWidth / 2) - (x * ZOOM_SCALE);
        const moveY = (lensHeight / 2) - (y * ZOOM_SCALE);

        lensContent.style.transform = `translate(${moveX}px, ${moveY}px) scale(${ZOOM_SCALE})`;
    });

    container.addEventListener('mouseleave', function() {
        zoomLens.style.opacity = '0';
    });
});