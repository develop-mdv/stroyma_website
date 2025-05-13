// Ждем загрузки документа и проверяем наличие django.jQuery
document.addEventListener('DOMContentLoaded', function() {
  // Проверяем наличие django.jQuery
  if (typeof django !== 'undefined' && typeof django.jQuery !== 'undefined') {
    // Выполняем код только если django.jQuery доступен
    (function($) {
      'use strict';
      $(".admindatefilter").each(function(){
        var form = $(this).find("form");
        if (!form.length || !form.attr('id')) {
          console.log('RangeFilter: форма не найдена или не имеет id');
          return; // Пропускаем текущий элемент, если форма не найдена или не имеет id
        }
        
        var form_id = form.attr('id').slice(0,-5);
        var qs_name = form_id+"-query-string";
        var query_string = $('#'+qs_name).val();
        var form_name = form_id+"-form";

        // Bind submit buttons
        $(this).find("input[type=select]").bind("click", function(event){
          event.preventDefault();
          var form_data = $('#'+form_name).serialize();
          var amp = query_string == "?" ? "" : "&";  // avoid leading ?& combination
          window.location = window.location.pathname + query_string + amp + form_data;
        });

        // Bind reset buttons
        $(this).find("input[type=reset]").bind("click", function(){
          window.location = window.location.pathname + query_string;
        });
      });
    })(django.jQuery);
  } else {
    console.warn('django.jQuery не найден. Скрипт rangefilter не будет работать.');
  }
}); 