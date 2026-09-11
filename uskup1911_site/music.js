// Üsküp 1911 anthem playlist.
// Placeholder entries — swap `src` for the real files under assets/audio/
// once they're available, and update `title` to the real song names.
const TRACKS = [
  { id: 'track01', title: 'Şarkı 1', src: 'assets/audio/track01.mp3' },
  { id: 'track02', title: 'Şarkı 2', src: 'assets/audio/track02.mp3' },
  { id: 'track03', title: 'Şarkı 3', src: 'assets/audio/track03.mp3' },
  { id: 'track04', title: 'Şarkı 4', src: 'assets/audio/track04.mp3' },
  { id: 'track05', title: 'Şarkı 5', src: 'assets/audio/track05.mp3' },
  { id: 'track06', title: 'Şarkı 6', src: 'assets/audio/track06.mp3' },
  { id: 'track07', title: 'Şarkı 7', src: 'assets/audio/track07.mp3' },
  { id: 'track08', title: 'Şarkı 8', src: 'assets/audio/track08.mp3' },
  { id: 'track09', title: 'Şarkı 9', src: 'assets/audio/track09.mp3' },
  { id: 'track10', title: 'Şarkı 10', src: 'assets/audio/track10.mp3' }
];

(function () {
  var NAMESPACE = 'uskup1911-anthems';
  var VOTED_KEY = 'uskup1911_voted';

  var audio = document.getElementById('audioEl');
  var playlistEl = document.getElementById('playlist');
  var playBtn = document.getElementById('playBtn');
  var prevBtn = document.getElementById('prevBtn');
  var nextBtn = document.getElementById('nextBtn');
  var seekBar = document.getElementById('seekBar');
  var nowTitle = document.getElementById('nowTitle');
  var timeDisplay = document.getElementById('timeDisplay');

  if (!audio || !playlistEl) return;

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

  function countApiUrl(action, key) {
    return 'https://api.countapi.xyz/' + action + '/' + NAMESPACE + '/' + key;
  }

  function refreshCounts(trackId, likeEl, dislikeEl) {
    fetch(countApiUrl('get', trackId + '_like')).then(function (r) { return r.json(); }).then(function (d) {
      likeEl.textContent = d && typeof d.value === 'number' ? d.value : 0;
    }).catch(function () {});
    fetch(countApiUrl('get', trackId + '_dislike')).then(function (r) { return r.json(); }).then(function (d) {
      dislikeEl.textContent = d && typeof d.value === 'number' ? d.value : 0;
    }).catch(function () {});
  }

  function vote(trackId, kind, likeEl, dislikeEl, likeBtn, dislikeBtn) {
    var voted = getVoted();
    if (voted[trackId]) return; // one vote per track per browser
    fetch(countApiUrl('hit', trackId + '_' + kind)).then(function (r) { return r.json(); }).then(function (d) {
      if (kind === 'like') likeEl.textContent = d.value; else dislikeEl.textContent = d.value;
      voted[trackId] = kind;
      setVoted(voted);
      likeBtn.classList.toggle('active', kind === 'like');
      dislikeBtn.classList.toggle('active', kind === 'dislike');
      likeBtn.disabled = true;
      dislikeBtn.disabled = true;
    }).catch(function () {});
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

      likeBtn.addEventListener('click', function () { vote(track.id, 'like', likeCount, dislikeCount, likeBtn, dislikeBtn); });
      dislikeBtn.addEventListener('click', function () { vote(track.id, 'dislike', likeCount, dislikeCount, likeBtn, dislikeBtn); });

      votesEl.appendChild(likeBtn);
      votesEl.appendChild(dislikeBtn);

      li.appendChild(playBtnEl);
      li.appendChild(titleEl);
      li.appendChild(votesEl);
      playlistEl.appendChild(li);

      refreshCounts(track.id, likeCount, dislikeCount);
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
