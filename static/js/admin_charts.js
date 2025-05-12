// Скрипт для отображения графиков в админ-панели
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, что мы на странице отчета и доступна библиотека Chart.js
    if (document.getElementById('salesChart') && typeof Chart !== 'undefined') {
        initCharts();
    }
});

// Инициализация всех графиков
function initCharts() {
    // Загружаем начальные данные
    loadSalesChartData(30); // По умолчанию 30 дней
    loadPopularProductsData(30);
    createStatusChart();

    // Настраиваем кнопки переключения периода
    const periodButtons = document.querySelectorAll('.period-btn');
    periodButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Делаем кнопку активной
            periodButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Загружаем данные за выбранный период
            const days = this.dataset.days;
            loadSalesChartData(days);
            loadPopularProductsData(days);
        });
    });
}

// Функция для загрузки данных графика продаж
function loadSalesChartData(days) {
    // Используем URL из переменной, определенной в шаблоне, или запасной вариант
    const url = typeof SALES_CHART_DATA_URL !== 'undefined' 
        ? `${SALES_CHART_DATA_URL}?days=${days}`
        : `/admin/products/order/sales-chart-data/?days=${days}`;
        
    fetch(url)
        .then(response => {
            if (!response.ok && response.status !== 200) {
                throw new Error(`Ошибка HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Проверяем, есть ли ошибка в ответе
            if (data.error) {
                console.error('Ошибка в данных графика продаж:', data.error, data.details);
                // Если есть пустые данные, все равно обновляем график
                if (data.labels && data.labels.length === 0) {
                    updateSalesChart({
                        labels: [],
                        sales: [],
                        counts: []
                    });
                }
                return;
            }
            updateSalesChart(data);
        })
        .catch(error => {
            console.error('Ошибка при загрузке данных графика продаж:', error);
            // В случае ошибки отображаем пустой график
            updateSalesChart({
                labels: [],
                sales: [],
                counts: []
            });
        });
}

// Функция для загрузки данных о популярных товарах
function loadPopularProductsData(days) {
    // Используем URL из переменной, определенной в шаблоне, или запасной вариант
    const url = typeof POPULAR_PRODUCTS_URL !== 'undefined' 
        ? `${POPULAR_PRODUCTS_URL}?days=${days}`
        : `/admin/products/order/popular-products/?days=${days}`;
        
    fetch(url)
        .then(response => {
            if (!response.ok && response.status !== 200) {
                throw new Error(`Ошибка HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Проверяем, есть ли ошибка в ответе
            if (data.error) {
                console.error('Ошибка в данных о популярных товарах:', data.error, data.details);
                // Если есть пустые данные, все равно обновляем график
                if (data.labels && data.labels.length === 0) {
                    updateProductsChart({
                        labels: [],
                        quantities: [],
                        sales: []
                    });
                }
                return;
            }
            updateProductsChart(data);
        })
        .catch(error => {
            console.error('Ошибка при загрузке данных о популярных товарах:', error);
            // В случае ошибки отображаем пустой график
            updateProductsChart({
                labels: [],
                quantities: [],
                sales: []
            });
        });
}

// Обновление графика продаж
let salesChart = null;
function updateSalesChart(data) {
    const ctx = document.getElementById('salesChart').getContext('2d');
    
    if (salesChart) {
        salesChart.destroy();
    }
    
    // Если данных нет, показываем сообщение
    if (!data.labels || data.labels.length === 0) {
        // Создаем график с информационным сообщением
        salesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Нет данных'],
                datasets: [
                    {
                        label: 'Продажи (₽)',
                        data: [0],
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Нет данных за выбранный период',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
        return;
    }
    
    // Градиент для фона
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(54, 162, 235, 0.2)');
    gradient.addColorStop(1, 'rgba(54, 162, 235, 0.0)');
    
    salesChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Продажи (₽)',
                    data: data.sales,
                    borderColor: 'rgba(54, 162, 235, 1)',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'white',
                    pointBorderColor: 'rgba(54, 162, 235, 1)',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                },
                {
                    label: 'Количество заказов',
                    data: data.counts,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(255, 99, 132, 0)',
                    borderWidth: 3,
                    tension: 0.4,
                    yAxisID: 'y1',
                    pointBackgroundColor: 'white',
                    pointBorderColor: 'rgba(255, 99, 132, 1)',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    title: {
                        display: true,
                        text: 'Сумма (₽)',
                        font: {
                            weight: 'bold'
                        }
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    title: {
                        display: true,
                        text: 'Количество',
                        font: {
                            weight: 'bold'
                        }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            },
            plugins: {
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#333',
                    bodyColor: '#333',
                    borderColor: '#ddd',
                    borderWidth: 1,
                    padding: 10,
                    displayColors: true,
                    boxWidth: 10,
                    boxHeight: 10,
                    boxPadding: 5,
                    usePointStyle: true
                },
                legend: {
                    position: 'top',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        },
                        usePointStyle: true
                    }
                }
            }
        }
    });
}

// Обновление графика популярных товаров
let productsChart = null;
function updateProductsChart(data) {
    const ctx = document.getElementById('productsChart').getContext('2d');
    
    if (productsChart) {
        productsChart.destroy();
    }
    
    // Если данных нет, показываем сообщение
    if (!data.labels || data.labels.length === 0) {
        // Создаем график с информационным сообщением
        productsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Нет данных'],
                datasets: [
                    {
                        label: 'Количество продаж',
                        data: [0],
                        backgroundColor: 'rgba(75, 192, 192, 0.7)',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Нет данных за выбранный период',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
        return;
    }
    
    // Подготовка данных и цветов
    const colors = [
        'rgba(75, 192, 192, 0.8)',
        'rgba(54, 162, 235, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)',
        'rgba(255, 99, 132, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(199, 199, 199, 0.8)',
        'rgba(83, 102, 255, 0.8)',
        'rgba(78, 205, 196, 0.8)',
        'rgba(232, 65, 24, 0.8)'
    ];
    
    const backgroundColors = data.labels.map((_, i) => colors[i % colors.length]);
    const borderColors = backgroundColors.map(color => color.replace('0.8', '1'));
    
    productsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Количество продаж',
                    data: data.quantities,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 2,
                    borderRadius: 5,
                    maxBarThickness: 30
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    title: {
                        display: true,
                        text: 'Количество',
                        font: {
                            weight: 'bold'
                        }
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#333',
                    bodyColor: '#333',
                    borderColor: '#ddd',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw} шт.`;
                        }
                    }
                }
            }
        }
    });
}

// График статусов заказов
function createStatusChart() {
    const statusElement = document.getElementById('statusChart');
    if (!statusElement) return;
    
    const ctx = statusElement.getContext('2d');
    const labels = [];
    const values = [];
    const statusElements = document.querySelectorAll('.status-data');
    
    statusElements.forEach(item => {
        labels.push(item.dataset.status);
        values.push(parseInt(item.dataset.count));
    });
    
    // Цвета для статусов
    const backgroundColors = [
        'rgba(255, 99, 132, 0.8)',
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)'
    ];
    
    const borderColors = backgroundColors.map(color => color.replace('0.8', '1'));
    
    // Если нет данных
    if (values.reduce((a, b) => a + b, 0) === 0) {
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Нет данных'],
                datasets: [{
                    data: [1],
                    backgroundColor: ['rgba(200, 200, 200, 0.8)'],
                    borderColor: ['rgba(200, 200, 200, 1)'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Нет данных за выбранный период',
                        font: {
                            size: 16
                        }
                    }
                }
            }
        });
        return;
    }
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: backgroundColors,
                borderColor: borderColors,
                borderWidth: 2,
                borderRadius: 5,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12
                        },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(255, 255, 255, 0.9)',
                    titleColor: '#333',
                    bodyColor: '#333',
                    borderColor: '#ddd',
                    borderWidth: 1,
                    padding: 10,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((acc, val) => acc + val, 0);
                            const percentage = Math.round((context.raw / total * 100) * 10) / 10;
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
} 