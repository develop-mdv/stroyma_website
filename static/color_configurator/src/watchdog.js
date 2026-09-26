(function () {
  let error = '';

  addEventListener('error', (event) => {
    error = event.target && event.target.src
      ? 'не загрузился файл: ' + String(event.target.src).split('/').pop()
      : (event.message || 'ошибка') + ' ('
        + String(event.filename || '').split('/').pop() + ':' + (event.lineno || '?') + ')';
  }, true);

  addEventListener('unhandledrejection', (event) => {
    error = 'promise: ' + ((event.reason && (event.reason.message || event.reason)) || 'ошибка');
  });

  setTimeout(() => {
    if (window.__cfgReady) return;
    const loader = document.getElementById('loader');
    if (!loader) return;

    const modules = 'noModule' in document.createElement('script');
    let webgl = false;
    try { webgl = !!document.createElement('canvas').getContext('webgl2'); } catch (_) { /* нет WebGL */ }

    const message = document.createElement('div');
    message.style.cssText = 'max-width:32ch;text-align:center;line-height:1.6';
    const title = document.createElement('b');
    title.style.color = '#eef1f5';
    title.textContent = '3D-виджет не запустился';
    const diagnostics = document.createElement('span');
    diagnostics.style.opacity = '.65';
    diagnostics.textContent = `модули: ${modules ? 'да' : 'нет'} · WebGL2: ${webgl ? 'да' : 'нет'}`;
    message.append(title, document.createElement('br'), document.createTextNode(error || 'модуль не стартовал'),
      document.createElement('br'), diagnostics);
    loader.replaceChildren(message);
  }, 8000);
})();
