// sidebar.js – carga dinámica de los módulos del dashboard
document.addEventListener('DOMContentLoaded', () => {
  const mainPanel = document.getElementById('main-panel');
  const links = document.querySelectorAll('.sidebar a[data-endpoint]');

  const load = async endpoint => {
    mainPanel.innerHTML = '<div class="loading">Cargando…</div>';
    try {
      const resp = await fetch(endpoint);
      if (!resp.ok) throw new Error(`Error ${resp.status}`);
      const html = await resp.text();
      mainPanel.innerHTML = html;
    } catch (e) {
      mainPanel.innerHTML = `<div class="error">${e.message}</div>`;
    }
  };

  // Cargar descriptivo por defecto al iniciar
  load('/descriptivo/');

  links.forEach(link => {
    link.addEventListener('click', ev => {
      ev.preventDefault();
      const ep = link.dataset.endpoint;
      if (ep) load(ep);
    });
  });
});
