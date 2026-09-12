// Üsküp 1911 anthem playlist. Real tracks, in the order the club provided them.
const COVER_IMAGE = 'assets/album-kapak.jpg';
const TRACKS = [
  { id: 'track01', title: 'Zafer İnananlarındır #1', src: 'assets/audio/track01.mp3' },
  { id: 'track02', title: 'Zafer İnananlarındır #2', src: 'assets/audio/track02.mp3' },
  { id: 'track03', title: 'Zafer İnananlarındır #3', src: 'assets/audio/track03.mp3' },
  { id: 'track04', title: 'Zafer İnananlarındır #4', src: 'assets/audio/track04.mp3' },
  { id: 'track05', title: 'Zafer İnananlarındır #5', src: 'assets/audio/track05.mp3' },
  { id: 'track06', title: 'Zafer İnananlarındır #6', src: 'assets/audio/track06.mp3' },
  { id: 'track07', title: 'Zafer İnananlarındır #7', src: 'assets/audio/track07.mp3' },
  { id: 'track08', title: 'Zafer İnananlarındır #8', src: 'assets/audio/track08.mp3' },
  { id: 'track09', title: 'Zafer İnananlarındır #9', src: 'assets/audio/track09.mp3' },
  { id: 'track10', title: 'Zafer İnananlarındır #10', src: 'assets/audio/track10.mp3' }
];

(function () {
  var VOTED_KEY = 'uskup1911_voted';

  var audio = document.getElementById('audioEl');
  var playlistEl = document.getElementById('playlist');
  var playBtn = document.getElementById('playBtn');
  var prevBtn = document.getElementById('prevBtn');
  var nextBtn = document.getElementById('nextBtn');
  var seekBar = document.getElementById('seekBar');
  var nowTitle = document.getElementById('nowTitle');
  var timeDisplay = document.getElementById('timeDisplay');
  var coverEl = document.getElementById('playerCover');

  if (!audio || !playlistEl) return;

  if (coverEl) {
    coverEl.innerHTML = '';
    coverEl.textContent = '';
    var coverImg = document.createElement('img');
    coverImg.src = COVER_IMAGE;
    coverImg.alt = 'Üsküp 1911 albüm kapağı';
    coverImg.style.width = '100%';
    coverImg.style.height = '100%';
    coverImg.style.objectFit = 'cover';
    coverImg.style.borderRadius = '6px';
    coverEl.appendChild(coverImg);
  }

  var currentIndex = 0;

  function formatTime(sec) {
    if (!isFinite(sec)) return '0:00';
    var m = Math.floor(sec / 60);
    var s = Math.floor(sec % 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  function getVoted() {
    try { return JSON.parse(localStorage.getItem(VOTED_KEY) || '{}'); } catch (e) { return {}; }
  }
  function setVoted(map) {
    try { localStorage.setItem(VOTED_KEY, JSON.stringify(map)); } catch (e) {}
  }

  var VOTE_ENDPOINT = '/.netlify/functions/vote';

  function updateSummary(summaryEl, likeEl, dislikeEl) {
    var likes = parseInt(likeEl.textContent, 10) || 0;
    var dislikes = parseInt(dislikeEl.textContent, 10) || 0;
    summaryEl.textContent = likes + ' beğenildi, ' + dislikes + ' beğenilmedi';
  }

  function refreshCounts(trackId, likeEl, dislikeEl, summaryEl) {
    fetch(VOTE_ENDPOINT + '?track=' + encodeURIComponent(trackId))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        likeEl.textContent = (d && d.like) || 0;
        dislikeEl.textContent = (d && d.dislike) || 0;
        updateSummary(summaryEl, likeEl, dislikeEl);
      }).catch(function () {});
  }

  function vote(trackId, kind, likeEl, dislikeEl, likeBtn, dislikeBtn, summaryEl) {
    var voted = getVoted();
    if (voted[trackId] || likeBtn.disabled || dislikeBtn.disabled) return; // one vote per track per browser
    // disable immediately (before the network round-trip) so rapid repeat
    // clicks can't sneak in extra votes while the first request is in flight
    likeBtn.disabled = true;
    dislikeBtn.disabled = true;
    fetch(VOTE_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ track: trackId, kind: kind })
    }).then(function (r) { return r.json(); }).then(function (d) {
      likeEl.textContent = d.like || 0;
      dislikeEl.textContent = d.dislike || 0;
      updateSummary(summaryEl, likeEl, dislikeEl);
      voted[trackId] = kind;
      setVoted(voted);
      likeBtn.classList.toggle('active', kind === 'like');
      dislikeBtn.classList.toggle('active', kind === 'dislike');
    }).catch(function () {
      // request failed - re-enable so the visitor can try again
      likeBtn.disabled = false;
      dislikeBtn.disabled = false;
    });
  }

  function shareTrack(track) {
    var url = 'https://uskup1911.com/#muzik';
    var text = 'Üsküp 1911 - ' + track.title + ' şarkısını dinle: ' + url;
    if (navigator.share) {
      navigator.share({ title: track.title, text: 'Üsküp 1911 - ' + track.title, url: url }).catch(function () {});
    } else {
      window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank', 'noopener');
    }
  }

  function loadTrack(index, autoplay) {
    currentIndex = (index + TRACKS.length) % TRACKS.length;
    var track = TRACKS[currentIndex];
    audio.src = track.src;
    nowTitle.textContent = track.title;
    document.querySelectorAll('.track').forEach(function (li, i) {
      li.classList.toggle('playing', i === currentIndex);
    });
    if (autoplay) {
      audio.play().catch(function () { /* autoplay blocked, wait for user gesture */ });
    }
  }

  function renderPlaylist() {
    var voted = getVoted();
    TRACKS.forEach(function (track, i) {
      var li = document.createElement('li');
      li.className = 'track';
      li.dataset.index = i;

      var playBtnEl = document.createElement('button');
      playBtnEl.className = 'trackPlay';
      playBtnEl.setAttribute('aria-label', 'Çal');
      playBtnEl.textContent = '▶';
      playBtnEl.addEventListener('click', function () { loadTrack(i, true); updatePlayIcon(); });

      var titleEl = document.createElement('span');
      titleEl.className = 'trackTitle';
      titleEl.textContent = track.title;

      var votesEl = document.createElement('span');
      votesEl.className = 'trackVotes';

      var likeCount = document.createElement('span');
      likeCount.className = 'voteCount';
      likeCount.textContent = '0';
      var dislikeCount = document.createElement('span');
      dislikeCount.className = 'voteCount';
      dislikeCount.textContent = '0';

      var likeBtn = document.createElement('button');
      likeBtn.className = 'voteBtn like';
      likeBtn.innerHTML = '👍 ';
      likeBtn.appendChild(likeCount);
      var dislikeBtn = document.createElement('button');
      dislikeBtn.className = 'voteBtn dislike';
      dislikeBtn.innerHTML = '👎 ';
      dislikeBtn.appendChild(dislikeCount);

      if (voted[track.id]) {
        likeBtn.disabled = true;
        dislikeBtn.disabled = true;
        likeBtn.classList.toggle('active', voted[track.id] === 'like');
        dislikeBtn.classList.toggle('active', voted[track.id] === 'dislike');
      }

      var summaryEl = document.createElement('span');
      summaryEl.className = 'trackVoteSummary';
      summaryEl.textContent = '0 beğenildi, 0 beğenilmedi';

      likeBtn.addEventListener('click', function () { vote(track.id, 'like', likeCount, dislikeCount, likeBtn, dislikeBtn, summaryEl); });
      dislikeBtn.addEventListener('click', function () { vote(track.id, 'dislike', likeCount, dislikeCount, likeBtn, dislikeBtn, summaryEl); });

      var shareBtn = document.createElement('button');
      shareBtn.className = 'trackShare';
      shareBtn.setAttribute('aria-label', 'Paylaş');
      shareBtn.textContent = '↗ Paylaş';
      shareBtn.addEventListener('click', function () { shareTrack(track); });

      votesEl.appendChild(likeBtn);
      votesEl.appendChild(dislikeBtn);
      votesEl.appendChild(summaryEl);
      votesEl.appendChild(shareBtn);

      li.appendChild(playBtnEl);
      li.appendChild(titleEl);
      li.appendChild(votesEl);
      playlistEl.appendChild(li);

      refreshCounts(track.id, likeCount, dislikeCount, summaryEl);
    });
  }

  function updatePlayIcon() {
    playBtn.textContent = audio.paused ? '▶' : '⏸';
  }

  playBtn.addEventListener('click', function () {
    if (audio.paused) { audio.play().catch(function () {}); } else { audio.pause(); }
  });
  prevBtn.addEventListener('click', function () { loadTrack(currentIndex - 1, true); });
  nextBtn.addEventListener('click', function () { loadTrack(currentIndex + 1, true); });

  audio.addEventListener('play', updatePlayIcon);
  audio.addEventListener('pause', updatePlayIcon);
  audio.addEventListener('ended', function () { loadTrack(currentIndex + 1, true); });
  audio.addEventListener('timeupdate', function () {
    if (audio.duration) seekBar.value = (audio.currentTime / audio.duration) * 100;
    timeDisplay.textContent = formatTime(audio.currentTime) + ' / ' + formatTime(audio.duration);
  });
  seekBar.addEventListener('input', function () {
    if (audio.duration) audio.currentTime = (seekBar.value / 100) * audio.duration;
  });

  renderPlaylist();
  loadTrack(0, false);

  // Try to autoplay on load; if the browser blocks it (no user gesture yet),
  // start on the first click/tap/key anywhere on the page instead.
  function tryAutoplay() {
    var p = audio.play();
    if (p && typeof p.catch === 'function') {
      p.catch(function () {
        var start = function () {
          audio.play().catch(function () {});
          document.removeEventListener('click', start);
          document.removeEventListener('keydown', start);
          document.removeEventListener('touchstart', start);
        };
        document.addEventListener('click', start, { once: true });
        document.addEventListener('keydown', start, { once: true });
        document.addEventListener('touchstart', start, { once: true });
      });
    }
  }
  tryAutoplay();
})();
