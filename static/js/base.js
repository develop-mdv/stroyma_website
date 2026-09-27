// Мобильное меню
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
    const closeMenuBtn = document.getElementById('close-menu-btn');

    function openMobileMenu() {
        if (!mobileMenu || !mobileMenuOverlay) return;
        mobileMenu.inert = false;
        mobileMenu.setAttribute('aria-hidden', 'false');
        mobileMenu.classList.add('is-open');
        mobileMenuOverlay.classList.add('is-open');
        document.body.style.overflow = 'hidden';
        menuToggle.setAttribute('aria-expanded', 'true');
        menuToggle.setAttribute('aria-label', 'Закрыть меню');
        closeMenuBtn.focus();
    }

    function closeMobileMenu() {
        if (!mobileMenu || !mobileMenuOverlay) return;
        const wasOpen = mobileMenu.classList.contains('is-open');
        mobileMenu.classList.remove('is-open');
        mobileMenuOverlay.classList.remove('is-open');
        mobileMenu.setAttribute('aria-hidden', 'true');
        mobileMenu.inert = true;
        document.body.style.overflow = '';
        menuToggle.setAttribute('aria-expanded', 'false');
        menuToggle.setAttribute('aria-label', 'Открыть меню');
        if (wasOpen && window.innerWidth < 1200) menuToggle.focus();
    }

    if (menuToggle) menuToggle.addEventListener('click', openMobileMenu);
    if (closeMenuBtn) closeMenuBtn.addEventListener('click', closeMobileMenu);
    if (mobileMenuOverlay) mobileMenuOverlay.addEventListener('click', closeMobileMenu);

    // Обработка клавиши Escape для закрытия меню
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && mobileMenu && mobileMenu.classList.contains('is-open')) {
            closeMobileMenu();
        }
        if (event.key === 'Tab' && mobileMenu && mobileMenu.classList.contains('is-open')) {
            const focusable = [...mobileMenu.querySelectorAll('a, button')].filter(el => !el.disabled);
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1200 && mobileMenu.classList.contains('is-open')) {
            closeMobileMenu();
        }
    });

    // Cookie consent (UI-only; используется для скрытия баннера и будущей категоризации).
    // Важно: обязательные cookie (sessionid/csrftoken) выставляет Django и они не зависят от согласия.
    initCookieConsent();
});

function initCookieConsent() {
    const banner = document.getElementById('cookie-notification');
    if (!banner) return;

    const acceptBtn = document.getElementById('cookie-accept');
    const settingsBtn = document.getElementById('cookie-settings');

    const STORAGE_KEY = 'cookie_accepted';
    const accepted = (() => {
        try {
            return window.localStorage.getItem(STORAGE_KEY) === '1';
        } catch (_e) {
            return false;
        }
    })();

    if (!accepted) {
        banner.classList.remove('hidden');
    }

    function acceptAll() {
        try {
            window.localStorage.setItem(STORAGE_KEY, '1');
        } catch (_e) {
            // ignore
        }
        banner.classList.add('hidden');
    }

    if (acceptBtn) {
        acceptBtn.addEventListener('click', function(e) {
            e.preventDefault();
            acceptAll();
        });
    }

    if (settingsBtn) {
        settingsBtn.addEventListener('click', function(e) {
            // Простой и безопасный вариант: ведём на страницу политики cookie.
            // Если появятся категории аналитики/маркетинга — сюда можно добавить модальное окно настроек.
            e.preventDefault();
            const link = banner.querySelector('a[href]');
            if (link && link.getAttribute('href')) {
                window.location.href = link.getAttribute('href');
            }
        });
    }
}

// Кнопка "Наверх"
window.addEventListener('scroll', () => {
    const scrollTopButton = document.getElementById('scroll-top');
    if (!scrollTopButton) return;
    if (window.scrollY > 300) {
        scrollTopButton.classList.remove('hidden');
        scrollTopButton.classList.add('flex');
    } else {
        scrollTopButton.classList.add('hidden');
        scrollTopButton.classList.remove('flex');
    }
});

// Функции для модального окна
function openQuickView(productId) {
    const modal = document.getElementById('quick-view-modal');
    const content = document.getElementById('quick-view-content');
    if (!modal || !content) return;

    content.innerHTML = '';

    fetch(`/quick-view/${productId}/`)
        .then(response => response.text())
        .then(data => {
            content.innerHTML = data;
            modal.classList.add('show');
            document.body.style.overflow = 'hidden';
        })
        .catch(error => console.error('Ошибка при загрузке:', error));
}

function closeQuickView() {
    const modal = document.getElementById('quick-view-modal');
    if (!modal) return;
    modal.classList.remove('show');
    document.body.style.overflow = '';
    setTimeout(() => {
        const content = document.getElementById('quick-view-content');
        if (content) content.innerHTML = '';
    }, 300);
}

const quickViewModal = document.getElementById('quick-view-modal');
if (quickViewModal) {
    quickViewModal.addEventListener('click', function (e) {
        if (e.target === this) {
            closeQuickView();
        }
    });
}
