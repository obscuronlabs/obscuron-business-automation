// Reads content/iletisim/*.json (one file per contact card, managed via /admin CMS)
// and writes assets/iletisim.json — the feed contact.js fetches at runtime.
const fs = require('fs');
const path = require('path');

const SRC_DIR = path.join(__dirname, '..', 'content', 'iletisim');
const OUT_FILE = path.join(__dirname, '..', 'assets', 'iletisim.json');

function readEntries() {
  if (!fs.existsSync(SRC_DIR)) return [];
  return fs.readdirSync(SRC_DIR)
    .filter((f) => f.endsWith('.json'))
    .map((f) => {
      try {
        return JSON.parse(fs.readFileSync(path.join(SRC_DIR, f), 'utf8'));
      } catch (e) {
        console.warn('iletisim: skipping unreadable entry', f, e.message);
        return null;
      }
    })
    .filter((entry) => entry && entry.name)
    .sort((a, b) => (a.order || 0) - (b.order || 0));
}

const entries = readEntries();
fs.writeFileSync(OUT_FILE, JSON.stringify(entries, null, 2));
console.log('iletisim: wrote', entries.length, 'entries to', OUT_FILE);
