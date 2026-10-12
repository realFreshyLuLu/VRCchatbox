"""PC-side persistence for UI data. Original POST / and OSC code remains unchanged.

New endpoints are intentionally separate from the upstream Flask route.
Like the original project, these endpoints have no authentication: use trusted LAN only.
"""
import json
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request

frontend_store = Blueprint("frontend_store", __name__)
# In PyInstaller distributions, __file__ refers to the read-only _internal folder.
# User data must live beside the EXE (the original Flask core also uses this path).
_RUNTIME_BASE = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DATA_PATH = _RUNTIME_BASE / "config" / "frontend_state.json"
_LOCK = threading.RLock()
MAX_BODY = 1024 * 1024  # 1 MiB, including browser migration payload
MAX_HISTORY = 150
MAX_QUICK = 100
MAX_ENTRY = 8000
DEFAULT_PREFS = {
    "dark": False, "typing": True, "source": "zh-CN", "target": "ja",
    "format": "both", "order": "source-first", "email": "", "language": "auto", "provider": "mymemory", "endpoint": "", "model": "", "region": ""
}
PREF_FIELDS = frozenset(DEFAULT_PREFS)


def _default():
    return {"history": [], "quick": [], "prefs": dict(DEFAULT_PREFS),
            "prefsInitialized": False, "revision": 0}


def _load():
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _default()
        result = _default()
        if isinstance(raw.get("history"), list):
            result["history"] = raw["history"][:MAX_HISTORY]
        if isinstance(raw.get("quick"), list):
            result["quick"] = raw["quick"][:MAX_QUICK]
        if isinstance(raw.get("prefs"), dict):
            result["prefs"].update({k: v for k,v in raw["prefs"].items() if k in PREF_FIELDS})
        result["prefsInitialized"] = raw.get("prefsInitialized") is True
        result["revision"] = int(raw.get("revision", 0))
        return result
    except FileNotFoundError:
        return _default()
    except (OSError, ValueError, TypeError, UnicodeError):
        # Never overwrite an unreadable/corrupt file as if it were empty.
        raise RuntimeError("frontend_state.json 无法读取，请备份并修复该文件")


def _save(data):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".frontend_state_", suffix=".json", dir=DATA_PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, DATA_PATH)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _entry(value, kind):
    if not isinstance(value, dict):
        raise ValueError("条目必须是 JSON 对象")
    text = value.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_ENTRY:
        raise ValueError("条目文字为空或过长")
    ident = value.get("id")
    if not isinstance(ident, str) or not 1 <= len(ident) <= 128:
        ident = uuid.uuid4().hex
    out = {"id": ident, "text": text}
    if kind == "history":
        out["original"] = str(value.get("original", ""))[:MAX_ENTRY]
        out["translated"] = str(value.get("translated", ""))[:MAX_ENTRY]
        stamp = value.get("time", time.time()*1000)
        try:
            out["time"] = min(max(float(stamp), 0), 4102444800000)
        except (ValueError, TypeError):
            out["time"] = time.time()*1000
    return out


def _prefs(value):
    if not isinstance(value, dict):
        raise ValueError("偏好设置必须是对象")
    result = {}
    for key, val in value.items():
        if key not in PREF_FIELDS:
            continue
        if key in ("dark", "typing"):
            if not isinstance(val, bool):
                raise ValueError("布尔选项格式错误")
        elif not isinstance(val, str) or len(val) > 256:
            raise ValueError("设置文本格式错误")
        choices = {'language': {'auto', 'zh-CN', 'ja', 'en', 'ko'},
                   'provider': {'mymemory', 'deepl', 'azure', 'openai'}}
        if key in choices and val not in choices[key]:
            raise ValueError('Unsupported language' if key == 'language' else 'Unsupported provider')
        result[key] = val
    return result


def _apply(state, action, payload):
    if action == "history/add":
        row = _entry(payload.get("item"), "history")
        state["history"] = [row] + [x for x in state["history"] if x.get("id") != row["id"]]
        state["history"] = state["history"][:MAX_HISTORY]
    elif action == "history/delete":
        state["history"] = [x for x in state["history"] if x.get("id") != payload.get("id")]
    elif action == "history/clear":
        state["history"] = []
    elif action == "quick/upsert":
        row = _entry(payload.get("item"), "quick")
        existing = any(x.get("id") == row["id"] for x in state["quick"])
        if not existing and len(state["quick"]) >= MAX_QUICK:
            raise ValueError("最多可保存 100 条快捷短语")
        state["quick"] = [row] + [x for x in state["quick"] if x.get("id") != row["id"]]
    elif action == "quick/delete":
        state["quick"] = [x for x in state["quick"] if x.get("id") != payload.get("id")]
    elif action == "prefs/update":
        state["prefs"].update(_prefs(payload.get("prefs")))
        state["prefsInitialized"] = True
    elif action == "legacy/import":
        # Multiple phones may each hold old localStorage; merge by unique ID.
        for kind, limit in (("history", MAX_HISTORY), ("quick", MAX_QUICK)):
            arr = payload.get(kind, [])
            if not isinstance(arr, list) or len(arr) > 250:
                raise ValueError("迁移数据格式错误")
            seen = {x.get("id") for x in state[kind]}
            for obj in arr:
                row = _entry(obj, kind)
                if row["id"] not in seen and len(state[kind]) < limit:
                    state[kind].append(row)
                    seen.add(row["id"])
            if kind == "history":
                state[kind].sort(key=lambda x: x.get("time", 0), reverse=True)
                state[kind] = state[kind][:limit]
        if not state["prefsInitialized"] and isinstance(payload.get("prefs"), dict):
            state["prefs"].update(_prefs(payload["prefs"]))
            state["prefsInitialized"] = True
    else:
        raise ValueError("不支持的操作")


@frontend_store.route("/api/frontend-state", methods=["GET", "POST"])
def frontend_state():
    if request.method == "POST" and request.content_length is not None and request.content_length > MAX_BODY:
        return jsonify(error="请求内容过大"), 413
    if request.method == "POST" and not request.is_json:
        return jsonify(error="必须提交 JSON"), 415
    try:
        with _LOCK:
            state = _load()
            if request.method == "POST":
                payload = request.get_json(silent=True)
                if not isinstance(payload, dict):
                    return jsonify(error="请求 JSON 不正确"), 400
                try:
                    _apply(state, payload.get("action"), payload)
                except ValueError as exc:
                    return jsonify(error=str(exc)), 400
                state["revision"] += 1
                _save(state)
            response = jsonify(state)
            response.headers["Cache-Control"] = "no-store"
            return response
    except (OSError, RuntimeError) as exc:
        return jsonify(error=str(exc)), 500
