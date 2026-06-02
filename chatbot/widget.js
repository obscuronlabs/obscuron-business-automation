(function() {
  var scriptTag = document.currentScript || (function() {
    var scripts = document.getElementsByTagName('script');
    return scripts[scripts.length - 1];
  })();

  var widgetId = scriptTag.getAttribute('data-widget') || 'demo';
  var apiBase = scriptTag.src.replace('/widget.js', '');

  // Fetch config
  fetch(apiBase + '/api/config/' + widgetId)
    .then(function(r) { return r.json(); })
    .then(function(config) { initWidget(config); })
    .catch(function() { initWidget({ business_name: 'AI Assistant', primary_color: '#6c5fff', greeting: 'Hi! How can I help?' }); });

  function initWidget(config) {
    var color = config.primary_color || '#6c5fff';
    var greeting = config.greeting || 'Hi! How can I help you today?';
    var name = config.business_name || 'AI Assistant';

    var style = document.createElement('style');
    style.textContent = `
      #ob-chat-btn { position:fixed; bottom:24px; right:24px; width:56px; height:56px; background:${color}; border-radius:50%; border:none; cursor:pointer; box-shadow:0 4px 20px rgba(0,0,0,0.3); z-index:99999; display:flex; align-items:center; justify-content:center; transition:transform 0.2s; }
      #ob-chat-btn:hover { transform:scale(1.1); }
      #ob-chat-btn svg { width:26px; height:26px; fill:#fff; }
      #ob-chat-window { position:fixed; bottom:90px; right:24px; width:340px; height:480px; background:#fff; border-radius:16px; box-shadow:0 8px 40px rgba(0,0,0,0.2); z-index:99998; display:none; flex-direction:column; overflow:hidden; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
      #ob-chat-window.open { display:flex; }
      #ob-chat-header { background:${color}; color:#fff; padding:16px; font-weight:700; font-size:15px; display:flex; align-items:center; gap:10px; }
      #ob-chat-header .dot { width:8px; height:8px; background:#4ade80; border-radius:50%; }
      #ob-chat-messages { flex:1; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:10px; background:#f9f9f9; }
      .ob-msg { max-width:80%; padding:10px 14px; border-radius:12px; font-size:14px; line-height:1.5; word-break:break-word; }
      .ob-msg.user { background:${color}; color:#fff; align-self:flex-end; border-bottom-right-radius:4px; }
      .ob-msg.bot { background:#fff; color:#333; align-self:flex-start; border-bottom-left-radius:4px; box-shadow:0 1px 4px rgba(0,0,0,0.1); }
      .ob-msg.typing { color:#999; font-style:italic; }
      #ob-chat-input-row { display:flex; padding:12px; gap:8px; background:#fff; border-top:1px solid #eee; }
      #ob-chat-input { flex:1; border:1px solid #ddd; border-radius:8px; padding:10px 12px; font-size:14px; outline:none; }
      #ob-chat-input:focus { border-color:${color}; }
      #ob-send-btn { background:${color}; color:#fff; border:none; border-radius:8px; padding:10px 16px; cursor:pointer; font-weight:700; font-size:14px; transition:opacity 0.2s; }
      #ob-send-btn:hover { opacity:0.85; }
      #ob-powered { text-align:center; font-size:11px; color:#bbb; padding:6px; background:#fff; }
      #ob-powered a { color:#bbb; text-decoration:none; }
    `;
    document.head.appendChild(style);

    // Chat button
    var btn = document.createElement('button');
    btn.id = 'ob-chat-btn';
    btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';
    document.body.appendChild(btn);

    // Chat window
    var win = document.createElement('div');
    win.id = 'ob-chat-window';
    win.innerHTML = `
      <div id="ob-chat-header"><div class="dot"></div><span>${name}</span></div>
      <div id="ob-chat-messages"></div>
      <div id="ob-chat-input-row">
        <input id="ob-chat-input" type="text" placeholder="Type a message...">
        <button id="ob-send-btn">Send</button>
      </div>
      <div id="ob-powered">Powered by <a href="https://obscuronlabs.com" target="_blank">Obscuron AI</a></div>
    `;
    document.body.appendChild(win);

    var messages = [];
    var open = false;

    // Greeting
    addMessage('bot', greeting);

    btn.addEventListener('click', function() {
      open = !open;
      win.classList.toggle('open', open);
      if (open) document.getElementById('ob-chat-input').focus();
    });

    document.getElementById('ob-send-btn').addEventListener('click', sendMsg);
    document.getElementById('ob-chat-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') sendMsg();
    });

    function addMessage(role, text) {
      var msgsEl = document.getElementById('ob-chat-messages');
      var div = document.createElement('div');
      div.className = 'ob-msg ' + (role === 'user' ? 'user' : 'bot');
      div.textContent = text;
      msgsEl.appendChild(div);
      msgsEl.scrollTop = 99999;
      return div;
    }

    function sendMsg() {
      var input = document.getElementById('ob-chat-input');
      var text = input.value.trim();
      if (!text) return;
      input.value = '';
      addMessage('user', text);
      messages.push({ role: 'user', content: text });

      var typing = addMessage('bot', '...');
      typing.classList.add('typing');
      document.getElementById('ob-send-btn').disabled = true;

      fetch(apiBase + '/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ widget_id: widgetId, messages: messages })
      })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        typing.remove();
        var reply = data.reply || 'Sorry, I could not process that.';
        addMessage('bot', reply);
        messages.push({ role: 'assistant', content: reply });
      })
      .catch(function() {
        typing.remove();
        addMessage('bot', 'Connection error. Please try again.');
      })
      .finally(function() {
        document.getElementById('ob-send-btn').disabled = false;
      });
    }
  }
})();
