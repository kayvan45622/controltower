# runner/sdk.py
import datetime as dt, uuid, os, json

def now_utc_iso():
    return dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def new_run_id():
    t = dt.datetime.utcnow().strftime("%Y-%m-%dT%H-%MZ")
    return f"{t}-{uuid.uuid4().hex[:4]}"

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)

def write_json(path, obj):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def out_path(plugin, run_id):
    ensure_dir("out")
    return os.path.join("out", f"{plugin}_{run_id}.jsonl")
