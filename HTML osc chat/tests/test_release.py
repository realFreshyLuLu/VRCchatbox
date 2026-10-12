import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
import translation
import startup
import osc_viewer
import frontend_store

@pytest.mark.parametrize('provider,result,expected_path', [
    ('mymemory',{'responseStatus':200,'responseData':{'translatedText':'Hello'}},'/get?'),
    ('deepl',{'translations':[{'text':'Hello'}]},'/v2/translate'),
    ('azure',[{'translations':[{'text':'Hello'}]}],'/translate?'),
    ('openai',{'choices':[{'message':{'content':'Hello'}}]},'/chat/completions')])
def test_adapters(provider,result,expected_path):
    with patch.object(translation,'exchange',return_value=result) as send:
        assert translation.translate(dict(text='你好',source='zh-CN',target='en',provider=provider,key='test-key',region='eastasia'))=='Hello'
        args=send.call_args.args
        assert expected_path in args[0]
        if provider=='deepl':
            assert args[1]['source_lang']=='ZH'
            assert args[2]['Authorization']=='DeepL-Auth-Key test-key'
        if provider=='azure': assert args[2]['Ocp-Apim-Subscription-Region']=='eastasia'
        if provider=='openai': assert args[1]['messages'][1]['content']=='你好'

def test_errors_and_no_secret_leak():
    client=osc_viewer.app.test_client()
    base=dict(text='你好',source='zh-CN',target='en',provider='deepl')
    assert client.post('/api/translate',json=base).status_code==400
    base['key']='secret'
    with patch.object(translation,'exchange',side_effect=translation.HTTPError('url',401,'secret',{},None)):
        response=client.post('/api/translate',json=base)
        assert response.status_code==502
        assert b'secret' not in response.data
    with patch.object(translation,'exchange',side_effect=TimeoutError):
        assert client.post('/api/translate',json=base).status_code==502
    assert client.post('/api/translate',json={**base,'endpoint':'http://example.com'}).status_code==400

def test_language_and_provider_persist(tmp_path):
    with patch.object(frontend_store,'DATA_PATH',tmp_path/'state.json'):
        client=osc_viewer.app.test_client()
        for lang in ['zh-CN','ja','en','ko','auto']:
            assert client.post('/api/frontend-state',json={'action':'prefs/update','prefs':{'language':lang,'provider':'deepl','key':'secret'}}).status_code==200
            result=client.get('/api/frontend-state').json
            assert result['prefs']['language']==lang
            assert 'key' not in result['prefs']
        assert 'secret' not in (tmp_path/'state.json').read_text()

def test_addresses():
    assert startup.addresses('127.0.0.1',8123)==(['http://127.0.0.1:8123/'],[])
    with patch.object(startup.socket,'getaddrinfo',return_value=[(None,None,None,None,('192.168.1.8',0))]):
        local,lan=startup.addresses('0.0.0.0',8123)
        assert local==['http://127.0.0.1:8123/']
        assert 'http://192.168.1.8:8123/' in lan

def test_page_and_osc():
    client=osc_viewer.app.test_client()
    page=client.get('/')
    assert page.status_code==200 and b'SYSTEM_LANGUAGE' in page.data
    with patch.object(osc_viewer,'osc_client') as osc:
        assert client.post('/',data={'message':'hello','typing':'0'}).data==b'ok'
        osc.send_message.assert_any_call('/chatbox/input',['hello',True,True])
