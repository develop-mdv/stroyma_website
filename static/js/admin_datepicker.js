// Скрипт для обработки DateRangeFilter в админке

// Функция для инициализации datepicker
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, доступен ли jQuery от Django
    if (typeof django !== 'undefined' && django.jQuery) {
        var $ = django.jQuery;
        
        // Если Calendar не определен, создаем заглушку
        if (typeof Calendar === 'undefined') {
            window.Calendar = function() {
                return {
                    show: function() {},
                    hide: function() {}
                };
            };
        }
        
        // Добавляем стили для полей дат, если они есть
        $('.admindatefilter').parent().find('input').addClass('datepicker');
    }
}); 