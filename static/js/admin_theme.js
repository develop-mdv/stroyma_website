(function() {
    'use strict';

    var STORAGE_KEY = 'stroyma-theme';
    var DARK  = 'dark';
    var LIGHT = 'light';

    function getStored() {
        try { return localStorage.getItem(STORAGE_KEY); } catch(e) { return null; }
    }
    function setStored(t) {
        try { localStorage.setItem(STORAGE_KEY, t); } catch(e) {}
    }

    function updateIcon(btn, theme) {
        if (!btn) return;
        var icon = btn.querySelector('i');
        if (icon) {
            icon.className = theme === LIGHT ? 'fas fa-moon' : 'fas fa-sun';
        }
        btn.setAttribute('title', theme === LIGHT ? 'Тёмная тема' : 'Светлая тема');
        btn.setAttribute('aria-label', theme === LIGHT ? 'Переключить на тёмную тему' : 'Переключить на светлую тему');
    }

    function apply(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        updateIcon(document.getElementById('sm-theme-btn'), theme);
    }

    function toggle() {
        var current = document.documentElement.getAttribute('data-theme') || DARK;
        var next = current === DARK ? LIGHT : DARK;
        setStored(next);
        apply(next);
    }

    function injectButton() {
        var navRight = document.querySelector('#jazzy-navbar .navbar-nav.ml-auto');
        if (!navRight || document.getElementById('sm-theme-btn')) return;

        var li = document.createElement('li');
        li.className = 'nav-item';

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'sm-theme-btn';
        btn.className = 'sm-theme-toggle';
        btn.innerHTML = '<i class="fas fa-sun"></i>';
        btn.addEventListener('click', toggle);

        li.appendChild(btn);
        navRight.insertBefore(li, navRight.firstChild);

        var current = document.documentElement.getAttribute('data-theme') || DARK;
        updateIcon(btn, current);
    }

    var saved = getStored() || DARK;
    document.documentElement.setAttribute('data-theme', saved);

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            apply(saved);
            injectButton();
        });
    } else {
        apply(saved);
        injectButton();
    }
})();
