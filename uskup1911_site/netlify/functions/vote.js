const { getStore } = require('@netlify/blobs');

const VALID_KIND = new Set(['like', 'dislike']);

exports.handler = async (event) => {
  const store = getStore('uskup1911-votes');
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
};
