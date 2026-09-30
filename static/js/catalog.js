(() => {
    const browser = document.getElementById('catalog-browser');
    if (!browser) return;

    const searchInput = document.getElementById('id_query');
    const searchForm = document.getElementById('main-search-form');
    const filterForm = document.getElementById('search-form');
    const filterQuery = document.getElementById('filter-query');
    const suggestions = document.getElementById('autocomplete-suggestions');
    const resultsGrid = document.getElementById('products-grid');
    const pagination = document.getElementById('products-pagination');
    const resultCount = document.getElementById('results-count');
    const filterToggle = document.getElementById('toggle-filter');
    const filterClose = filterForm.querySelector('.mobile-filter-close');
    const resetFilters = document.getElementById('reset-filters');
    const priceMin = document.getElementById('price_min');
    const priceMax = document.getElementById('price_max');
    const rangeMin = document.getElementById('price-range-min');
    const rangeMax = document.getElementById('price-range-max');
    const priceSlider = document.getElementById('price-slider');
    const sortSelect = document.getElementById('sort-by');
    const sortTrigger = document.getElementById('sort-trigger');
    const sortMenu = document.getElementById('sort-options');
    const sortCurrent = document.getElementById('sort-current');
    const sortChoices = [...sortMenu.querySelectorAll('.home-sort-option')];
    let priceFloor = Number(browser.dataset.priceMin);
    let priceCeiling = Number(browser.dataset.priceMax);
    let resultRequest = null;
    let suggestionRequest = null;
    let suggestionTimer = null;
    let resultTimer = null;
    let priceFieldTimer = null;
    let activeSuggestion = -1;

    function searchParams(pageNumber = 1) {
        const params = new URLSearchParams();
        params.set('view', 'grid');
        if (browser.dataset.scope) params.set('scope', browser.dataset.scope);
        const query = searchInput.value.trim();
        if (query) params.set('query', query);
        if (priceMin.value !== '' && Number(priceMin.value) !== priceFloor) params.set('price_min', priceMin.value);
        if (priceMax.value !== '' && Number(priceMax.value) !== priceCeiling) params.set('price_max', priceMax.value);
        if (sortSelect.value !== 'name') params.set('sort_by', sortSelect.value);
        if (pageNumber > 1) params.set('page', pageNumber);
        filterForm.querySelectorAll('input[name="category"]:checked').forEach(input => params.append('category', input.value));
        return params;
    }

    function updateAddress() {
        const params = searchParams();
        params.delete('view');
        params.delete('scope');
        const url = new URL(window.location.href);
        url.search = params.toString();
        window.history.replaceState(null, '', url);
    }

    async function loadResults(pageNumber = 1) {
        if (resultRequest) resultRequest.abort();
        const controller = new AbortController();
        resultRequest = controller;
        resultsGrid.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(`${browser.dataset.searchUrl}?${searchParams(pageNumber)}`, { signal: controller.signal });
            if (!response.ok) throw new Error('Search failed');
            const data = await response.json();
            if (pageNumber === 1 && data.price_bounds && data.selected_price) {
                setPriceBounds(data.price_bounds.min, data.price_bounds.max, data.selected_price.min, data.selected_price.max, data.price_bounds.available);
                appliedPriceRange = `${priceMin.value}:${priceMax.value}`;
                updateAddress();
            }
            resultsGrid.innerHTML = data.results;
            pagination.innerHTML = data.pagination;
            resultCount.textContent = `Найдено товаров: ${data.count}`;
        } catch (error) {
            if (error.name !== 'AbortError') resultCount.textContent = 'Не удалось загрузить товары';
        } finally {
            if (resultRequest === controller) {
                resultRequest = null;
                resultsGrid.removeAttribute('aria-busy');
            }
        }
    }

    function hideSuggestions() {
        suggestions.hidden = true;
        suggestions.replaceChildren();
        searchInput.setAttribute('aria-expanded', 'false');
        searchInput.removeAttribute('aria-activedescendant');
        activeSuggestion = -1;
    }

    function setActiveSuggestion(index) {
        const links = [...suggestions.querySelectorAll('.home-suggestion')];
        links.forEach((link, linkIndex) => {
            link.classList.toggle('is-active', linkIndex === index);
            link.setAttribute('aria-selected', linkIndex === index ? 'true' : 'false');
        });
        activeSuggestion = index;
        if (index >= 0 && links[index]) searchInput.setAttribute('aria-activedescendant', links[index].id);
        else searchInput.removeAttribute('aria-activedescendant');
    }

    function showSuggestions(categories, products) {
        suggestions.replaceChildren();
        if (!categories.length && !products.length) {
            const empty = document.createElement('div');
            empty.className = 'home-suggestions-empty';
            empty.textContent = 'Подходящих разделов и товаров пока нет. Попробуйте другой запрос.';
            suggestions.append(empty);
        }
        function addHeading(label) {
            const heading = document.createElement('div');
            heading.className = 'catalog-suggestion-heading';
            heading.setAttribute('role', 'presentation');
            heading.textContent = label;
            suggestions.append(heading);
        }
        let index = 0;
        if (categories.length) addHeading('Категории');
        categories.forEach(category => {
            const link = document.createElement('a');
            link.className = 'home-suggestion catalog-category-suggestion';
            link.id = `catalog-suggestion-${index++}`;
            link.href = category.url;
            link.setAttribute('role', 'option');
            link.setAttribute('aria-selected', 'false');
            const icon = document.createElement('span');
            icon.className = 'catalog-suggestion-icon';
            icon.innerHTML = '<i class="fas fa-folder-open" aria-hidden="true"></i>';
            const text = document.createElement('span');
            text.className = 'catalog-suggestion-text';
            const name = document.createElement('strong');
            name.textContent = category.name;
            text.append(name);
            if (category.parent_name) {
                const parent = document.createElement('small');
                parent.textContent = `В разделе «${category.parent_name}»`;
                text.append(parent);
            }
            link.append(icon, text);
            suggestions.append(link);
        });
        if (products.length) addHeading('Товары');
        products.forEach(product => {
            const link = document.createElement('a');
            link.className = 'home-suggestion';
            link.id = `catalog-suggestion-${index++}`;
            link.href = product.url;
            link.setAttribute('role', 'option');
            link.setAttribute('aria-selected', 'false');
            if (product.image) {
                const image = document.createElement('img');
                image.src = product.image;
                image.alt = '';
                link.append(image);
            } else {
                const placeholder = document.createElement('span');
                placeholder.className = 'home-suggestion-placeholder';
                placeholder.innerHTML = '<i class="fa-regular fa-image" aria-hidden="true"></i>';
                link.append(placeholder);
            }
            const name = document.createElement('span');
            name.className = 'home-suggestion-name';
            name.textContent = product.name;
            const price = document.createElement('strong');
            price.className = 'home-suggestion-price';
            price.textContent = product.price === "Цена уточняется" ? product.price : `${product.price} ₽ / ${product.unit || 'шт'}`;
            link.append(name, price);
            suggestions.append(link);
        });
        suggestions.hidden = false;
        searchInput.setAttribute('aria-expanded', 'true');
        activeSuggestion = -1;
    }

    async function fetchSuggestions() {
        const query = searchInput.value.trim();
        if (query.length < 2) { hideSuggestions(); return; }
        if (suggestionRequest) suggestionRequest.abort();
        const controller = new AbortController();
        suggestionRequest = controller;
        try {
            const params = searchParams();
            params.set('autocomplete', '1');
            const response = await fetch(`${browser.dataset.searchUrl}?${params}`, { signal: controller.signal });
            if (!response.ok) throw new Error('Suggestions failed');
            const data = await response.json();
            if (searchInput.value.trim() === query && document.activeElement === searchInput) {
                showSuggestions(data.categories || [], data.products || []);
            }
        } catch (error) {
            if (error.name !== 'AbortError') hideSuggestions();
        }
    }

    searchInput.addEventListener('input', () => {
        filterQuery.value = searchInput.value;
        clearTimeout(suggestionTimer);
        clearTimeout(resultTimer);
        suggestionTimer = setTimeout(fetchSuggestions, 260);
        resultTimer = setTimeout(() => loadResults(), 550);
    });
    searchInput.addEventListener('focus', () => {
        if (searchInput.value.trim().length >= 2) fetchSuggestions();
    });
    searchInput.addEventListener('keydown', event => {
        const links = [...suggestions.querySelectorAll('.home-suggestion')];
        if (!suggestions.hidden && links.length && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
            event.preventDefault();
            setActiveSuggestion((activeSuggestion + (event.key === 'ArrowDown' ? 1 : -1) + links.length) % links.length);
        } else if (event.key === 'Enter' && activeSuggestion >= 0 && links[activeSuggestion]) {
            event.preventDefault();
            window.location.href = links[activeSuggestion].href;
        } else if (event.key === 'Escape') hideSuggestions();
    });
    searchForm.addEventListener('submit', event => {
        event.preventDefault();
        clearTimeout(resultTimer);
        hideSuggestions();
        filterQuery.value = searchInput.value;
        updateAddress();
        loadResults();
        document.getElementById('catalog-results-title').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    document.addEventListener('pointerdown', event => {
        if (!suggestions.contains(event.target) && !searchForm.contains(event.target)) hideSuggestions();
    });

    function clampPrice(value, fallback) {
        if (value === '') return fallback;
        const number = Number(value);
        return Number.isFinite(number) ? Math.max(priceFloor, Math.min(priceCeiling, Math.round(number))) : fallback;
    }
    function paintPriceRange(minimum, maximum) {
        const span = priceCeiling - priceFloor;
        priceSlider.style.setProperty('--range-start', `${span ? (minimum - priceFloor) / span * 100 : 0}%`);
        priceSlider.style.setProperty('--range-end', `${span ? (maximum - priceFloor) / span * 100 : 100}%`);
        priceSlider.classList.toggle('is-overlapping', !span || (maximum - minimum) / span * (priceSlider.clientWidth - 20) < 22);
    }
    function updateResetState() {
        resetFilters.disabled = Number(priceMin.value) === priceFloor && Number(priceMax.value) === priceCeiling &&
            sortSelect.value === 'name' && !filterForm.querySelector('input[name="category"]:checked');
    }
    function setPrices(minimum, maximum) {
        priceMin.value = minimum;
        priceMax.value = maximum;
        rangeMin.value = minimum;
        rangeMax.value = maximum;
        paintPriceRange(minimum, maximum);
        updateResetState();
    }
    function setPriceBounds(minimum, maximum, selectedMinimum, selectedMaximum, available = true) {
        priceFloor = Number(minimum);
        priceCeiling = Number(maximum);
        [priceMin, priceMax, rangeMin, rangeMax].forEach(input => {
            input.min = priceFloor;
            input.max = priceCeiling;
        });
        const singlePrice = available && priceCeiling <= priceFloor;
        const priceUnavailable = !available || singlePrice;
        priceSlider.hidden = !available;
        priceSlider.classList.toggle('is-single-price', singlePrice);
        priceMin.disabled = priceUnavailable;
        priceMax.disabled = priceUnavailable;
        rangeMin.disabled = priceUnavailable;
        rangeMax.disabled = priceUnavailable;
        setPrices(Number(selectedMinimum), Number(selectedMaximum));
        if (!available) {
            priceMin.value = '';
            priceMax.value = '';
            updateResetState();
        }
    }
    function applyFilters() {
        updateAddress();
        updateResetState();
        appliedPriceRange = `${priceMin.value}:${priceMax.value}`;
        loadResults();
    }
    const initialMin = clampPrice(priceMin.value, priceFloor);
    const initialMax = clampPrice(priceMax.value, priceCeiling);
    setPriceBounds(priceFloor, priceCeiling, Math.min(initialMin, initialMax), Math.max(initialMin, initialMax), browser.dataset.priceAvailable === 'true');
    let appliedPriceRange = `${priceMin.value}:${priceMax.value}`;

    rangeMin.addEventListener('input', () => setPrices(Math.min(Number(rangeMin.value), Number(priceMax.value)), Number(priceMax.value)));
    rangeMax.addEventListener('input', () => setPrices(Number(priceMin.value), Math.max(Number(rangeMax.value), Number(priceMin.value))));
    [rangeMin, rangeMax].forEach(input => {
        input.addEventListener('pointerdown', () => {
            rangeMin.classList.toggle('is-active', input === rangeMin);
            rangeMax.classList.toggle('is-active', input === rangeMax);
        });
        input.addEventListener('change', applyFilters);
    });
    priceSlider.addEventListener('pointerdown', event => {
        if (rangeMin.disabled || event.target.matches('input')) return;
        const track = priceSlider.querySelector('.home-price-track').getBoundingClientRect();
        const progress = Math.max(0, Math.min(1, (event.clientX - track.left) / track.width));
        const value = Math.round(priceFloor + progress * (priceCeiling - priceFloor));
        const minimum = Number(priceMin.value);
        const maximum = Number(priceMax.value);
        const moveMinimum = Math.abs(value - minimum) < Math.abs(value - maximum) ||
            (Math.abs(value - minimum) === Math.abs(value - maximum) && value < minimum);
        if (moveMinimum) setPrices(Math.min(value, maximum), maximum);
        else setPrices(minimum, Math.max(value, minimum));
        applyFilters();
    });
    function commitPriceField(source, apply = true) {
        clearTimeout(priceFieldTimer);
        if (source === 'min') {
            const minimum = clampPrice(priceMin.value, Number(rangeMin.value));
            setPrices(minimum, Math.max(minimum, clampPrice(priceMax.value, priceCeiling)));
        } else {
            const maximum = clampPrice(priceMax.value, Number(rangeMax.value));
            setPrices(Math.min(clampPrice(priceMin.value, priceFloor), maximum), maximum);
        }
        if (apply && `${priceMin.value}:${priceMax.value}` !== appliedPriceRange) applyFilters();
    }
    function previewPriceField(source) {
        if ((source === 'min' && priceMin.value === '') || (source === 'max' && priceMax.value === '')) return;
        const minimum = clampPrice(priceMin.value, priceFloor);
        const maximum = clampPrice(priceMax.value, priceCeiling);
        const low = source === 'min' ? minimum : Math.min(minimum, maximum);
        const high = source === 'min' ? Math.max(minimum, maximum) : maximum;
        rangeMin.value = low;
        rangeMax.value = high;
        paintPriceRange(low, high);
        updateResetState();
        clearTimeout(priceFieldTimer);
        priceFieldTimer = setTimeout(() => commitPriceField(source), 450);
    }
    priceMin.addEventListener('input', () => previewPriceField('min'));
    priceMax.addEventListener('input', () => previewPriceField('max'));
    priceMin.addEventListener('change', () => commitPriceField('min'));
    priceMax.addEventListener('change', () => commitPriceField('max'));
    priceMin.addEventListener('blur', () => commitPriceField('min'));
    priceMax.addEventListener('blur', () => commitPriceField('max'));

    function syncSortMenu() {
        const selected = sortChoices.find(choice => choice.dataset.value === sortSelect.value) || sortChoices[0];
        sortCurrent.textContent = selected.querySelector('span').textContent;
        sortChoices.forEach(choice => choice.setAttribute('aria-selected', choice === selected ? 'true' : 'false'));
    }
    function setSortMenuOpen(open, focusSelected = false) {
        sortMenu.hidden = !open;
        sortTrigger.setAttribute('aria-expanded', open ? 'true' : 'false');
        sortTrigger.closest('.home-sort-wrap').classList.toggle('is-open', open);
        if (open) {
            const panel = sortTrigger.closest('.home-filter-panel').getBoundingClientRect();
            const trigger = sortTrigger.getBoundingClientRect();
            sortMenu.classList.toggle('opens-up', Math.min(window.innerHeight, panel.bottom) - trigger.bottom < 150);
            if (focusSelected) (sortChoices.find(choice => choice.dataset.value === sortSelect.value) || sortChoices[0]).focus();
        }
    }
    sortTrigger.addEventListener('click', () => setSortMenuOpen(sortMenu.hidden));
    sortTrigger.addEventListener('keydown', event => {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            setSortMenuOpen(true, true);
        } else if (event.key === 'Escape') setSortMenuOpen(false);
    });
    sortMenu.addEventListener('click', event => {
        const choice = event.target.closest('.home-sort-option');
        if (!choice) return;
        sortSelect.value = choice.dataset.value;
        syncSortMenu();
        setSortMenuOpen(false);
        sortTrigger.focus();
        applyFilters();
    });
    sortMenu.addEventListener('keydown', event => {
        const index = sortChoices.indexOf(document.activeElement);
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Home' || event.key === 'End') {
            event.preventDefault();
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? sortChoices.length - 1 :
                (index + (event.key === 'ArrowDown' ? 1 : -1) + sortChoices.length) % sortChoices.length;
            sortChoices[next].focus();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            setSortMenuOpen(false);
            sortTrigger.focus();
        } else if (event.key === 'Tab') setSortMenuOpen(false);
    });
    document.addEventListener('pointerdown', event => {
        if (!sortTrigger.closest('.home-sort-wrap').contains(event.target)) setSortMenuOpen(false);
    });
    sortSelect.addEventListener('change', () => { syncSortMenu(); applyFilters(); });

    const categoryNodes = [...filterForm.querySelectorAll('.catalog-category-node')];
    const categoryInput = node => node.querySelector(':scope > .catalog-category-row input[name="category"]');
    function syncCategoryStates() {
        [...categoryNodes].reverse().forEach(node => {
            const input = categoryInput(node);
            input.indeterminate = !input.checked && [...node.querySelectorAll(':scope > .catalog-category-children input[name="category"]')]
                .some(child => child.checked || child.indeterminate);
        });
    }
    categoryNodes.forEach(node => {
        const input = categoryInput(node);
        input.addEventListener('change', () => {
            if (input.checked) {
                node.querySelectorAll(':scope > .catalog-category-children input[name="category"]').forEach(child => { child.checked = false; });
                let parent = node.parentElement.closest('.catalog-category-node');
                while (parent) {
                    categoryInput(parent).checked = false;
                    parent = parent.parentElement.closest('.catalog-category-node');
                }
            }
            syncCategoryStates();
            applyFilters();
        });
    });
    syncCategoryStates();
    filterForm.querySelectorAll('.accordion-toggle').forEach(button => {
        const target = document.getElementById(button.dataset.target);
        const categoryName = button.closest('.catalog-category-row').querySelector('.catalog-category-link').textContent.trim();
        function updateAccordion(open) {
            button.classList.toggle('active', open);
            button.setAttribute('aria-expanded', open ? 'true' : 'false');
            button.setAttribute('aria-label', `${open ? 'Скрыть' : 'Показать'} подкатегории: ${categoryName}`);
        }
        button.addEventListener('click', () => {
            if (!target) return;
            target.classList.toggle('hidden');
            updateAccordion(!target.classList.contains('hidden'));
        });
        if (target && target.querySelector('input:checked')) target.classList.remove('hidden');
        updateAccordion(target && !target.classList.contains('hidden'));
    });

    function setMobileFiltersOpen(open) {
        filterForm.classList.toggle('mobile-filter-visible', open);
        filterToggle.querySelector('span').textContent = open ? 'Скрыть фильтры' : 'Фильтры';
        filterToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    }
    filterToggle.addEventListener('click', () => {
        const open = !filterForm.classList.contains('mobile-filter-visible');
        setMobileFiltersOpen(open);
        if (open) filterToggle.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    filterClose.addEventListener('click', () => {
        setMobileFiltersOpen(false);
        filterToggle.focus({ preventScroll: true });
        filterToggle.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    filterForm.addEventListener('submit', event => {
        event.preventDefault();
        commitPriceField('min', false);
        applyFilters();
        if (window.matchMedia('(max-width: 900px)').matches) {
            setMobileFiltersOpen(false);
            document.getElementById('catalog-results-title').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
    resetFilters.addEventListener('click', () => {
        clearTimeout(priceFieldTimer);
        setPrices(priceFloor, priceCeiling);
        sortSelect.value = 'name';
        syncSortMenu();
        setSortMenuOpen(false);
        filterForm.querySelectorAll('input[name="category"]').forEach(input => { input.checked = false; input.indeterminate = false; });
        applyFilters();
    });
})();
