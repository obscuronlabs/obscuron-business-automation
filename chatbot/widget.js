(function() {
  'use strict';
  var s = document.currentScript;
  var rawConfig = (s && s.getAttribute('data-config')) || window._ob_config || '';
  var config = {};
  try { config = JSON.parse(atob(rawConfig)); } catch(e) {}

  var color   = config.c || '#6c5fff';
  var name    = config.n || 'AI Assistant';
  var info    = config.i || '';
  var bizType = config.t || 'business';
  var greeting = config.g || ('Hi! Welcome to ' + name + '. How can I help you today?');
  var API_KEY = s && (s.getAttribute('data-key') || '');

  var systemPrompt = [
    'You are a helpful AI assistant for ' + name + ', a ' + bizType + '.',
    info ? info : '',
    'Answer questions professionally, keep responses concise and friendly.',
    'If unsure about specific details, politely suggest contacting the business directly.',
    'Respond in the same language the user writes in.',
    'Today\'s date: ' + new Date().toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'})
  ].filter(Boolean).join(' ');

  // Inject styles
  var st = document.createElement('style');
  st.textContent = [
    '#_ob_btn{position:fixed;bottom:24px;right:24px;width:56px;height:56px;background:'+color+';border-radius:50%;border:none;cursor:pointer;box-shadow:0 4px 24px rgba(0,0,0,.35);z-index:2147483647;display:flex;align-items:center;justify-content:center;transition:transform .2s,box-shadow .2s}',
    '#_ob_btn:hover{transform:scale(1.08);box-shadow:0 6px 32px rgba(0,0,0,.4)}',
    '#_ob_btn svg{width:26px;height:26px;fill:#fff;pointer-events:none}',
    '#_ob_win{position:fixed;bottom:90px;right:24px;width:340px;height:500px;background:#fff;border-radius:18px;box-shadow:0 12px 50px rgba(0,0,0,.25);z-index:2147483646;display:none;flex-direction:column;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:14px}',
    '#_ob_win._open{display:flex}',
    '#_ob_hd{background:'+color+';color:#fff;padding:14px 16px;font-weight:700;font-size:15px;display:flex;align-items:center;justify-content:space-between}',
    '#_ob_hd .info{display:flex;align-items:center;gap:8px}',
    '#_ob_hd .dot{width:8px;height:8px;background:#4ade80;border-radius:50%;flex-shrink:0}',
    '#_ob_close{background:transparent;border:none;color:#fff;cursor:pointer;font-size:18px;line-height:1;opacity:.8;padding:0}',
    '#_ob_msgs{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:#f5f5f7}',
    '._ob_m{max-width:82%;padding:9px 13px;border-radius:14px;font-size:13.5px;line-height:1.5;word-break:break-word}',
    '._ob_m.u{background:'+color+';color:#fff;align-self:flex-end;border-bottom-right-radius:4px}',
    '._ob_m.b{background:#fff;color:#1a1a1a;align-self:flex-start;border-bottom-left-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.08)}',
    '._ob_m.typing{color:#999;font-style:italic}',
    '#_ob_ir{display:flex;padding:10px 12px;gap:8px;background:#fff;border-top:1px solid #eee}',
    '#_ob_inp{flex:1;border:1px solid #ddd;border-radius:10px;padding:9px 12px;font-size:13.5px;outline:none;transition:border-color .2s;font-family:inherit}',
    '#_ob_inp:focus{border-color:'+color+'}',
    '#_ob_send{background:'+color+';color:#fff;border:none;border-radius:10px;padding:9px 14px;cursor:pointer;font-weight:700;font-size:13px;transition:opacity .2s;white-space:nowrap}',
    '#_ob_send:hover{opacity:.85}',
    '#_ob_send:disabled{opacity:.4;cursor:not-allowed}',
    '#_ob_pw{text-align:center;font-size:10.5px;color:#bbb;padding:5px;background:#fff}',
    '#_ob_pw a{color:#bbb;text-decoration:none}',
  ].join('');
  document.head.appendChild(st);

  // Build DOM
  var btn = document.createElement('button');
  btn.id = '_ob_btn';
  btn.setAttribute('aria-label', 'Open chat');
  btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>';

  var win = document.createElement('div');
  win.id = '_ob_win';
  win.innerHTML = [
    '<div id="_ob_hd"><div class="info"><div class="dot"></div><span>'+escHtml(name)+'</span></div><button id="_ob_close" aria-label="Close">✕</button></div>',
    '<div id="_ob_msgs"></div>',
    '<div id="_ob_ir"><input id="_ob_inp" type="text" placeholder="Type a message…" maxlength="500"><button id="_ob_send">Send</button></div>',
    '<div id="_ob_pw">Powered by <a href="https://obscuronlabs.com" target="_blank" rel="noopener">Obscuron AI</a></div>',
  ].join('');

  document.body.appendChild(btn);
  document.body.appendChild(win);

  var msgs = [];
  var isOpen = false;

  addMsg('b', greeting);

  btn.addEventListener('click', toggle);
  win.querySelector('#_ob_close').addEventListener('click', toggle);
  win.querySelector('#_ob_send').addEventListener('click', send);
  win.querySelector('#_ob_inp').addEventListener('keydown', function(e){ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }});

  function toggle() {
    isOpen = !isOpen;
    win.classList.toggle('_open', isOpen);
    if (isOpen) { win.querySelector('#_ob_inp').focus(); scrollBottom(); }
  }

  function addMsg(role, text) {
    var msgsEl = document.getElementById('_ob_msgs');
    var d = document.createElement('div');
    d.className = '_ob_m ' + role;
    d.textContent = text;
    msgsEl.appendChild(d);
    scrollBottom();
    return d;
  }

  function scrollBottom() {
    var m = document.getElementById('_ob_msgs');
    if (m) m.scrollTop = m.scrollHeight;
  }

  function send() {
    var inp = document.getElementById('_ob_inp');
    var text = inp.value.trim();
    if (!text) return;
    inp.value = '';
    addMsg('u', text);
    msgs.push({ role: 'user', content: text });

    var typing = addMsg('b', '…');
    typing.classList.add('typing');
    var sendBtn = document.getElementById('_ob_send');
    sendBtn.disabled = true;

    var payload = {
      model: 'openai/gpt-4o-mini',
      max_tokens: 350,
      messages: [{ role: 'system', content: systemPrompt }].concat(msgs)
    };

    fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + API_KEY },
      body: JSON.stringify(payload)
    })
    .then(function(r){ return r.json(); })
    .then(function(data){
      typing.remove();
      var reply = (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) || 'Sorry, I could not process that.';
      addMsg('b', reply.trim());
      msgs.push({ role: 'assistant', content: reply.trim() });
    })
    .catch(function(){
      typing.remove();
      addMsg('b', 'Connection error. Please try again.');
    })
    .finally(function(){ sendBtn.disabled = false; });
  }

  function escHtml(s){ var d=document.createElement('div');d.appendChild(document.createTextNode(s));return d.innerHTML; }
})();
