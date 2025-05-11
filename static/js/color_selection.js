document.addEventListener('DOMContentLoaded', function() {
    let selectedFacadeColor = null;
    let selectedBaseTexture = null;

    // Обработчик для цветов фасада
    document.querySelectorAll('.color-swatch').forEach(swatch => {
        swatch.addEventListener('click', function() {
            const color = this.dataset.color;
            const target = this.dataset.target;

            // Обновление наложения фасада
            document.querySelector(`.${target}-overlay`).style.backgroundColor = color;

            // Удаление класса 'selected' у всех образцов фасада
            document.querySelectorAll(`.color-swatch[data-target="${target}"]`).forEach(s => s.classList.remove('selected'));

            // Добавление класса 'selected' к текущему образцу
            this.classList.add('selected');

            // Сохранение выбранного цвета
            selectedFacadeColor = color;
        });
    });

    // Обработчик для текстур цоколя
    document.querySelectorAll('.texture-swatch').forEach(swatch => {
        swatch.addEventListener('click', function() {
            const image = this.dataset.image;
            const target = this.dataset.target;

            // Обновление наложения цоколя
            document.querySelector(`.${target}-overlay`).style.background = `url('${image}')`;

            // Удаление класса 'selected' у всех текстур цоколя
            document.querySelectorAll(`.texture-swatch[data-target="${target}"]`).forEach(s => s.classList.remove('selected'));

            // Добавление класса 'selected' к текущему образцу
            this.classList.add('selected');

            // Сохранение выбранной текстуры
            selectedBaseTexture = image;
        });
    });
});