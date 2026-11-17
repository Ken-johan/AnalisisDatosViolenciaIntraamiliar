// sidebar.js – Navegación dinámica y fluida del Dashboard
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const menuToggle = document.getElementById('menuToggle');
  const links = document.querySelectorAll('.sidebar-nav .nav-link');

  // Crear backdrop overlay para móviles
  let overlay = document.querySelector('.sidebar-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.className = 'sidebar-overlay';
    document.body.appendChild(overlay);
  }

  // Toggle móvil
  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('show');
    });
  }

  if (overlay) {
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('show');
    });
  }

  // Navegación fluida y activación contextual
  links.forEach(link => {
    link.addEventListener('click', e => {
      const targetId = link.getAttribute('href');
      if (targetId && targetId.startsWith('#')) {
        e.preventDefault();
        const targetSection = document.querySelector(targetId);
        if (targetSection) {
          // Desactivar otros enlaces
          links.forEach(l => l.classList.remove('active'));
          link.classList.add('active');

          // Cerrar sidebar en móvil si está abierto
          sidebar.classList.remove('open');
          overlay.classList.remove('show');

          // Desplazamiento suave con offset del topbar
          const topbarHeight = 70;
          const sectionTop = targetSection.getBoundingClientRect().top + window.pageYOffset - topbarHeight;
          window.scrollTo({
            top: sectionTop,
            behavior: 'smooth'
          });
        }
      }
    });
  });

  // Detección contextual por scroll (IntersectionObserver)
  const sections = document.querySelectorAll('section.section-block[id]');
  if ('IntersectionObserver' in window && sections.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const currentId = '#' + entry.target.id;
          links.forEach(link => {
            if (link.getAttribute('href') === currentId) {
              link.classList.add('active');
            } else {
              link.classList.remove('active');
            }
          });
        }
      });
    }, {
      rootMargin: '-20% 0px -70% 0px',
      threshold: 0
    });

    sections.forEach(s => observer.observe(s));
  }
});
