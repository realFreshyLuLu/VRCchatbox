"""Offline testing of actual upstream-derived index() handler without installing Flask.
Extracts the genuine Python AST of the Flask route, not a copy of its logic.
"""
import ast
from pathlib import Path
from types import SimpleNamespace

SOURCE=Path(__file__).resolve().parents[1]/'osc_viewer.py'

class FakeOsc:
    def __init__(self): self.sent=[]
    def send_message(self, address, payload): self.sent.append((address,payload))

def run():
    source=SOURCE.read_text(encoding='utf-8')
    original=source.replace('                else: osc_client.send_message("/chatbox/input", ["", True, False])\n','')
    assert 'if msg: osc_client.send_message("/chatbox/input", [msg, True, True])' in original
    fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='index')
    fn.decorator_list=[]
    code=compile(ast.Module(body=[fn],type_ignores=[]),str(SOURCE),'exec')
    for form, expected in [
        ({'message':'你好','typing':'0'}, [('/chatbox/input',['你好',True,True]),('/chatbox/typing',False)]),
        ({'message':'','typing':'0'}, [('/chatbox/input',['',True,False]),('/chatbox/typing',False)]),
        ({'typing':'1'}, [('/chatbox/typing',True)]),
    ]:
        mock=FakeOsc()
        ns={'request':SimpleNamespace(method='POST',form=form),'osc_client':mock,'config':{},'render_template':lambda *a,**kw:None}
        exec(code,ns)
        assert ns['index']()=='ok'
        assert mock.sent==expected,(form,mock.sent)
    print('PASS original-core offline: normal OSC unchanged, empty-message clear, typing-only')

if __name__=='__main__':run()
