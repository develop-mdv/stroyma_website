// Переключатель тем
const themeToggle = document.getElementById('theme-toggle');
themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    themeToggle.innerHTML = newTheme === 'light' ? '<i class="fas fa-moon text-sm"></i>' : '<i class="fas fa-sun text-sm"></i>';
    
    // Обновляем иконку в мобильном меню
    const mobileThemeToggle = document.getElementById('mobile-theme-toggle');
    if (mobileThemeToggle) {
            mobileThemeToggle.innerHTML = newTheme === 'light' 
            ? '<i class="fas fa-moon text-sm"></i> Сменить тему'
            : '<i class="fas fa-sun text-sm"></i> Сменить тему';
    }
});

// Загрузка сохраненной темы
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
themeToggle.innerHTML = savedTheme === 'light' ? '<i class="fas fa-moon text-sm"></i>' : '<i class="fas fa-sun text-sm"></i>';

// Мобильное меню
document.addEventListener('DOMContentLoaded', function() {
    const menuToggle = document.getElementById('menu-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    const mobileMenuOverlay = document.getElementById('mobile-menu-overlay');
    const closeMenuBtn = document.getElementById('close-menu-btn');
    const mobileThemeToggle = document.getElementById('mobile-theme-toggle');

    // Функция для открытия меню
    function openMobileMenu() {
        mobileMenu.classList.remove('translate-x-full');
        mobileMenuOverlay.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Изменить иконку меню на крестик
        menuToggle.innerHTML = '<i class="fas fa-times text-base"></i>';
        
        // Плавное появление оверлея
        setTimeout(() => {
            mobileMenuOverlay.style.opacity = '1';
        }, 10);
    }

    // Функция для закрытия меню
    function closeMobileMenu() {
        mobileMenu.classList.add('translate-x-full');
        mobileMenuOverlay.style.opacity = '0';
        document.body.style.overflow = '';
        
        // Вернуть иконку меню
        menuToggle.innerHTML = '<i class="fas fa-bars text-base"></i>';
        
        // Скрытие оверлея после анимации
        setTimeout(() => {
            mobileMenuOverlay.classList.add('hidden');
        }, 300);
    }

    // Обработчики событий для мобильного меню
    if (menuToggle) menuToggle.addEventListener('click', openMobileMenu);
    if (closeMenuBtn) closeMenuBtn.addEventListener('click', closeMobileMenu);
    if (mobileMenuOverlay) mobileMenuOverlay.addEventListener('click', closeMobileMenu);
    if (mobileThemeToggle) mobileThemeToggle.addEventListener('click', () => themeToggle.click());

    // Обработка клавиши Escape для закрытия меню
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && !mobileMenu.classList.contains('translate-x-full')) {
            closeMobileMenu();
        }
    });

    // Подсветка активного пункта меню
    highlightActiveMenuItem();

    // Закрытие меню при нажатии на пункт меню
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

    content.innerHTML = '';

    fetch(`/product/${productId}/quick-view/`)
        .then(response => response.text())
        .then(data => {
            content.innerHTML = data;
            modal.classList.add('show');
        })
        .catch(error => console.error('Ошибка при загрузке:', error));
}

function closeQuickView() {
    const modal = document.getElementById('quick-view-modal');
    modal.classList.remove('show');
    setTimeout(() => {
        document.getElementById('quick-view-content').innerHTML = '';
    }, 300);
}

document.getElementById('quick-view-modal').addEventListener('click', function (e) {
    if (e.target === this) {
        closeQuickView();
    }
});