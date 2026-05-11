document.addEventListener('DOMContentLoaded', function () {
  if (typeof GLightbox === 'undefined') return;

  GLightbox({
    selector: '.glightbox',
    touchNavigation: true,
    loop: true,
    closeOnOutsideClick: true,
    openEffect: 'zoom',
    closeEffect: 'fade',
    cssEf498: 'fade',
    skin: 'clean',
  });
});
