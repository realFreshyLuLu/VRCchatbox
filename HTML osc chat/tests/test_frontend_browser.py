"""End-to-end browser behavior with mocked transport and PC persistence API.
Run: python 'HTML osc chat/tests/test_frontend_browser.py'
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CFG=dict(SYSTEM_LANGUAGE='zh-CN', OSC_IP='127.0.0.1', OSC_PORT=9000,WEB_IP='0.0.0.0',WEB_PORT=5000,
         primary_color='#008f7a',user_avatar_color='#6c5ce7',system_avatar_color='#00b894',
         user_bubble_color='#008f7a',system_bubble_color='#ffffff',chat_bg_color='#f5f7fa',
         chat_bg_size='cover',user_avatar='',system_avatar='',chat_bg_image='')


def build_html():
    s=(ROOT/'templates/index.html').read_text(encoding='utf-8')
    css=(ROOT/'static/app.css').read_text(encoding='utf-8')
    s=s.replace('{{ config | tojson }}',json.dumps(CFG,ensure_ascii=False))
    s=s.replace('<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'app.css\') }}">',
                '<style>'+css+'</style>')
    s=s.replace('<script src="{{ url_for(\'static\', filename=\'app.js\') }}" defer></script>','')
    s=s.replace('<script src="{{ url_for(\'static\', filename=\'i18n.js\') }}" defer></script>','')
    assert '{{ ' not in s
    return s

DEFAULT_STATE={"history":[],"quick":[],"prefs":{"dark":False,"typing":True,"source":"zh-CN", "target":"ja", "format":"both","order":"source-first","email":""},"revision":0,"prefsInitialized":False}
MOCK_FETCH='''(initialState) => {
  const memory=new Map();
  Object.defineProperty(window,'localStorage',{configurable:true,value:{
    getItem:k=>memory.has(k)?memory.get(k):null,
    setItem:(k,v)=>memory.set(k,String(v)),removeItem:k=>memory.delete(k)
  }});
  window.__requests=[];window.__apiActions=[];
  window.__serverState=structuredClone(initialState);
  window.__failNextSend=false;
  const response=(status,data)=>({ok:status<400,status,json:async()=>structuredClone(data)});
  window.fetch=async function(url, options={}) {
    const uri=String(url);
    if(uri==='/api/translate')
      return response(200,{text:'こんにちは'});
    if(uri==='/api/frontend-state') {
      if(!options.method || options.method==='GET')return response(200,window.__serverState);
      let p=JSON.parse(options.body);window.__apiActions.push(p.action);
      let st=window.__serverState, item=p.item;
      switch(p.action) {
        case 'history/add':st.history=[item,...st.history.filter(x=>x.id!==item.id)].slice(0,150);break;
        case 'history/delete':st.history=st.history.filter(x=>x.id!==p.id);break;
        case 'history/clear':st.history=[];break;
        case 'quick/upsert':st.quick=[item,...st.quick.filter(x=>x.id!==item.id)].slice(0,100);break;
        case 'quick/delete':st.quick=st.quick.filter(x=>x.id!==p.id);break;
        case 'prefs/update':st.prefs={...st.prefs,...p.prefs};st.prefsInitialized=true;break;
        case 'legacy/import':{
          for(const [kind,cap] of [['history',150],['quick',100]]){
            let ids=new Set(st[kind].map(x=>x.id));
            for(let entry of p[kind]||[]){if(!ids.has(entry.id)){st[kind].push(entry);ids.add(entry.id)}}
            st[kind]=st[kind].slice(0,cap);
          }
          if(!st.prefsInitialized && p.prefs){st.prefs={...st.prefs,...p.prefs};st.prefsInitialized=true;}
          break;
        }
        default: return response(400,{error:'unsupported'});
      }
      st.revision++;return response(200,st);
    }
    if(uri==='/') {
      let fields={};
      if(typeof options.body==='string')fields=Object.fromEntries(new URLSearchParams(options.body));
      else if(options.body instanceof FormData)fields=Object.fromEntries(options.body.entries());
      window.__requests.push(fields);
      if(window.__failNextSend && 'message' in fields){window.__failNextSend=false;throw Error('mock network failure')}
      return {ok:true,status:200,text:async()=>fields.save_config?'success':'ok'};
    }
    throw Error('Unexpected URL: '+uri);
  };
}'''


def wait_init(page):
    page.wait_for_function("localStorage.getItem('vrc-first-project-frontend-v1:migrated-to-pc') === '1'")


def wait_records(page,n):
    page.wait_for_function(f'window.__serverState.history.length==={n}')


def messages(page):
    return page.evaluate('window.__requests.filter(x=>Object.hasOwn(x,"message"))')


def setup(page, state=None, legacy=None):
    page.set_content(build_html())
    page.evaluate(MOCK_FETCH, state or DEFAULT_STATE)
    if legacy:
        for key,value in legacy.items():
            page.evaluate('(pair) => localStorage.setItem(pair[0],JSON.stringify(pair[1]))',[key,value])
    page.add_script_tag(content=(ROOT/'static/i18n.js').read_text(encoding='utf-8'))
    page.add_script_tag(content=(ROOT/'static/app.js').read_text(encoding='utf-8'))
    wait_init(page)


def run():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
        context=browser.new_context(viewport={'width':390,'height':844})
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        setup(page)
        assert page.locator('#messageInput').get_attribute('maxlength') is None
        assert page.locator('#messageInput').get_attribute('enterkeyhint')=='send'
        assert page.locator('.primary-actions button').evaluate_all('(bs)=>bs.map(x=>x.id)')==['translateButton','directSend']

        # Translate is a preview only; the one send button always posts upstream form.
        page.locator('#messageInput').fill('你好')
        page.locator('#translateButton').click()
        page.wait_for_function("document.querySelector('#messageInput').value.includes('こんにちは')")
        assert not messages(page)
        page.locator('#directSend').click()
        wait_records(page,1)
        assert messages(page)[-1]['message']=='你好\nこんにちは',messages(page)
        assert page.locator('#toast').get_attribute('class')=='toast'
        assert page.locator('#messageInput').input_value()==''
        page.locator('#directSend').click()
        page.wait_for_function('window.__requests.some(x=>Object.hasOwn(x,"message")&&x.message==="")')
        assert page.evaluate('window.__serverState.history.length')==1

        # Last delimiter under cap wins; remainder stays and is only sent next press.
        long_text='甲'*50+'，'+'乙'*70+'。'+'丙'*90
        page.locator('#messageInput').fill(long_text)
        assert page.locator('#messageInput').input_value()==long_text
        page.locator('#directSend').click()
        wait_records(page,2)
        assert messages(page)[-1]['message']=='甲'*50+'，'+'乙'*70+'。',messages(page)[-1]
        assert page.locator('#messageInput').input_value()=='丙'*90
        page.locator('#messageInput').press('Enter')
        wait_records(page,3)
        assert messages(page)[-1]['message']=='丙'*90
        assert page.locator('#messageInput').input_value()==''

        # English word spaces are not safe boundaries; hyphens inside words aren't either.
        page.locator('#messageInput').fill('Hello world '*20)
        before=len(messages(page))
        page.locator('#directSend').click()
        assert len(messages(page))==before
        assert '找不到合适的标点' in page.locator('#toast').inner_text()
        assert page.locator('#messageInput').input_value()=='Hello world '*20
        page.locator('#messageInput').fill('Hello world. '+'nice day '*20)
        page.locator('#directSend').click()
        wait_records(page,4)
        assert messages(page)[-1]['message']=='Hello world.'
        assert page.locator('#messageInput').input_value().startswith('nice day')

        # More than nine lines: only send through a newline before line 10.
        many='\n'.join(['第'+str(n)+'行' for n in range(1,12)])
        page.locator('#messageInput').fill(many)
        page.locator('#directSend').click()
        wait_records(page,5)
        assert len(messages(page)[-1]['message'].split('\n'))<=9
        assert page.locator('#messageInput').input_value().startswith('第')

        # Failure must not discard the unsent text.
        page.locator('#messageInput').fill('甲'*100+'，'+'乙'*100)
        page.evaluate('window.__failNextSend=true')
        before=len(messages(page))
        page.locator('#directSend').click()
        assert page.locator('#messageInput').input_value()=='甲'*100+'，'+'乙'*100
        assert page.evaluate('window.__serverState.history.length')==5
        assert '发送失败' in page.locator('#toast').inner_text()

        # Quick text and UI prefs are written to PC state rather than localStorage.
        page.locator('.mobile-item[data-view="quick"]').click()
        page.locator('#quickEditor').fill('电脑端测试快捷文本')
        page.locator('#saveQuick').click()
        page.wait_for_function('window.__serverState.quick.length===1')
        page.locator('.mobile-item[data-view="history"]').click()
        assert page.locator('.record-card').count()>=1
        page.locator('#themeToggle').click()
        page.wait_for_function('window.__serverState.prefs.dark===true')
        assert 'prefs/update' in page.evaluate('window.__apiActions')
        assert not page.evaluate('localStorage.getItem("vrc-first-project-frontend-v1:history")')
        assert not page.evaluate('localStorage.getItem("vrc-first-project-frontend-v1:quick")')
        snapshot=page.evaluate('structuredClone(window.__serverState)')

        # Opening from a different phone/browser recovers the PC state.
        page2=context.new_page()
        setup(page2, snapshot)
        assert page2.locator('#chatMessages .chat-bubble').count()==5
        assert page2.locator('#themeToggle').inner_text()=='☀'
        page2.locator('.mobile-item[data-view="quick"]').click()
        assert '电脑端测试快捷文本' in page2.locator('#quickList').inner_text()

        # Legacy browser records are imported to PC once.
        legacy={'vrc-first-project-frontend-v1:history':[{'id':'old-001','text':'旧版历史','time':123,'original':'旧版历史','translated':''}],
                'vrc-first-project-frontend-v1:quick':[{'id':'oldquick','text':'旧快捷'}]}
        page3=context.new_page();setup(page3,DEFAULT_STATE,legacy)
        assert page3.evaluate('window.__serverState.history[0].text')=='旧版历史'
        assert page3.evaluate('window.__serverState.quick[0].text')=='旧快捷'
        assert page3.evaluate('window.__apiActions.filter(x=>x==="legacy/import").length')==1

        # 320px and 390px shouldn't overflow horizontally.
        for w in (320,390):
            page.set_viewport_size({'width':w,'height':800})
            page.locator('.mobile-item[data-view="chat"]').click()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2'),w
        assert not errors,errors
        browser.close()
    print('PASS: browser v1.2 overlimit splitting, EN word safety, 9 lines, failure preservation, PC sync, migration, responsive UI')

if __name__=='__main__':run()
