// Appends extra gallery photos added through /admin (assets/galeri.json)
// after the club's baseline photos already in index.html.
(function () {
  var container = document.querySelector('#galeri .gallery');
  if (!container) return;

  fetch('assets/galeri.json?_=' + Date.now())
    .then(function (r) { return r.json(); })
    .then(function (entries) {
      if (!Array.isArray(entries)) return;
      entries.forEach(function (entry) {
        if (!entry.image) return;
        var img = document.createElement('img');
        img.src = entry.image;
        img.alt = entry.alt || '';
        container.appendChild(img);
      });
    })
    .catch(function () { /* no extra photos yet, or offline */ });
})();
