import os, sys, shutil, subprocess
from datetime import datetime
from pathlib import Path

ROOT    = Path(__file__).parent
UPLOAD  = ROOT / "upload"
ARCHIVE = UPLOAD / "archive"
CONFIG  = ROOT / ".deploy-config"
REMOTE  = "/home/ubuntu/strangeness-is"
VENV    = f"{REMOTE}/venv/bin/pip"

# Files that ALWAYS get pushed to the server on every deploy
ALWAYS_PUSH_BACKEND = ["app.py", "requirements.txt"]

def load_config():
    cfg = {}
    for line in CONFIG.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    key    = cfg.get("KEY", "")
    server = cfg.get("SERVER", "")
    if not key or not server:
        print("ERROR: .deploy-config must have KEY= and SERVER=")
        sys.exit(1)
    if not Path(key).exists():
        print(f"ERROR: SSH key not found: {key}")
        print(f"Make sure your .pem file is at: {key}")
        sys.exit(1)
    return key, server

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def ssh(key, server, command):
    r = run(f'ssh -i "{key}" -o StrictHostKeyChecking=no {server} "{command}"')
    return r.returncode == 0, r.stdout.strip()

def scp(key, server, local, remote):
    r = run(f'scp -i "{key}" -o StrictHostKeyChecking=no "{local}" {server}:{remote}')
    if r.returncode != 0:
        print(f"  ERROR uploading {local}: {r.stderr.strip()[:120]}")
    return r.returncode == 0

def collect_upload():
    skip = {"README.txt", ".gitkeep", "Thumbs.db", ".DS_Store"}
    files = []
    for f in UPLOAD.rglob("*"):
        if f.is_file() and "archive" not in f.parts and f.name not in skip:
            files.append(f)
    return files

def archive_and_copy(files):
    if not files:
        return None
    ts  = datetime.now().strftime("%Y-%m-%d_%H-%M")
    arc = ARCHIVE / ts
    arc.mkdir(parents=True, exist_ok=True)
    for f in files:
        rel  = f.relative_to(UPLOAD)
        dest = arc / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        # Copy into project
        proj_dest = ROOT / rel
        proj_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, proj_dest)
        print(f"  Copied: {rel}")
    return ts

def clear_upload(files):
    for f in files:
        f.unlink(missing_ok=True)
    for d in sorted(UPLOAD.rglob("*"), reverse=True):
        if d.is_dir() and "archive" not in str(d) and d != UPLOAD:
            try: d.rmdir()
            except: pass

def push_backend(key, server):
    print("[BACKEND] Uploading app.py and requirements.txt...")
    ok1 = scp(key, server, ROOT / "app.py",          f"{REMOTE}/app.py")
    ok2 = scp(key, server, ROOT / "requirements.txt", f"{REMOTE}/requirements.txt")
    if not ok1:
        print("  CRITICAL: app.py failed to upload — aborting restart")
        return False

    print("  Installing packages into venv...")
    ok, out = ssh(key, server, f"{VENV} install -r {REMOTE}/requirements.txt -q 2>&1 | tail -3")
    if not ok:
        print(f"  WARN: pip had issues: {out[:120]}")

    print("  Restarting service...")
    ok, out = ssh(key, server,
        "sudo systemctl restart strangeness && sleep 5 && sudo systemctl is-active strangeness")
    status = out.strip().split("\n")[-1].strip()
    if status == "active":
        print(f"  OK: Service is active")
    else:
        print(f"  ERROR: Service status: {status}")
        ok2, log = ssh(key, server, "sudo journalctl -u strangeness -n 10 --no-pager")
        print(log)
        return False

    print("  Health check...")
    ok, out = ssh(key, server, "curl -s --max-time 6 http://localhost:5000/health")
    if '"ok"' in out:
        print(f"  OK: API is live — {out[:80]}")
    else:
        print(f"  WARN: {out[:120] or 'no response'}")
    return True

def git_push():
    if run("git status").returncode != 0:
        print("  SKIP: Not a git repo. Run SETUP_GIT.bat first.")
        return
    run("git add -A")
    r = run("git diff --staged --quiet")
    if r.returncode == 0:
        print("  SKIP: No changes to push.")
        return
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    run(f'git commit -m "deploy {ts}"')
    r = run("git push origin main")
    if r.returncode != 0:
        r2 = run("git push -u origin main --force")
        if r2.returncode != 0:
            print(f"  WARN: Push failed — {r2.stderr.strip()[:120]}")
            return
    print("  OK: Pushed to GitHub. Live in ~60 seconds.")

# ── Main ──────────────────────────────────────────────────────────────────────
print()
print("=" * 50)
print("  Strangeness IS -- Deploy")
print("=" * 50)
print()

ARCHIVE.mkdir(parents=True, exist_ok=True)
key, server = load_config()

# ── Scan upload/ ──────────────────────────────────────────────────────────────
upload_files = collect_upload()

if upload_files:
    print(f"Found {len(upload_files)} file(s) in upload/:")
    for f in upload_files:
        print(f"  {f.relative_to(UPLOAD)}")
    print()

    print("[1/4] Archiving and copying to project...")
    ts = archive_and_copy(upload_files)
    print(f"  OK: Archived to upload/archive/{ts}/")
    print()
else:
    print("upload/ is empty -- pushing current project files to server.")
    print()

# ── ALWAYS push backend ───────────────────────────────────────────────────────
print("[2/4] Pushing backend to server (always)...")
if not push_backend(key, server):
    print()
    print("Backend push failed. Fix errors above and try again.")
    input("Press Enter to exit...")
    sys.exit(1)
print()

# ── Frontend push ─────────────────────────────────────────────────────────────
print("[3/4] Pushing frontend to GitHub...")
git_push()
print()

# ── Clear upload/ ─────────────────────────────────────────────────────────────
if upload_files:
    print("[4/4] Clearing upload/...")
    clear_upload(upload_files)
    print("  OK: upload/ ready for next update.")
else:
    print("[4/4] No upload files to clear.")
print()

print("=" * 50)
print("  Done!")
print("  API:   https://api.strangenessis.com/health")
print("  Site:  https://strangenessis.com")
print("  Admin: https://strangenessis.com/admin.html")
print("=" * 50)
print()
input("Press Enter to exit...")
