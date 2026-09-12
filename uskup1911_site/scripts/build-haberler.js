// Reads content/haberler/*.json (one file per news item, managed via /admin CMS)
// and writes assets/haberler.json — the aggregated feed news.js fetches at runtime.
// Runs as the Netlify build command, so it must not fail when there's no content yet.
const fs = require('fs');
const path = require('path');

const SRC_DIR = path.join(__dirname, '..', 'content', 'haberler');
const OUT_FILE = path.join(__dirname, '..', 'assets', 'haberler.json');

function readEntries() {
  if (!fs.existsSync(SRC_DIR)) return [];
  return fs.readdirSync(SRC_DIR)
    .filter((f) => f.endsWith('.json'))
    .map((f) => {
      try {
        const raw = fs.readFileSync(path.join(SRC_DIR, f), 'utf8');
        const data = JSON.parse(raw);
        return {
          title: String(data.title || ''),
          date: String(data.date || ''),
          image: data.image ? String(data.image) : '',
          body: String(data.body || ''),
        };
      } catch (e) {
        console.warn('haberler: skipping unreadable entry', f, e.message);
        return null;
      }
    })
    .filter((entry) => entry && entry.title)
    .sort((a, b) => (b.date || '').localeCompare(a.date || ''));
}

const entries = readEntries();
fs.writeFileSync(OUT_FILE, JSON.stringify(entries, null, 2));
console.log('haberler: wrote', entries.length, 'entries to', OUT_FILE);
