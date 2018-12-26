(function(p) {
  if (!p === undefined) {
    console.error('Pebble object not found!?');
    return;
  }

  // Aliases:
  p.on = p.addEventListener;
  p.off = p.removeEventListener;

  // For Android (WebView-based) pkjs, print stacktrace for uncaught errors:
  if (typeof window !== 'undefined' && window.addEventListener) {
    window.addEventListener('error', function(event) {
      if (event.error && event.error.stack) {
        console.error('' + event.error + '\n' + event.error.stack);
      }
    });
  }

})(Pebble);
