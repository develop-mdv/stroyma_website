/* Sales report charts without third-party scripts. */
document.addEventListener('DOMContentLoaded', () => {
    const report = document.querySelector('.sales-report-container');
    if (!report) return;

    const period = report.querySelector('.period-filters');
    const days = period?.dataset.initialDays || '30';
    const money = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });

    period?.querySelectorAll('.period-btn').forEach(button => {
        button.addEventListener('click', () => {
            const target = new URL(window.location.href);
            target.searchParams.set('days', button.dataset.days);
            window.location.assign(target.href);
        });
    });

    function empty(container, message) {
        const note = document.createElement('p');
        note.className = 'sm-chart-empty';
        note.textContent = message;
        container.replaceChildren(note);
    }

    function svgElement(name, attributes = {}) {
        const element = document.createElementNS('http://www.w3.org/2000/svg', name);
        Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
        return element;
    }

    function renderSales(data) {
        const container = document.getElementById('salesChart');
        if (!container) return;
        const labels = Array.isArray(data.dates) ? data.dates : [];
        const values = Array.isArray(data.sales) ? data.sales.map(Number) : [];
        if (!labels.length || labels.length !== values.length) {
            empty(container, 'Нет данных за выбранный период');
            return;
        }

        const width = 680;
        const height = 220;
        const left = 54;
        const right = 20;
        const top = 18;
        const bottom = 34;
        const plotWidth = width - left - right;
        const plotHeight = height - top - bottom;
        const maximum = Math.max(1, ...values);
        const point = (value, index) => [
            left + (labels.length === 1 ? plotWidth / 2 : index * plotWidth / (labels.length - 1)),
            top + plotHeight - (value / maximum) * plotHeight,
        ];
        const svg = svgElement('svg', {
            viewBox: `0 0 ${width} ${height}`,
            role: 'img',
            'aria-label': 'Динамика выручки за выбранный период',
            preserveAspectRatio: 'xMidYMid meet',
        });

        for (let step = 0; step <= 4; step += 1) {
            const y = top + plotHeight * step / 4;
            svg.appendChild(svgElement('line', {
                x1: left, y1: y, x2: width - right, y2: y,
                stroke: 'rgba(148,163,184,.22)', 'stroke-width': 1,
            }));
            const label = svgElement('text', {
                x: left - 8, y: y + 4, 'text-anchor': 'end',
                fill: 'currentColor', 'font-size': 10,
            });
            label.textContent = money.format(maximum * (1 - step / 4));
            svg.appendChild(label);
        }

        const coordinates = values.map(point);
        const fill = svgElement('polygon', {
            points: [
                `${left},${top + plotHeight}`,
                ...coordinates.map(([x, y]) => `${x},${y}`),
                `${width - right},${top + plotHeight}`,
            ].join(' '),
            fill: 'rgba(59,166,232,.13)',
        });
        svg.appendChild(fill);
        svg.appendChild(svgElement('polyline', {
            points: coordinates.map(([x, y]) => `${x},${y}`).join(' '),
            fill: 'none', stroke: '#3ba6e8', 'stroke-width': 3,
            'stroke-linecap': 'round', 'stroke-linejoin': 'round',
        }));

        const labelStep = Math.max(1, Math.ceil(labels.length / 6));
        labels.forEach((label, index) => {
            const [x, y] = coordinates[index];
            const circle = svgElement('circle', {
                cx: x, cy: y, r: values[index] ? 4 : 2,
                fill: '#3ba6e8', stroke: '#fff', 'stroke-width': values[index] ? 1 : 0,
            });
            const tooltip = svgElement('title');
            tooltip.textContent = `${label}: ${money.format(values[index])} ₽, заказов: ${data.counts?.[index] || 0}`;
            circle.appendChild(tooltip);
            svg.appendChild(circle);
            if (index % labelStep === 0 || index === labels.length - 1) {
                const date = svgElement('text', {
                    x, y: height - 9, 'text-anchor': 'middle',
                    fill: 'currentColor', 'font-size': 10,
                });
                date.textContent = label;
                svg.appendChild(date);
            }
        });
        container.replaceChildren(svg);
    }

    function renderBars(id, labels, values, suffix) {
        const container = document.getElementById(id);
        if (!container) return;
        if (!labels.length || !values.some(value => Number(value) > 0)) {
            empty(container, 'Нет данных за выбранный период');
            return;
        }
        const maximum = Math.max(1, ...values.map(Number));
        const list = document.createElement('div');
        list.className = 'sm-report-bars';
        labels.forEach((label, index) => {
            const value = Number(values[index]) || 0;
            const row = document.createElement('div');
            row.className = 'sm-report-bar-row';
            const heading = document.createElement('div');
            heading.className = 'sm-report-bar-heading';
            const name = document.createElement('span');
            name.textContent = label;
            name.title = label;
            const total = document.createElement('strong');
            total.textContent = `${money.format(value)}${suffix}`;
            heading.append(name, total);
            const track = document.createElement('div');
            track.className = 'sm-report-bar-track';
            const bar = document.createElement('span');
            bar.style.width = `${100 * value / maximum}%`;
            track.appendChild(bar);
            row.append(heading, track);
            list.appendChild(row);
        });
        container.replaceChildren(list);
    }

    const statusNodes = [...report.querySelectorAll('.status-data')];
    renderBars(
        'statusChart',
        statusNodes.map(node => node.dataset.status || ''),
        statusNodes.map(node => Number(node.dataset.count) || 0),
        '',
    );

    async function loadChart(url, render) {
        try {
            const response = await fetch(`${url}?days=${encodeURIComponent(days)}`, { credentials: 'same-origin' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            render(data);
        } catch (error) {
            const container = document.getElementById(url === SALES_CHART_DATA_URL ? 'salesChart' : 'productsChart');
            if (container) empty(container, 'Не удалось загрузить данные графика');
            console.error('Ошибка загрузки отчёта:', error);
        }
    }

    loadChart(SALES_CHART_DATA_URL, renderSales);
    loadChart(POPULAR_PRODUCTS_URL, data => {
        renderBars('productsChart', data.labels || [], data.quantities || [], ' шт.');
    });
});
