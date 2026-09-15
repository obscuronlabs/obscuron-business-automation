export default async (request, context) => {
  const url = new URL(request.url);
  const host = url.hostname;

  if (host === 'neocomusmusic.com' || host === 'www.neocomusmusic.com') {
    return context.rewrite('/neocomus_website.html');
  }
};
