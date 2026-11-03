// Pre-paint bootstrap. External classic script (script-src 'self').
// Allowlists mo.theme and mo.density; ignores anything else.
(function () {
  try {
    var theme = null;
    try { theme = window.localStorage.getItem('mo.theme'); } catch (e) { theme = null; }
    if (theme === 'light' || theme === 'dark') {
      document.documentElement.setAttribute('data-theme', theme);
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    var density = null;
    try { density = window.localStorage.getItem('mo.density'); } catch (e) { density = null; }
    document.documentElement.setAttribute('data-density', density === 'comfortable' ? 'comfortable' : 'compact');
  } catch (e) {
    document.documentElement.setAttribute('data-density', 'compact');
    document.documentElement.removeAttribute('data-theme');
  }
})();
