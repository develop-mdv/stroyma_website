(() => {
    if (!('serviceWorker' in navigator)) return;

    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {
            // Browsing stays available when registration is unavailable.
        });
    });

    let installPrompt = null;
    const installButton = document.getElementById('pwa-install');
    const iosHint = document.getElementById('pwa-install-ios');
    const installed = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;

    window.addEventListener('beforeinstallprompt', event => {
        event.preventDefault();
        installPrompt = event;
        if (installButton && !installed()) installButton.hidden = false;
    });

    if (installButton) installButton.addEventListener('click', async () => {
        if (!installPrompt) return;
        installButton.hidden = true;
        const prompt = installPrompt;
        installPrompt = null;
        await prompt.prompt();
        await prompt.userChoice;
    });

    window.addEventListener('appinstalled', () => {
        installPrompt = null;
        if (installButton) installButton.hidden = true;
        if (iosHint) iosHint.hidden = true;
    });

    if (iosHint && /iPad|iPhone|iPod/.test(navigator.userAgent) && !installed()) iosHint.hidden = false;

    const offlineNotice = document.createElement('div');
    offlineNotice.className = 'pwa-offline-notice';
    offlineNotice.setAttribute('role', 'status');
    offlineNotice.textContent = 'Нет сети. Доступны ранее открытые страницы; корзина и отправка форм требуют подключения.';
    offlineNotice.hidden = true;
    document.body.append(offlineNotice);
    const updateConnection = () => { offlineNotice.hidden = navigator.onLine; };
    window.addEventListener('online', updateConnection);
    window.addEventListener('offline', updateConnection);
    updateConnection();
})();
