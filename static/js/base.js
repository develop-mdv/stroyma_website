// Мобильное меню
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
    const closeMenuBtn = document.getElementById('close-menu-btn');

    // Функция для открытия меню
    function openMobileMenu() {
        if (!mobileMenu || !mobileMenuOverlay) return;
        mobileMenu.classList.remove('translate-x-full');
        mobileMenuOverlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';

        if (menuToggle) menuToggle.innerHTML = '<i class="fas fa-times text-base"></i>';

        setTimeout(() => {
            mobileMenuOverlay.style.opacity = '1';
        }, 10);
    }

    // Функция для закрытия меню
    function closeMobileMenu() {
        if (!mobileMenu || !mobileMenuOverlay) return;
        mobileMenu.classList.add('translate-x-full');
        mobileMenuOverlay.style.opacity = '0';
        document.body.style.overflow = '';

        if (menuToggle) menuToggle.innerHTML = '<i class="fas fa-bars text-base"></i>';

        setTimeout(() => {
            mobileMenuOverlay.classList.add('hidden');
        }, 300);
    }

    if (menuToggle) menuToggle.addEventListener('click', openMobileMenu);
    if (closeMenuBtn) closeMenuBtn.addEventListener('click', closeMobileMenu);
    if (mobileMenuOverlay) mobileMenuOverlay.addEventListener('click', closeMobileMenu);

    // Обработка клавиши Escape для закрытия меню
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && mobileMenu && !mobileMenu.classList.contains('translate-x-full')) {
            closeMobileMenu();
        }
    });

    // Закрытие меню при изменении ширины выше lg (≥1024)
    let lastWidth = window.innerWidth;
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 1024 && lastWidth < 1024) {
            closeMobileMenu();
        }
        lastWidth = window.innerWidth;
    });

    highlightActiveMenuItem();

    const menuLinks = document.querySelectorAll('#mobile-menu a');
    menuLinks.forEach(link => {
        link.addEventListener('click', function() {
            setTimeout(closeMobileMenu, 150);
        });
    });
});

// Функция для подсветки активного пункта меню
function highlightActiveMenuItem() {
    const currentPath = window.location.pathname;
    const menuLinks = document.querySelectorAll('#mobile-menu a');

    menuLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath) {
            if (currentPath === linkPath ||
                (linkPath !== '/' && currentPath.startsWith(linkPath))) {
                link.classList.add('bg-gray-50', 'font-medium');
            }
        }
    });
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
