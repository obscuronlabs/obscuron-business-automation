// Replaces the static İletişim cards with whatever is set through /admin
// (Decap CMS writes content/iletisim/*.json, the build flattens them into
// assets/iletisim.json). If the fetch fails or returns nothing, the static
// markup already in index.html stays exactly as it is.
(function () {
  var container = document.querySelector('#iletisim .contact');
  if (!container) return;

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function link(href, text) {
    var a = document.createElement('a');
    a.href = href;
    a.textContent = text;
    if (/^https?:\/\//.test(href)) {
      a.target = '_blank';
      a.rel = 'noopener';
    }
    return a;
  }

  function buildCard(entry) {
    var article = document.createElement('article');

    if (entry.avatar) {
      var img = document.createElement('img');
      img.className = 'avatar';
      img.src = entry.avatar;
      img.alt = entry.name || '';
      article.appendChild(img);
    }

    article.appendChild(el('h3', null, entry.name || ''));

    if (entry.role) {
      var role = el('p');
      entry.role.split('\n').forEach(function (line, i) {
        if (i > 0) role.appendChild(document.createElement('br'));
        role.appendChild(document.createTextNode(line));
      });
      article.appendChild(role);
    }

    if (entry.whatsapp) {
      article.appendChild(link('https://wa.me/' + entry.whatsapp, 'WhatsApp: +' + entry.whatsapp));
    }
    if (entry.email) {
      article.appendChild(link('mailto:' + entry.email, entry.email));
    }
    if (Array.isArray(entry.extra_links)) {
      entry.extra_links.forEach(function (l) {
        if (l && l.url && l.label) article.appendChild(link(l.url, l.label));
      });
    }
    if (entry.note_prefix || entry.note_link_label) {
      var note = el('span', 'techCredit');
      if (entry.note_prefix) note.appendChild(document.createTextNode(entry.note_prefix + ' '));
      if (entry.note_link_label && entry.note_url) {
        note.appendChild(link(entry.note_url, entry.note_link_label));
      } else if (entry.note_link_label) {
        note.appendChild(document.createTextNode(entry.note_link_label));
      }
      article.appendChild(note);
    }

    return article;
  }

  fetch('assets/iletisim.json?_=' + Date.now())
    .then(function (r) { return r.json(); })
    .then(function (entries) {
      if (!Array.isArray(entries) || entries.length === 0) return;
      container.innerHTML = '';
      entries.forEach(function (entry) { container.appendChild(buildCard(entry)); });
    })
    .catch(function () { /* keep the static cards already in the page */ });
})();
