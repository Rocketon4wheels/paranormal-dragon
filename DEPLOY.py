import os, sys, subprocess
from pathlib import Path

ROOT   = Path(__file__).parent
CONFIG = ROOT / ".deploy-config"
REMOTE = "/home/ubuntu/strangeness-is"
VENV   = f"{REMOTE}/venv/bin/pip"

def load_config():
    if not CONFIG.exists():
        print("ERROR: .deploy-config not found")
        input("Press Enter to exit..."); sys.exit(1)
    cfg = {}
    for line in CONFIG.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    key    = cfg.get("KEY","")
    server = cfg.get("SERVER","")
    if not Path(key).exists():
        print(f"ERROR: Key not found: {key}")
        input("Press Enter to exit..."); sys.exit(1)
    return key, server

def run(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)

def ssh(key, server, cmd):
    r = run(f'ssh -i "{key}" -o StrictHostKeyChecking=no {server} "{cmd}"')
    return r.returncode == 0, r.stdout.strip()

def scp(key, server, local, remote):
    r = run(f'scp -i "{key}" -o StrictHostKeyChecking=no "{local}" {server}:{remote}')
    return r.returncode == 0

print()
print("=" * 50)
print("  Strangeness IS -- Deploy")
print("=" * 50)
print()

key, server = load_config()

# ── Step 1: Push app.py and requirements.txt to server ────────────────────────
print("[1/3] Uploading backend to server...")
if scp(key, server, ROOT/"app.py", f"{REMOTE}/app.py"):
    print("  OK: app.py uploaded")
else:
    print("  ERROR: app.py failed"); input("Press Enter..."); sys.exit(1)

scp(key, server, ROOT/"requirements.txt", f"{REMOTE}/requirements.txt")
print("  OK: requirements.txt uploaded")

ok, out = ssh(key, server, f"{VENV} install -r {REMOTE}/requirements.txt -q 2>&1 | tail -2")
print("  OK: packages checked")

ok, out = ssh(key, server,
    "sudo systemctl restart strangeness && sleep 5 && sudo systemctl is-active strangeness")
status = out.strip().split("\n")[-1].strip()
print(f"  Service: {status}")

ok, out = ssh(key, server, "curl -s --max-time 6 http://localhost:5000/health")
if '"ok"' in out:
    print(f"  API: LIVE")
else:
    print(f"  API: {out[:80]}")
print()

# ── Step 2: Push frontend to GitHub ───────────────────────────────────────────
print("[2/3] Pushing frontend to GitHub...")
r = run("git status", cwd=ROOT)
if r.returncode != 0:
    print("  SKIP: Run SETUP_GIT.bat first to connect GitHub")
else:
    run("git add -A", cwd=ROOT)
    r = run("git diff --staged --quiet", cwd=ROOT)
    if r.returncode == 0:
        print("  No changes to push")
    else:
        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        run(f'git commit -m "deploy {ts}"', cwd=ROOT)
        r = run("git push origin main", cwd=ROOT)
        if r.returncode != 0:
            run("git push -u origin main --force", cwd=ROOT)
        print("  OK: Live on GitHub Pages in ~60 seconds")
print()

# ── Step 3: Done ──────────────────────────────────────────────────────────────
print("[3/3] Done!")
print()
print("=" * 50)
print("  API:   https://api.strangenessis.com/health")
print("  Site:  https://strangenessis.com")
print("  Admin: https://strangenessis.com/admin.html")
print("=" * 50)
print()
input("Press Enter to close...")
