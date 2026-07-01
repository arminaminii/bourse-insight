/**
 * Bourse Insight — Main JS
 */

/* ── Toast Notification ── */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `bi-toast ${type}`;
    toast.innerHTML = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(-20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/* ── Scroll Reveal Animation ── */
function initScrollReveal() {
    const elements = document.querySelectorAll(
        '.bi-company-card, .bi-sector-card, .bi-stat-card, .bi-report-card, .bi-info-card'
    );
    if (!elements.length) return;

    elements.forEach((el, i) => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(15px)';
        el.style.transition = `opacity 0.4s ease ${i * 0.03}s, transform 0.4s ease ${i * 0.03}s`;
    });

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    elements.forEach(el => observer.observe(el));
}

/* ── Loading State ── */
function showLoading() {
    const overlay = document.createElement('div');
    overlay.id = 'bi-loading';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(10,14,23,0.7);z-index:9998;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
    overlay.innerHTML = '<div style="text-align:center;"><div style="width:40px;height:40px;border:3px solid #1e1e3a;border-top-color:#00ff88;border-radius:50%;animation:bi-spin 0.8s linear infinite;margin:0 auto 1rem;"></div><p style="color:#8892a4;font-size:0.9rem;">در حال دریافت از Codal.ir...</p></div>';
    const style = document.createElement('style');
    style.textContent = '@keyframes bi-spin{to{transform:rotate(360deg)}}';
    document.head.appendChild(style);
    document.body.appendChild(overlay);
}

function hideLoading() {
    const el = document.getElementById('bi-loading');
    if (el) el.remove();
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
    initScrollReveal();

    // Show loading on search form submit
    document.querySelectorAll('form[action="/search/"], form[action="/reports/"]').forEach(form => {
        form.addEventListener('submit', () => {
            const q = form.querySelector('input[name="q"]');
            if (q && q.value.trim()) {
                showLoading();
            }
        });
    });
});