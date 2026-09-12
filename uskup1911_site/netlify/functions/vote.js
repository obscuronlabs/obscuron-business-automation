const { getStore } = require('@netlify/blobs');

const VALID_KIND = new Set(['like', 'dislike']);

function openStore() {
  var siteID = process.env.NETLIFY_SITE_ID;
  var token = process.env.NETLIFY_BLOBS_TOKEN;
  if (siteID && token) {
    return getStore({ name: 'uskup1911-votes', siteID: siteID, token: token });
  }
  return getStore('uskup1911-votes');
}

exports.handler = async (event) => {
  try {
    const store = openStore();
    const params = event.httpMethod === 'GET'
      ? event.queryStringParameters || {}
      : JSON.parse(event.body || '{}');
    const track = String(params.track || '').trim();

    if (!track || !/^[a-zA-Z0-9_-]+$/.test(track)) {
      return { statusCode: 400, body: JSON.stringify({ error: 'invalid track' }) };
    }

    if (event.httpMethod === 'GET') {
      const data = (await store.get(track, { type: 'json' })) || { like: 0, dislike: 0 };
      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      };
    }

    if (event.httpMethod === 'POST') {
      const kind = String(params.kind || '');
      if (!VALID_KIND.has(kind)) {
        return { statusCode: 400, body: JSON.stringify({ error: 'invalid kind' }) };
      }
      const data = (await store.get(track, { type: 'json' })) || { like: 0, dislike: 0 };
      data[kind] = (data[kind] || 0) + 1;
      await store.setJSON(track, data);
      return {
        statusCode: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      };
    }

    return { statusCode: 405, body: JSON.stringify({ error: 'method not allowed' }) };
  } catch (err) {
    return {
      statusCode: 500,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ error: String(err && err.message || err) }),
    };
  }
};
