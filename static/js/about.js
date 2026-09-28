(() => {
    const page = document.querySelector('.about-page');
    if (!page || !('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const items = [...page.querySelectorAll('.about-reveal')];
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
        });
    }, { threshold: 0.08, rootMargin: '0px 0px 40px 0px' });

    items.forEach((item) => {
        if (item.getBoundingClientRect().top < window.innerHeight) item.classList.add('is-visible');
        observer.observe(item);
    });
    page.classList.add('is-motion-ready');
})();
