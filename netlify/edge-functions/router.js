export default async (request, context) => {
  const url = new URL(request.url);
  const host = url.hostname;

  if (host === 'neocomusmusic.com' || host === 'www.neocomusmusic.com') {
    const path = url.pathname;

    // Pass through all real static files — only rewrite navigation to the app shell
    const isStaticFile = path.match(/\.(html|mp4|mp3|jpg|jpeg|png|gif|webp|svg|ico|css|js|woff|woff2|ttf|otf|eot|pdf|zip|webm|ogg|wav)$/i);

    if (isStaticFile) {
      return; // serve the real file as-is
    }

    return context.rewrite('/neocomus_website.html');
  }
};
