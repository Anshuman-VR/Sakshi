"""CLI script to reset and seed the demo database."""
import urllib.request
import json
import sys

def reset_db(base_url="http://localhost:8000"):
    url = f"{base_url.rstrip('/')}/v1/demo/reset"
    req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[RESET] HTTP {resp.status}: {data.get('message')}")
            print(f"        Baseline Decision ID: {data.get('decision_id')}")
            print(f"        Ledger Height: #{data.get('ledger_seq')}")
            return True
    except Exception as exc:
        print(f"[ERROR] Failed to reset database at {url}: {exc}")
        return False

if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    success = reset_db(base)
    sys.exit(0 if success else 1)
