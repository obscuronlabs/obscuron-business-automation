// Reads content/galeri/*.json (extra gallery photos added via /admin CMS)
// and writes assets/galeri.json — gallery.js appends these after the base photos.
const fs = require('fs');
const path = require('path');

const SRC_DIR = path.join(__dirname, '..', 'content', 'galeri');
const OUT_FILE = path.join(__dirname, '..', 'assets', 'galeri.json');

function readEntries() {
  if (!fs.existsSync(SRC_DIR)) return [];
  return fs.readdirSync(SRC_DIR)
    .filter((f) => f.endsWith('.json'))
    .map((f) => {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(SRC_DIR, f), 'utf8'));
        return { image: String(data.image || ''), alt: String(data.alt || '') };
      } catch (e) {
        console.warn('galeri: skipping unreadable entry', f, e.message);
        return null;
      }
    })
    .filter((entry) => entry && entry.image);
}

const entries = readEntries();
fs.writeFileSync(OUT_FILE, JSON.stringify(entries, null, 2));
console.log('galeri: wrote', entries.length, 'entries to', OUT_FILE);
