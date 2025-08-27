import os, glob, argparse, time, json
from datetime import datetime, timezone

def now_utc(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def iso(ts):   return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    ap.add_argument("--late_minutes", type=int, default=60)
    ap.add_argument("--run_id", required=True)
    args = ap.parse_args()

    now = time.time()
    for p in glob.glob(args.path):
        exists = os.path.exists(p)
        st = os.stat(p) if exists else None
        mtime = st.st_mtime if exists else None
        age_min = (now - mtime)/60 if mtime else None
        status = "missing" if not exists else ("late" if age_min > args.late_minutes else "on_time")
        rec = {
          "plugin":"file_age",
          "plugin_version":"1.0.0",
          "run_id": args.run_id,
          "ts": now_utc(),
          "data": {
            "path": p,
            "exists": exists,
            "mtime": iso(mtime) if mtime else None,
            "age_minutes": round(age_min,2) if age_min is not None else None,
            "status": status
          },
          "errors":[]
        }
        print(json.dumps(rec, separators=(",",":")))
