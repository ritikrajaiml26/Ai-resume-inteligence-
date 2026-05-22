document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.querySelector('#mobile-menu-button');
  const menu = document.querySelector('#mobile-menu');
  if (toggle && menu) {
    toggle.addEventListener('click', () => {
      menu.classList.toggle('hidden');
    });
  }
});