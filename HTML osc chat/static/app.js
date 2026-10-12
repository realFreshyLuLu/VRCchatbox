/* VRC Chatbox interface. See NOTICE.md for attribution. */
(() => {
  'use strict';
  const t = window.I18N.t;
  const $ = id => document.getElementById(id);
  const upstream = JSON.parse($('server-config').textContent);
  const KEY = 'vrc-first-project-frontend-v1';
  const HISTORY_KEY = KEY + ':history';
  const QUICK_KEY = KEY + ':quick';
  const PREF_KEY = KEY + ':prefs';
  const DEFAULT_PREFS = {
    dark: false, typing: true, source: 'zh-CN', target: 'ja',
    format: 'both', order: 'source-first', email: '', language: 'auto', provider: 'mymemory', endpoint: '', model: '', region: ''
  };
  const getJson = (k, fallback) => {
    try { const x = JSON.parse(localStorage.getItem(k)); return x === null ? fallback : x; }
    catch (_) { return fallback; }
  };
  let prefs = { ...DEFAULT_PREFS };
  let history = [];
  let quick = [];
  let serverRevision = -1;
  let writeQueue = Promise.resolve();
  const MIGRATED_KEY = KEY + ':migrated-to-pc';
  async function requestState(action, payload={}) {
    const res = await fetch('/api/frontend-state', action ? {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({action, ...payload}), cache:'no-store'
    } : {cache:'no-store'});
    let data;
    try {data = await res.json();} catch(_) {throw Error(t('PC 数据接口响应无效'));}
    if(!res.ok) throw Error(t(data.error) || `HTTP ${res.status}`);
    return data;
  }
  function applyState(state, {refreshPreferences=true}={}) {
    if(!state || !Array.isArray(state.history) || !Array.isArray(state.quick))
      throw Error(t('PC 数据结构不正确'));
    if(state.revision === serverRevision) return;
    history=state.history;
    quick=state.quick;
    serverRevision=state.revision;
    if(refreshPreferences){
      prefs={...DEFAULT_PREFS,...state.prefs};
      initPrefs();
      applyUpstreamTheme();
    }
    renderChat();renderHistory();renderQuick();
  }
  function queueAction(action, payload={}) {
    const task=writeQueue.then(async()=>{
      const state=await requestState(action,payload);
      applyState(state,{refreshPreferences:action !== 'prefs/update'});
      return state;
    });
    writeQueue=task.catch(()=>{});
    return task;
  }
  async function initializePcData() {
    try {
      await writeQueue;
      applyState(await requestState(null));
      // One-time localStorage import for existing v1.1 browsers; IDs prevent duplicates.
      if(!localStorage.getItem(MIGRATED_KEY)){
        const oldHistory=getJson(HISTORY_KEY,[]),oldQuick=getJson(QUICK_KEY,[]),oldPrefs=getJson(PREF_KEY,null);
        if((Array.isArray(oldHistory)&&oldHistory.length)||(Array.isArray(oldQuick)&&oldQuick.length)||oldPrefs){
          await queueAction('legacy/import',{
            history:Array.isArray(oldHistory)?oldHistory.slice(0,150):[],
            quick:Array.isArray(oldQuick)?oldQuick.slice(0,100):[],
            prefs:oldPrefs&&typeof oldPrefs==='object'?oldPrefs:undefined
          });
        }
        localStorage.setItem(MIGRATED_KEY,'1');
      }
    } catch(e){showToast(t('电脑端数据读取/迁移失败：')+e.message,true);}
  }
  async function refreshPcData() {
    try {
      await writeQueue;
      applyState(await requestState(null), {refreshPreferences:false});
    }catch(_){/* Offline request: do not erase already loaded records. */}
  }
  let currentView = 'chat';
  let pending = false;
  let typingActive = false;
  let typingTimer = null;
  let typingHeartbeat = null;
  let toastTimer = null;
  let quickEditId = null;
  let translatedDraft = null; // Metadata preserved only while the translated text is unedited.
  let shiftLineBreak = false;
  const titles = {
    chat: ['消息发送','跨设备文字交流'],
    history: ['发送记录','保存在电脑上的共享历史'],
    quick: ['快捷短语','电脑端共享的常用文字']
  };
  const htmlEsc = text => String(text).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  function showToast(message, error = false) {
    const bar = $('toast');
    clearTimeout(toastTimer);
    bar.textContent = message;
    bar.className = 'toast show' + (error ? ' error' : '');
    toastTimer = setTimeout(() => bar.className = 'toast', 4400);
  }
  function connection(text, state = '') {
    $('connectionStatus').className = 'connection' + (state ? ' ' + state : '');
    $('connectionText').textContent = text;
  }
  function savePrefs() {
    prefs.language = $('uiLanguage').value;
    prefs.provider = $('translationProvider').value;
    prefs.endpoint = $('apiEndpoint').value.trim();
    prefs.model = $('apiModel').value.trim();
    prefs.region = $('apiRegion').value.trim();
    window.I18N.set(prefs.language);
    switchView(currentView);renderChat();renderHistory();renderQuick();
    prefs.source = $('sourceLang').value;
    prefs.target = $('targetLang').value;
    prefs.format = $('sendFormat').value;
    prefs.order = $('translationOrder').value;
    prefs.email = $('translationEmail').value.trim();
    prefs.typing = $('enableTyping').checked;
    queueAction('prefs/update', {prefs:{...prefs}})
      .catch(e=>showToast(t('设置保存到电脑失败：')+e.message,true));
  }
  function initPrefs() {
    window.I18N.set(prefs.language);
    for (const [id,key] of Object.entries({uiLanguage:'language',translationProvider:'provider',apiEndpoint:'endpoint',apiModel:'model',apiRegion:'region'})) $(id).value=prefs[key];
    $('sourceLang').value = prefs.source;
    $('targetLang').value = prefs.target;
    $('sendFormat').value = prefs.format;
    $('translationOrder').value = prefs.order;
    $('translationEmail').value = prefs.email;
    $('enableTyping').checked = prefs.typing;
    setTheme(prefs.dark,false);
  }
  function setTheme(dark, persist=true) {
    prefs.dark = Boolean(dark);
    document.body.classList.toggle('dark', prefs.dark);
    $('themeToggle').textContent = prefs.dark ? '☀' : '☾';
    $('themeToggle').title = prefs.dark ? t('切换浅色') : t('切换深色');
    if(persist)queueAction('prefs/update',{prefs:{...prefs}})
      .catch(e=>showToast(t('主题设置保存到电脑失败：')+e.message,true));
  }
  function applyUpstreamTheme() {
    const style = document.documentElement.style;
    style.setProperty('--accent', upstream.primary_color || '#008f7a');
    style.setProperty('--user-bubble', upstream.user_bubble_color || '#6c5ce7');
    style.setProperty('--system-bubble', upstream.system_bubble_color || '#ffffff');
    style.setProperty('--system-avatar', upstream.system_avatar_color || '#00b894');
    style.setProperty('--user-avatar', upstream.user_avatar_color || '#6c5ce7');
    // In dark mode, enforce legibility rather than hardcode the original light chat background.
    if (!prefs.dark) style.setProperty('--chat-background', upstream.chat_bg_color || '#f5f7fa');
    if (upstream.chat_bg_image) {
      const safe = encodeURIComponent(upstream.chat_bg_image);
      $('conversation').style.backgroundImage = `url("/data/${safe}")`;
      $('conversation').style.backgroundSize = ['cover','contain','auto'].includes(upstream.chat_bg_size) ? upstream.chat_bg_size : 'cover';
    }
    if (upstream.system_avatar) {
      $('systemAvatar').textContent = '';
      $('systemAvatar').style.backgroundImage = `url("/data/${encodeURIComponent(upstream.system_avatar)}")`;
    }
  }
  function switchView(view) {
    currentView = view;
    for (const target of ['chat','history','quick']) {
      const visible = target === view;
      $('view-' + target).classList.toggle('active', visible);
      $('view-' + target).hidden = !visible;
    }
    document.querySelectorAll('[data-view]').forEach(b => {
      const active = b.dataset.view === view;
      b.classList.toggle('active', active);
      b.setAttribute('aria-current', active ? 'page' : 'false');
    });
    $('viewTitle').textContent = t(titles[view][0]);
    $('viewSubtitle').textContent = t(titles[view][1]);
    if (view === 'history') renderHistory();
    if (view === 'quick') renderQuick();
    if (view !== 'chat') refreshPcData();
  }
  function count(str) {
    return [...str].length;
  }
  function validateMessage(str) {
    if (count(str) > 144) throw new Error(`发送文本为 ${count(str)} 字符，超过 Chatbox 的 144 字符上限。`);
    if (str.split('\n').length > 9) throw new Error(t('发送文本超过 9 行，请缩短。'));
  }
  async function submitOriginalForm(data, signal) {
    const form = new URLSearchParams();
    for (const [key, val] of Object.entries(data)) form.append(key, String(val));
    const res = await fetch('/', {
      method: 'POST',
      headers: {'Content-Type':'application/x-www-form-urlencoded;charset=UTF-8'},
      body: form.toString(),
      cache: 'no-store',
      signal
    });
    if (!res.ok) throw new Error(`原版 Flask 返回 HTTP ${res.status}`);
    const txt = (await res.text()).trim();
    if (txt !== 'ok') throw new Error(t('服务器未返回预期的 ok；请检查端口和 Flask 控制台。'));
    return txt;
  }
  function notifyTyping(value) {
    if (value && !prefs.typing) return;
    typingActive = value;
    submitOriginalForm({typing:value?'1':'0'}).catch(() => {});
  }
  function scheduleTyping() {
    clearTimeout(typingTimer);
    clearInterval(typingHeartbeat);
    if (!$('messageInput').value.trim()) {
      if (typingActive) notifyTyping(false);
      return;
    }
    if (!prefs.typing) return;
    typingTimer = setTimeout(() => notifyTyping(true), 350);
    typingHeartbeat = setInterval(() => {
      if ($('messageInput').value.trim()) notifyTyping(true);
    }, 5000);
  }
  function stopTyping(alreadyClearedBySend = false) {
    clearTimeout(typingTimer);
    clearInterval(typingHeartbeat);
    const wasTyping = typingActive;
    typingActive = false;
    if (wasTyping && !alreadyClearedBySend) notifyTyping(false);
  }
  function updateCount() {
    const n = count($('messageInput').value);
    $('inputCount').textContent = n + ' / 144';
    $('inputCount').style.color = n > 144 ? 'var(--danger)' : '';
  }
  async function addHistory(text, original, translated) {
    const item={id:Date.now() + '-' + Math.random().toString(36).slice(2,9),text,original,translated,time:Date.now()};
    await queueAction('history/add',{item});
  }
  function renderChat() {
    const wrap = $('chatMessages');
    wrap.replaceChildren();
    $('emptyChat').hidden = history.length > 0;
    // Show only the latest messages; old ones remain in the History tab.
    [...history].slice(0,30).reverse().forEach(item => {
      const row = document.createElement('div');
      row.className = 'chat-bubble-item';
      const meta = document.createElement('time');
      meta.className = 'bubble-meta';
      meta.textContent = new Date(item.time).toLocaleTimeString(window.I18N.locale(),{hour:'2-digit',minute:'2-digit'});
      const bubble = document.createElement('div');
      bubble.className = 'chat-bubble';
      bubble.textContent = item.text;
      const avatar = document.createElement('div');
      avatar.className = 'user-avatar';
      avatar.textContent = t('我');
      if(upstream.user_avatar){avatar.style.backgroundImage = `url("/data/${encodeURIComponent(upstream.user_avatar)}")`;avatar.textContent='';}
      row.append(meta, bubble, avatar);
      wrap.append(row);
    });
    $('historyCount').textContent = history.length;
    $('conversation').scrollTop = $('conversation').scrollHeight;
  }
  function actionButton(title, callback) {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = title; b.addEventListener('click', callback);
    return b;
  }
  function emptyRecord(msg) {
    const box = document.createElement('div');
    box.className = 'empty-library'; box.textContent = msg;
    return box;
  }
  function renderHistory() {
    const list = $('historyList');
    list.replaceChildren();
    if (!history.length) {list.append(emptyRecord(t('暂时没有发送记录。')));return;}
    history.forEach(item => {
      const card = document.createElement('article'); card.className = 'record-card';
      const top = document.createElement('div'); top.className = 'record-top';
      const title = document.createElement('strong'); title.textContent = t('OSC 消息');
      const time = document.createElement('time'); time.textContent = new Date(item.time).toLocaleString(window.I18N.locale());
      top.append(title,time);
      const body = document.createElement('div'); body.className = 'record-body'; body.textContent = item.text;
      const actions = document.createElement('div'); actions.className = 'record-actions';
      actions.append(
        actionButton(t('填入编辑'), () => { $('messageInput').value=item.text; updateCount(); switchView('chat'); scheduleTyping(); }),
        actionButton(t('原样重发'), () => sendOriginal(item.text, {keepInput:true, original:item.original||item.text, translated:item.translated||''})),
        actionButton(t('复制'), () => copyText(item.text)),
        actionButton(t('删除'), () => queueAction('history/delete',{id:item.id}).catch(e=>showToast(t('删除历史失败：')+e.message,true)))
      );
      card.append(top,body);
      if (item.translated) {const origin=document.createElement('div'); origin.className='record-origin'; origin.textContent=t('原文：')+(item.original||'');card.append(origin)}
      card.append(actions); list.append(card);
    });
  }
  function renderQuick() {
    const list = $('quickList');list.replaceChildren();
    if (!quick.length) {list.append(emptyRecord(t('暂无快捷短语。可先新增一条常用消息。')));return;}
    quick.forEach(item => {
      const card=document.createElement('article');card.className='record-card';
      const body=document.createElement('div');body.className='record-body';body.textContent=item.text;
      const actions=document.createElement('div');actions.className='record-actions';
      actions.append(
        actionButton(t('发送'),()=>sendOriginal(item.text,{keepInput:true})),
        actionButton(t('填入'),()=>{$('messageInput').value=item.text;updateCount();switchView('chat');scheduleTyping()}),
        actionButton(t('复制'),()=>copyText(item.text)),
        actionButton(t('编辑'),()=>{quickEditId=item.id;$('quickEditor').value=item.text;$('saveQuick').textContent=t('保存修改');$('cancelQuick').hidden=false;$('quickEditor').focus()}),
        actionButton(t('删除'),()=>queueAction('quick/delete',{id:item.id}).catch(e=>showToast(t('删除短语失败：')+e.message,true)))
      );
      card.append(body,actions); list.append(card);
    });
  }
  async function saveQuick() {
    const text=$('quickEditor').value;
    if (!text.trim()) return showToast(t('短语不能为空。'),true);
    const item={id:quickEditId || Date.now()+'-'+Math.random().toString(36).slice(2,9),text};
    try {
      await queueAction('quick/upsert',{item});
      cancelQuick();
    }catch(e){showToast(t('保存短语失败：')+e.message,true);}
  }
  function cancelQuick() {quickEditId=null;$('quickEditor').value='';$('saveQuick').textContent=t('新增短语');$('cancelQuick').hidden=true;}
  async function copyText(text) {
    try {await navigator.clipboard.writeText(text);showToast(t('已复制到剪贴板。'));}
    catch (_) {showToast(t('浏览器未允许剪贴板访问，可以使用长按选择复制。'),true)}
  }
  function setBusy(value) {
    pending=value;
    for(const id of ['directSend','translateButton']) $(id).disabled=value;
  }
  const CHAT_MAX_CHARS=144, CHAT_MAX_LINES=9;
  const PUNCTUATION=/[。！？!?；;，,、：:．.…\.—]/u;
  function isSafeSpaceBoundary(chars, index) {
    // Treat a run of spaces/tabs between two English words as a non-boundary.
    let left=index-1, right=index+1;
    while(left>=0 && /[ \t]/.test(chars[left]))left--;
    while(right<chars.length && /[ \t]/.test(chars[right]))right++;
    return !(/[A-Za-z]/.test(chars[left]||'') && /[A-Za-z]/.test(chars[right]||''));
  }
  function chunkMessage(text) {
    const source=String(text).trim();
    if(!source) return {send:'',remaining:'',split:false};
    if(count(source)<=CHAT_MAX_CHARS && source.split('\n').length<=CHAT_MAX_LINES)
      return {send:source,remaining:'',split:false};
    const chars=Array.from(source);
    let lineCount=1,offset=0,lastBoundary=-1;
    for(let i=0;i<chars.length && i<CHAT_MAX_CHARS;i++){
      const ch=chars[i];
      if(ch==='\n' && lineCount>=CHAT_MAX_LINES)break;
      if(ch==='\n')lineCount++;
      offset+=ch.length; // UTF-16 offset; emoji counts as one character.
      const punctuation=PUNCTUATION.test(ch)
        && !(ch==='.' && /[0-9]/.test(chars[i-1]||'') && /[0-9]/.test(chars[i+1]||''))
        && !(ch===',' && /[0-9]/.test(chars[i-1]||'') && /[0-9]/.test(chars[i+1]||''));
      const newline=ch==='\n';
      const safeSpace=/[ \t]/.test(ch) && isSafeSpaceBoundary(chars,i);
      if(punctuation || newline || safeSpace){
        const candidate=source.slice(0,offset).trim();
        const rest=source.slice(offset).trimStart();
        if(candidate && rest)lastBoundary=offset;
      }
    }
    if(lastBoundary<0)throw Error(t('内容超出 144 字符或 9 行，且上限内找不到合适的标点分隔符。请手动加入逗号、句号或换行后重试。'));
    const send=source.slice(0,lastBoundary).trim();
    const remaining=source.slice(lastBoundary).trimStart();
    validateMessage(send);
    return {send,remaining,split:true};
  }
  async function sendOriginal(value, options={}) {
    if(pending)return;
    const isEditor = !options.keepInput;
    const before=$('messageInput').value;
    let plan;
    try {plan=chunkMessage(value);}catch(e){showToast(e.message,true);return;}
    const clearing=!plan.send;
    setBusy(true);
    try {
      // Original upstream Flask handler: POST / with message and typing=0.
      await submitOriginalForm({message:plan.send, typing:'0'});
      if (!clearing) {
        const draft = !plan.split && translatedDraft && translatedDraft.text === plan.send ? translatedDraft : null;
        try{
          await addHistory(plan.send, plan.split?plan.send:(options.original || (draft && draft.original) || plan.send),
                           plan.split?'':(options.translated || (draft && draft.translated) || ''));
        }catch(e){showToast(t('OSC 已提交，但历史记录保存失败：')+e.message,true);}
      }
      if(isEditor && $('messageInput').value===before){
        $('messageInput').value=plan.remaining;
        updateCount();
      }
      translatedDraft=null;
      stopTyping(true); // The original message POST already submitted typing=0.
      if (isEditor && plan.remaining) scheduleTyping();
      // No success confirmation; the untransmitted remainder stays in the editor.
      connection(t('网页已就绪'));
    } catch(e) {
      connection(t('HTTP 请求失败'),'bad');
      showToast((clearing?t('清除气泡失败：'):t('发送失败：'))+e.message+t('；文本已保留，可重试。'),true);
    } finally {setBusy(false);}
  }
  function uint8Length(text) {return new TextEncoder().encode(text).length;}
  function createFinalText(source, translation) {
    const format=$('sendFormat').value;
    if(format==='original')return source;
    if(format==='translated')return translation;
    return $('translationOrder').value === 'source-first' ? source+'\n'+translation : translation+'\n'+source;
  }
  async function translateViaMyMemory(source) {
    if ($('sourceLang').value === $('targetLang').value) return source;
    const controller = new AbortController();
    const timer = setTimeout(()=>controller.abort(),35000);
    try {
      const res=await fetch('/api/translate',{method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,
        body:JSON.stringify({text:source,source:$('sourceLang').value,target:$('targetLang').value,
          provider:$('translationProvider').value,key:$('apiKey').value,endpoint:$('apiEndpoint').value.trim(),
          model:$('apiModel').value.trim(),region:$('apiRegion').value.trim(),email:$('translationEmail').value.trim()})});
      const data=await res.json();
      if(!res.ok)throw Error(t(data.error || 'Translation failed')+(data.status?' (HTTP '+data.status+')':''));
      return data.text;
    } catch(e) {if(e.name==='AbortError')throw Error(t('Translation timed out'));throw e;}
    finally {clearTimeout(timer);}
  }
  async function prepareTranslation() {
    if(pending)return;
    const input=$('messageInput');
    // Translating repeatedly without edits always uses the last source text.
    const current=input.value.trim();
    const source=(translatedDraft && translatedDraft.text===current)
      ? translatedDraft.original : current;
    if(!source){showToast(t('先输入文字才能翻译。'),true);return;}
    if($('sendFormat').value==='original'){
      showToast(t('当前发送格式为「仅原文」，请选择「仅译文」或「原文 + 译文」。'),true);
      return;
    }
    setBusy(true);
    connection(t('翻译中…'),'warn');
    try {
      const translation=await translateViaMyMemory(source);
      const output=createFinalText(source,translation);
      input.value=output;
      translatedDraft={text:output.trim(),original:source,translated:translation};
      updateCount();
      scheduleTyping();
      connection(t('网页已就绪'));
      if(count(output)>144 || output.split('\n').length>9) {
        // No success receipt: the next Send automatically splits at punctuation.
      }
      // The translation remains in the main input. Never auto-send here.
    } catch(e){
      connection(t('翻译失败'),'bad');
      showToast(t('翻译失败：')+e.message+t('。可点击发送原文。'),true);
    } finally {setBusy(false);}
  }
  function openSettings(){populateServerSettings();$('settingsBackdrop').hidden=false;document.body.style.overflow='hidden';}
  function closeSettings(){$('settingsBackdrop').hidden=true;document.body.style.overflow='';}
  function populateServerSettings(){
    for(const [key,val] of Object.entries({oscIp:upstream.OSC_IP,oscPort:upstream.OSC_PORT,webIp:upstream.WEB_IP,webPort:upstream.WEB_PORT,accentColor:upstream.primary_color,userBubbleColor:upstream.user_bubble_color,systemBubbleColor:upstream.system_bubble_color,backgroundColor:upstream.chat_bg_color,userAvatarColor:upstream.user_avatar_color,systemAvatarColor:upstream.system_avatar_color,backgroundSize:upstream.chat_bg_size})){
      if($(key)) $(key).value=val;
    }
  }
  async function saveServerSettings(e){
    e.preventDefault();
    const btn=$('saveServerSettings');
    const form=new FormData($('originalSettingsForm'));
    for(const name of ['user_avatar','system_avatar','chat_bg_image']){
      const file=form.get(name);
      if(file&&file.size){
        if(file.size>3*1024*1024){showToast(t('单张图片请小于 3MB。'),true);return;}
        if(!/\.(png|jpe?g|gif|webp)$/i.test(file.name)){showToast(t('图片只能使用 png/jpg/gif/webp 扩展名。'),true);return;}
      }
    }
    const webChanged=$('webIp').value!==upstream.WEB_IP||Number($('webPort').value)!==Number(upstream.WEB_PORT);
    btn.disabled=true;
    try {
      // Original save_config handler: no other backend paths and no extra authentication behavior.
      const res=await fetch('/',{method:'POST',body:form});
      const txt=(await res.text()).trim();
      if(!res.ok||txt!=='success')throw new Error(t('服务器未确认保存'));
      closeSettings();
      showToast(webChanged?t('配置已保存。Web 监听地址/端口变化需要手动重启程序。'):t('配置已保存，正在刷新页面…'));
      if(!webChanged)setTimeout(()=>location.reload(),800);
    }catch(err){showToast(t('配置保存失败：')+err.message,true)}
    finally{btn.disabled=false}
  }
  function exportHistory(){
    if(!history.length)return showToast(t('没有可以导出的历史记录。'));
    const txt=history.map(h=>new Date(h.time).toLocaleString(window.I18N.locale())+'\n'+h.text+'\n').join('\n');
    const blob=new Blob([txt],{type:'text/plain;charset=utf-8'});
    const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='vrc-chatbox-history.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function pageHideTyping(){
    if(!typingActive)return;
    try { const body=new Blob(['typing=0'],{type:'application/x-www-form-urlencoded'});navigator.sendBeacon('/',body); }
    catch(_){/* Best effort; no server state change */}
  }
  function boot(){
    initPrefs();applyUpstreamTheme();renderChat();renderHistory();renderQuick();
    initializePcData();
    setInterval(()=>{if(!document.hidden)refreshPcData();},8000);
    document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>switchView(b.dataset.view)));
    $('themeToggle').addEventListener('click',()=>{setTheme(!prefs.dark);applyUpstreamTheme()});
    $('openSettings').addEventListener('click',openSettings);
    $('asideSettings').addEventListener('click',openSettings);
    $('translationProvider').addEventListener('change',()=>{
      $('apiKey').value='';$('apiEndpoint').value='';$('apiModel').value='';$('apiRegion').value='';
    });
    $('closeSettings').addEventListener('click',closeSettings);
    $('settingsBackdrop').addEventListener('click',e=>{if(e.target===$('settingsBackdrop'))closeSettings()});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('settingsBackdrop').hidden)closeSettings()});
    for(const id of ['sourceLang','targetLang','sendFormat','translationOrder','translationEmail','enableTyping','uiLanguage','translationProvider','apiEndpoint','apiModel','apiRegion']){
      $(id).addEventListener('change',()=>{savePrefs();if(id==='enableTyping'&&!prefs.typing)stopTyping()});
    }
    $('swapLang').addEventListener('click',()=>{const v=$('sourceLang').value;$('sourceLang').value=$('targetLang').value;$('targetLang').value=v;savePrefs()});
    $('messageInput').addEventListener('input',()=>{translatedDraft=null;updateCount();scheduleTyping()});
    $('messageInput').addEventListener('keydown',e=>{
      if(e.key!=='Enter' || e.isComposing || e.keyCode===229)return;
      if(e.shiftKey){
        // Desktop Shift+Enter must still insert a newline.
        shiftLineBreak=true;
        setTimeout(()=>{shiftLineBreak=false;},0);
        return;
      }
      e.preventDefault();
      sendOriginal($('messageInput').value);
    });
    // iOS / mobile keyboards sometimes emit beforeinput(insertLineBreak)
    // without a normal Enter keydown. Avoid accidentally sending while IME
    // is composing or when Shift+Enter was deliberately requested.
    $('messageInput').addEventListener('beforeinput',e=>{
      if(!['insertLineBreak','insertParagraph'].includes(e.inputType) || e.isComposing || shiftLineBreak)return;
      e.preventDefault();
      sendOriginal($('messageInput').value);
    });
    $('directSend').addEventListener('click',()=>sendOriginal($('messageInput').value));
    $('translateButton').addEventListener('click',prepareTranslation);
    $('clearInput').addEventListener('click',()=>{$('messageInput').value='';translatedDraft=null;updateCount();stopTyping();});
    $('insertQuick').addEventListener('click',()=>switchView('quick'));
    $('saveQuick').addEventListener('click',saveQuick);
    $('cancelQuick').addEventListener('click',cancelQuick);
    $('quickEditor').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing&&e.keyCode!==229){e.preventDefault();saveQuick()}});
    $('clearHistory').addEventListener('click',()=>{if(!history.length)return;if(!confirm(t('确定清空电脑上的全部发送记录？所有设备都会同步。')))return;queueAction('history/clear').catch(e=>showToast(t('清空历史失败：')+e.message,true))});
    $('exportHistory').addEventListener('click',exportHistory);
    $('originalSettingsForm').addEventListener('submit',saveServerSettings);
    window.addEventListener('pagehide',pageHideTyping);
    updateCount();connection(t('网页已就绪'));
  }
  boot();
})();
