# runner/run.py
import argparse, subprocess, sys, os, yaml, time
from sdk import new_run_id, now_utc_iso, out_path, write_json, ensure_dir

PS_CANDIDATES = ["pwsh", "powershell"]  # try PowerShell Core first, then Windows PowerShell

def find_powershell():
    for exe in PS_CANDIDATES:
        if subprocess.call(["where" if os.name=="nt" else "which", exe],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            return exe
    return None

def build_cmd(plugin_name, entry, inputs, run_id, ps_exe):
    entry_path = os.path.join("plugins", plugin_name, entry)
    if entry.endswith(".py"):
        cmd = [sys.executable, entry_path]
        for k, v in (inputs or {}).items():
            cmd += [f"--{k}", str(v)]
        cmd += ["--run_id", run_id]
        return cmd
    elif entry.endswith(".ps1"):
        if not ps_exe:
            raise RuntimeError("PowerShell not found (install PowerShell Core or use Windows PowerShell).")
        cmd = [ps_exe, "-File", entry_path]
        # PowerShell prefers -Param value style
        for k, v in (inputs or {}).items():
            cmd += [f"-{k}", str(v)]
        cmd += ["-Run_Id", run_id]
        return cmd
    else:
        # generic executable
        cmd = [entry_path]
        for k, v in (inputs or {}).items():
            cmd += [f"--{k}", str(v)]
        cmd += ["--run_id", run_id]
        return cmd

def run_job(job, run_id, ps_exe):
    plugin = job["plugin"]
    # read plugin.yaml (optional, but nice for entry name)
    meta_path = os.path.join("plugins", plugin, "plugin.yaml")
    if not os.path.exists(meta_path):
        raise FileNotFoundError(f"Missing {meta_path}")
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = yaml.safe_load(f)

    entry = meta.get("entry")
    if not entry:
        raise ValueError(f"plugins/{plugin}/plugin.yaml missing 'entry'")

    inputs = job.get("inputs", {})
    timeout = meta.get("timeout_sec", 120)
    retries = int(meta.get("retries", 0))

    # where to write JSONL
    outfile = out_path(plugin, run_id)

    for attempt in range(retries + 1):
        start = time.time()
        try:
            cmd = build_cmd(plugin, entry, inputs, run_id, ps_exe)
            print(f"[runner] {plugin} -> {cmd}")
            with open(outfile, "ab") as f:  # append bytes; we write plugin stdout raw
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    stdout, stderr = proc.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    stdout, stderr = proc.communicate()
                    raise TimeoutError(f"{plugin} timed out after {timeout}s")

                # append stdout to JSONL file as-is (plugins emit one JSON per line)
                if stdout:
                    f.write(stdout if isinstance(stdout, bytes) else stdout.encode("utf-8"))

                if proc.returncode != 0:
                    raise RuntimeError(f"{plugin} failed (exit {proc.returncode}): {stderr.decode('utf-8', 'ignore')}")
            dur = int((time.time() - start) * 1000)
            return {"plugin": plugin, "ok": True, "duration_ms": dur, "outfile": outfile}
        except Exception as e:
            print(f"[runner] {plugin} attempt {attempt+1} failed: {e}")
            if attempt >= retries:
                return {"plugin": plugin, "ok": False, "error": str(e)}

def main():
    ap = argparse.ArgumentParser(description="Modular extractor runner")
    ap.add_argument("--config", default="config/inventory.yaml")
    args = ap.parse_args()

    ensure_dir("out"); ensure_dir("state"); ensure_dir("out/_runs")

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    run_id = new_run_id()
    ps_exe = find_powershell()

    results = []
    started = now_utc_iso()
    for job in cfg.get("jobs", []):
        res = run_job(job, run_id, ps_exe)
        results.append(res)

    finished = now_utc_iso()
    meta = {
        "run_id": run_id,
        "started_at": started,
        "finished_at": finished,
        "results": results
    }
    write_json(os.path.join("out", "_runs", f"{run_id}.meta.json"), meta)
    print(f"[runner] done. run_id={run_id}")

if __name__ == "__main__":
    main()
