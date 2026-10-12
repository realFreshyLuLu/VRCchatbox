"""Exercise the real PC persistence logic without requiring Flask installation.
In Windows with Flask installed, the module uses an actual Flask Blueprint.
"""
import importlib.util
import json
import tempfile
import sys
import threading
import types
from types import SimpleNamespace
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
class FakeBlueprint:
    def __init__(self,*args,**kwargs):pass
    def route(self,*args,**kwargs):return lambda fn:fn
fake_flask=types.ModuleType('flask')
fake_flask.Blueprint=FakeBlueprint
class FakeResponse(dict):
    def __init__(self, data):
        super().__init__(data)
        self.headers={}
fake_flask.jsonify=FakeResponse
fake_flask.request=None
sys.modules.setdefault('flask',fake_flask)
spec=importlib.util.spec_from_file_location('frontend_store_test',HERE/'frontend_store.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def run():
    with tempfile.TemporaryDirectory() as d:
        mod.DATA_PATH=Path(d)/'config/frontend_state.json'
        state=mod._load()
        assert state['history']==[] and not mod.DATA_PATH.exists()
        mod._apply(state,'history/add',{'item':{'text':'你好，','original':'你好，','time':500}})
        assert len(state['history'])==1
        mod._apply(state,'quick/upsert',{'item':{'id':'q1','text':'常用文本'}})
        mod._apply(state,'prefs/update',{'prefs':{'dark':True,'target':'ja'}})
        mod._save(state)
        loaded=mod._load()
        assert loaded['history'][0]['text']=='你好，'
        assert loaded['prefs']['dark'] is True and loaded['quick'][0]['text']=='常用文本'
        old={'history':[{'id':'old','text':'旧记录','time':100},{'id':'old','text':'旧记录','time':100}],
             'quick':[{'id':'oldq','text':'旧短语'}],'prefs':{'dark':False}}
        mod._apply(loaded,'legacy/import',old)
        mod._apply(loaded,'legacy/import',old)
        assert sum(x['id']=='old' for x in loaded['history'])==1
        assert sum(x['id']=='oldq' for x in loaded['quick'])==1
        assert loaded['prefs']['dark'] is True,'legacy import cannot overwrite initialized preferences'
        mod._apply(loaded,'history/delete',{'id':'old'})
        assert all(x['id']!='old' for x in loaded['history'])
        mod._apply(loaded,'quick/delete',{'id':'oldq'})
        assert not any(x['id']=='oldq' for x in loaded['quick'])
        mod._apply(loaded,'history/clear',{})
        assert loaded['history']==[]
        try:mod._apply(loaded,'quick/upsert',{'item':{'text':''}})
        except ValueError:pass
        else:raise AssertionError('invalid empty quick text must reject')
        mod._save(loaded)
        assert json.loads(mod.DATA_PATH.read_text(encoding='utf-8'))['history']==[]
        # Exercise the actual route function with a minimal Flask request stub.
        mod.request=SimpleNamespace(method='GET')
        snapshot=mod.frontend_state()
        assert snapshot['quick'][0]['text']=='常用文本'
        mod.request=SimpleNamespace(method='POST',content_length=100,is_json=True,
                                    get_json=lambda silent=True:{'action':'quick/upsert','item':{'id':'q2','text':'新短语'}})
        saved=mod.frontend_state()
        assert saved['quick'][0]['text']=='新短语'
        assert mod._load()['quick'][0]['text']=='新短语'
        mod.DATA_PATH.write_text('{broken')
        try:mod._load()
        except RuntimeError:pass
        else:raise AssertionError('corrupt data must not silently reset')
    print('PASS PC persistence: atomic JSON, legacy migration, deduplication, preferences, CRUD and corruption safety')

if __name__=='__main__':run()
