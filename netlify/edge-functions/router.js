export default async (request, context) => {
  const url = new URL(request.url);
  const host = url.hostname;

  if (host === 'neocomusmusic.com' || host === 'www.neocomusmusic.com') {
    const rewriteUrl = new URL(request.url);
    rewriteUrl.pathname = '/neocomus_website.html';
    return context.rewrite(rewriteUrl.toString());
  }
};

export const config = { path: '/*' };
