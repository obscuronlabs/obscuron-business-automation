// Renders club news posted through /admin (Decap CMS writes JSON files under
// content/haberler/, the Netlify build flattens them into assets/haberler.json).
(function () {
  var container = document.getElementById('newsPosts');
  if (!container) return;

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('tr-TR', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  fetch('assets/haberler.json?_=' + Date.now())
    .then(function (r) { return r.json(); })
    .then(function (posts) {
      if (!Array.isArray(posts) || posts.length === 0) return;
      posts.forEach(function (post) {
        var article = document.createElement('article');
        article.className = 'newsPost';

        if (post.image) {
          var img = document.createElement('img');
          img.src = post.image;
          img.alt = post.title || '';
          article.appendChild(img);
        }

        var body = document.createElement('div');
        body.className = 'newsPostBody';

        var title = document.createElement('h3');
        title.textContent = post.title || '';
        body.appendChild(title);

        if (post.date) {
          var date = document.createElement('time');
          date.textContent = formatDate(post.date);
          body.appendChild(date);
        }

        if (post.body) {
          var text = document.createElement('p');
          text.innerHTML = escapeHtml(post.body).replace(/\n/g, '<br>');
          body.appendChild(text);
        }

        article.appendChild(body);
        container.appendChild(article);
      });
    })
    .catch(function () { /* no news yet, or offline — section stays quiet */ });
})();
