(function () {
  var SITE_URL = 'https://uskup1911.com';
  var PDF_URL = SITE_URL + '/assets/brosur/uskup1911-brosur.pdf';
  var SHARE_TEXT = 'Üsküp 1911 Spor Kulübü sponsorluk broşürümüzü inceleyin: ' + PDF_URL;

  var waLink = document.getElementById('brosurWhatsapp');
  var mailLink = document.getElementById('brosurEmail');
  var shareBtn = document.getElementById('brosurShare');

  if (waLink) {
    waLink.href = 'https://wa.me/?text=' + encodeURIComponent(SHARE_TEXT);
  }
  if (mailLink) {
    var subject = encodeURIComponent('Üsküp 1911 Sponsorluk Broşürü');
    var body = encodeURIComponent(
      'Merhaba,\n\nÜsküp 1911 Spor Kulübü sponsorluk broşürümüzü incelemenizi rica ederiz:\n' +
      PDF_URL + '\n\nSaygılarımızla,\nÜsküp 1911 Spor Kulübü'
    );
    mailLink.href = 'mailto:?subject=' + subject + '&body=' + body;
  }
  if (shareBtn && navigator.share) {
    shareBtn.hidden = false;
    shareBtn.addEventListener('click', function () {
      navigator.share({
        title: 'Üsküp 1911 Sponsorluk Broşürü',
        text: SHARE_TEXT,
        url: PDF_URL
      }).catch(function () {});
    });
  }

  var gallery = document.getElementById('brosurGallery');
  var lightbox = document.getElementById('brosurLightbox');
  if (!gallery || !lightbox) return;

  var lightboxImg = document.getElementById('brosurLightboxImg');
  var closeBtn = document.getElementById('brosurLightboxClose');
  var prevBtn = document.getElementById('brosurLightboxPrev');
  var nextBtn = document.getElementById('brosurLightboxNext');
  var pages = Array.prototype.slice.call(gallery.querySelectorAll('img'));
  var currentIndex = 0;

  function openLightbox(index) {
    currentIndex = (index + pages.length) % pages.length;
    lightboxImg.src = pages[currentIndex].getAttribute('data-full');
    lightboxImg.alt = pages[currentIndex].alt;
    lightbox.hidden = false;
  }
  function closeLightbox() {
    lightbox.hidden = true;
    lightboxImg.src = '';
  }

  pages.forEach(function (img, i) {
    img.addEventListener('click', function () { openLightbox(i); });
  });
  closeBtn.addEventListener('click', closeLightbox);
  prevBtn.addEventListener('click', function () { openLightbox(currentIndex - 1); });
  nextBtn.addEventListener('click', function () { openLightbox(currentIndex + 1); });
  lightbox.addEventListener('click', function (e) {
    if (e.target === lightbox) closeLightbox();
  });
  document.addEventListener('keydown', function (e) {
    if (lightbox.hidden) return;
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') openLightbox(currentIndex - 1);
    if (e.key === 'ArrowRight') openLightbox(currentIndex + 1);
  });
})();
