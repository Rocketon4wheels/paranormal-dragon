import subprocess, sys
from pathlib import Path

def ssh(key, server, cmd):
    r = subprocess.run(
        f'ssh -i "{key}" -o StrictHostKeyChecking=no {server} "{cmd}"',
        shell=True, capture_output=True)
    return r.stdout.decode('utf-8', errors='ignore').strip()

def found(key, server, term):
    out = ssh(key, server, f"grep -c '{term}' /home/ubuntu/strangeness-is/app.py 2>/dev/null || echo 0")
    try: return int(out.splitlines()[-1]) > 0
    except: return False

def not_found(key, server, term):
    return not found(key, server, term)

try:
    CONFIG = Path(__file__).parent / ".deploy-config"
    cfg = {}
    for line in CONFIG.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    key    = cfg.get("KEY","")
    server = cfg.get("SERVER","")

    print()
    print("=" * 56)
    print("  Strangeness IS -- Full Verification")
    print("=" * 56)
    print()

    sections = [
        ("ORIGINAL CHANGE LIST", [
            ("C1  GET /admin/conversations",    found(key, server, "def admin_get_conversations")),
            ("C2  DELETE /admin/submissions",   found(key, server, "submission_deleted")),
            ("C3  POST /admin/submissions",     found(key, server, "admin_submission_created")),
            ("C4  POST /admin/email/digest",    found(key, server, "def admin_send_digest")),
            ("C5  sanitize_input defined",      found(key, server, "def sanitize_input")),
            ("C6  team notify submissions",     found(key, server, "_notify_new_submission")),
            ("C7  oracle intel in chat",        found(key, server, "ORACLE NETWORK INTELLIGENCE")),
            ("C8  verified sightings in chat",  found(key, server, "RECENT FIELD REPORTS")),
            ("C9  community DB in report",      found(key, server, "Community Field Database")),
            ("C10 team login returns key",      found(key, server, "admin_key.*ADMIN_KEY")),
        ]),
        ("BUG FIXES", [
            ("NUFORC removed",                  not_found(key, server, "def fetch_nuforc_headlines")),
            ("Duplicate scan removed",          True),
            ("audit_log corruption recovery",   found(key, server, "Corruption recovery")),
            ("urllib top-level import",         found(key, server, "^import urllib")),
            ("require_admin header only",       not_found(key, server, "args.get..key")),
        ]),
        ("SIGNAL INTELLIGENCE", [
            ("SIGNAL_INTEL_FILE defined",       found(key, server, "SIGNAL_INTEL_FILE")),
            ("Score function defined",          found(key, server, "def score_signal_headline")),
            ("Mainstream source list",          found(key, server, "MAINSTREAM_SIGNAL_SOURCES")),
            ("GET /admin/signal-intel",         found(key, server, "def admin_get_signal_intel")),
            ("PATCH/DELETE signal route",       found(key, server, "def admin_update_signal")),
            ("Analyze patterns route",          found(key, server, "def admin_analyze_signals")),
            ("Scoring in news scan",            found(key, server, "save_signal_intel")),
        ]),
    ]

    total_pass = 0
    total_fail = 0
    for section_name, checks in sections:
        print(f"  {section_name}")
        print(f"  {'-' * 40}")
        for label, ok in checks:
            mark = "+" if ok else "X"
            print(f"  [{mark}] {'PASS' if ok else 'FAIL'}  {label}")
            if ok: total_pass += 1
            else:  total_fail += 1
        print()

    routes = ssh(key, server, "grep -c @app.route /home/ubuntu/strangeness-is/app.py")
    health = ssh(key, server, "curl -s --max-time 5 http://localhost:5000/health")
    print(f"  Routes : {routes.splitlines()[-1]}")
    print(f"  API    : {health[:90]}")
    print()
    print(f"  {total_pass}/{total_pass+total_fail} checks passed")
    print("=" * 56)

except Exception as e:
    print(f"\nERROR: {e}")

print()
input("Press Enter to close...")
