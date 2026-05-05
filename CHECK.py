import subprocess, sys
from pathlib import Path

CONFIG = Path(__file__).parent / ".deploy-config"
cfg = {}
for line in CONFIG.read_text().splitlines():
    if "=" in line:
        k, v = line.split("=", 1)
        cfg[k.strip()] = v.strip()
key    = cfg.get("KEY","")
server = cfg.get("SERVER","")

def ssh(cmd):
    r = subprocess.run(
        f'ssh -i "{key}" -o StrictHostKeyChecking=no {server} "{cmd}"',
        shell=True, capture_output=True, text=True)
    return r.stdout.strip()

print()
print("=" * 52)
print("  Strangeness IS -- Change List Verification")
print("=" * 52)
print()

src = ssh("cat /home/ubuntu/strangeness-is/app.py")

checks = [
    ("C1  GET /admin/conversations",    "def admin_get_conversations"   in src),
    ("C2  DELETE /admin/submissions",   "submission_deleted"            in src),
    ("C3  POST /admin/submissions",     "admin_submission_created"      in src),
    ("C4  POST /admin/email/digest",    "def admin_send_digest"         in src),
    ("C5  require_admin header only",   "request.args.get('key')"   not in src),
    ("C6  sanitize_input defined",      "def sanitize_input"            in src),
    ("C7  team notify submissions",     "_notify_new_submission"        in src),
    ("C8  oracle intel in /chat",       "ORACLE NETWORK INTELLIGENCE"   in src),
    ("C9  verified sightings in /chat", "RECENT FIELD REPORTS"          in src),
    ("C10 community DB in report",      "Community Field Database"      in src),
]

passed = 0
failed = 0
for label, ok in checks:
    status = "PASS" if ok else "FAIL"
    mark   = "+" if ok else "X"
    print(f"  [{mark}] {status}  {label}")
    if ok: passed += 1
    else:  failed += 1

routes = src.count("@app.route")
print(f"\n  [i] Routes in app.py: {routes} (should be 60)")
print()

adm = ssh("cat /home/ubuntu/strangeness-is/app.py | grep -c 'def admin'")
print(f"  [i] Admin functions: {adm.strip()}")

health = ssh("curl -s http://localhost:5000/health")
print(f"  [i] API health: {health[:80]}")

print()
print(f"  Result: {passed} passed, {failed} failed")
print("=" * 52)
print()
input("Press Enter to close...")
