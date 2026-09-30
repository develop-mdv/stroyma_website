document.addEventListener('DOMContentLoaded', () => {
    const frame = document.getElementById('facadeConfigurator');
    const form = document.getElementById('colorRequest');
    const summary = document.getElementById('selectedFinish');
    const facade = document.getElementById('selectedFacade');
    const plinth = document.getElementById('selectedPlinth');
    const configState = document.getElementById('selectedState');
    const name = document.getElementById('requestName');
    let revealStandaloneRequest = new URLSearchParams(window.location.search).get('request') === '1';

    if (!frame || !form) return;

    const startButton = document.getElementById('startConfigurator');
    const startPanel = document.getElementById('configuratorStart');
    const start = () => {
        if (frame.getAttribute('src')) return;
        frame.src = frame.dataset.src;
        frame.hidden = false;
        if (startPanel) startPanel.hidden = true;
        frame.focus({ preventScroll: true });
    };
    startButton?.addEventListener('click', start);
    // Restore a shared selection or a submitted form immediately.
    if (new URLSearchParams(location.search).size || facade?.value) start();

    const requestWidgetState = () => {
        if (revealStandaloneRequest) {
            frame.contentWindow?.postMessage({ type: 'facade-configurator:get-state' }, window.location.origin);
        }
    };
    frame.addEventListener('load', requestWidgetState);
    requestWidgetState();

    window.addEventListener('message', (event) => {
        if (event.origin !== window.location.origin || event.source !== frame.contentWindow) return;
        const data = event.data;
        if (!data || typeof data.type !== 'string') return;

        if (data.type === 'facade-configurator:size') {
            if (data.mode === 'stacked' && Number.isFinite(data.height)) {
                frame.style.height = `${Math.max(620, Math.min(1500, data.height))}px`;
            } else if (data.mode === 'side') {
                frame.style.height = '';
            }
        } else if (data.type === 'facade-configurator:change' && data.label) {
            const facadeLabel = String(data.label.facade || '').slice(0, 160);
            const plinthLabel = String(data.label.plinth || '').slice(0, 160);
            facade.value = facadeLabel;
            plinth.value = plinthLabel;
            if (data.state && configState) configState.value = JSON.stringify(data.state);
            if (!data.initial || revealStandaloneRequest) {
                summary.textContent = `Фасад: ${facadeLabel}. Цоколь: ${plinthLabel}.`;
            }
            if (revealStandaloneRequest) {
                revealStandaloneRequest = false;
                form.scrollIntoView({ behavior: 'instant', block: 'start' });
                name.focus({ preventScroll: true });
            }
        } else if (data.type === 'facade-configurator:request') {
            form.scrollIntoView({ behavior: 'smooth', block: 'center' });
            window.setTimeout(() => name.focus({ preventScroll: true }), 300);
        } else if (data.type === 'facade-configurator:scroll' && Number.isFinite(data.dy)) {
            window.scrollBy(0, data.dy);
        }
    });
});
