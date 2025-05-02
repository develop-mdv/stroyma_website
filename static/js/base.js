// Переключатель тем
const themeToggle = document.getElementById('theme-toggle');
themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    themeToggle.innerHTML = newTheme === 'light' ? '<i class="fas fa-moon text-2xl"></i>' : '<i class="fas fa-sun text-2xl"></i>';
});

// Загрузка сохраненной темы
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
themeToggle.innerHTML = savedTheme === 'light' ? '<i class="fas fa-moon text-2xl"></i>' : '<i class="fas fa-sun text-2xl"></i>';

// Мобильное меню
const menuToggle = document.getElementById('menu-toggle');
const mobileMenu = document.getElementById('mobile-menu');
menuToggle.addEventListener('click', () => {
    mobileMenu.classList.toggle('hidden');
});

// Кнопка "Наверх"
window.addEventListener('scroll', () => {
    const scrollTopButton = document.getElementById('scroll-top');
    if (window.scrollY > 300) {
        scrollTopButton.classList.remove('hidden');
    } else {
        scrollTopButton.classList.add('hidden');
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