/**
 * Автоматическое формирование slug поля при вводе названия
 */
django.jQuery(function($) {
    // Функция для создания slug из строки
    function slugify(str) {
        if (!str) return '';
        
        str = str.toString().toLowerCase();
        
        // Заменяем кириллицу на латиницу
        var translitMap = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        };
        
        var result = '';
        for (var i = 0; i < str.length; i++) {
            var char = str[i];
            result += translitMap[char] || char;
        }
        
        // Удаляем спецсимволы
        result = result.replace(/[^\w\s-]/g, '');
        // Заменяем пробелы на дефисы
        result = result.replace(/\s+/g, '-');
        // Заменяем множественные дефисы на один
        result = result.replace(/-+/g, '-');
        // Удаляем начальные и конечные дефисы
        result = result.trim().replace(/^-+|-+$/g, '');
        
        return result;
    }

    // Обработчик для Product (form #product_form)
    if ($('#product_form').length > 0 || $('.model-product').length > 0) {
        console.log('Initializing slugify for Product');
        var nameField = $('#id_name');
        var slugField = $('#id_slug');
        
        if (nameField.length > 0 && slugField.length > 0) {
            // Только если slug поле пустое, привязываем обработчик
            if (slugField.val() === '') {
                nameField.on('keyup change input', function() {
                    slugField.val(slugify($(this).val()));
                });
                
                // Инициализация при загрузке страницы
                if (nameField.val() !== '') {
                    slugField.val(slugify(nameField.val()));
                }
            }
        } else {
            console.log('Name or slug field not found for Product');
        }
    }
    
    // Обработчик для Service (form #service_form)
    if ($('#service_form').length > 0 || $('.model-service').length > 0) {
        console.log('Initializing slugify for Service');
        var titleField = $('#id_title');
        var slugField = $('#id_slug');
        
        if (titleField.length > 0 && slugField.length > 0) {
            // Только если slug поле пустое, привязываем обработчик
            if (slugField.val() === '') {
                titleField.on('keyup change input', function() {
                    slugField.val(slugify($(this).val()));
                });
                
                // Инициализация при загрузке страницы
                if (titleField.val() !== '') {
                    slugField.val(slugify(titleField.val()));
                }
            }
        } else {
            console.log('Title or slug field not found for Service');
        }
    }
    
    // Обработчик для Category (form #category_form)
    if ($('#category_form').length > 0 || $('.model-category').length > 0) {
        console.log('Initializing slugify for Category');
        var nameField = $('#id_name');
        var slugField = $('#id_slug');
        
        if (nameField.length > 0 && slugField.length > 0) {
            // Только если slug поле пустое, привязываем обработчик
            if (slugField.val() === '') {
                nameField.on('keyup change input', function() {
                    slugField.val(slugify($(this).val()));
                });
                
                // Инициализация при загрузке страницы
                if (nameField.val() !== '') {
                    slugField.val(slugify(nameField.val()));
                }
            }
        } else {
            console.log('Name or slug field not found for Category');
        }
    }
    
    // Добавим общий хендлер для всех форм
    console.log('Adding generic handler for any form with slug field');
    $(document).ready(function() {
        // Для любой формы с полем slug
        var slugField = $('#id_slug');
        if (slugField.length > 0 && slugField.val() === '') {
            // Найдём поле для названия/заголовка (обычно это первое текстовое поле)
            var nameFields = $('input[type="text"]').not('#id_slug');
            if (nameFields.length > 0) {
                var nameField = nameFields.first();
                console.log('Found name field:', nameField.attr('id'));
                
                nameField.on('keyup change input', function() {
                    slugField.val(slugify($(this).val()));
                });
                
                // Инициализация при загрузке страницы
                if (nameField.val() !== '') {
                    slugField.val(slugify(nameField.val()));
                }
            }
        }
    });
}); 