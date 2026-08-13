(() => {
  const html = document.documentElement;
  const button = document.getElementById('themeToggle');
  const saved = localStorage.getItem('theme') || 'light';
  html.setAttribute('data-bs-theme', saved);
  updateIcon(saved);

  button?.addEventListener('click', () => {
    const current = html.getAttribute('data-bs-theme') || 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-bs-theme', next);
    localStorage.setItem('theme', next);
    updateIcon(next);
  });

  function updateIcon(theme) {
    if (!button) return;
    button.innerHTML = theme === 'dark' ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
  }
})();
