"""Safe demo setup and seeding helper.

Checks that the lender API is reachable, and seeds the initial verified
policy, model, and prime-borrower decision record onto the tamper-evident ledger.
"""
import argparse
import json
import urllib.error
import urllib.request


def check_health(base_url: str) -> bool:
    url = base_url.rstrip("/") + "/healthz"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            print(f"[HEALTH] GET {url} -> HTTP {response.status}")
            print("         " + response.read().decode("utf-8", errors="replace").strip())
            return response.status == 200
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[ERROR] Lender API unavailable at {url}: {exc}")
        return False


def seed_demo(base_url: str) -> bool:
    url = base_url.rstrip("/") + "/v1/demo/apply"
    payload = json.dumps({"persona": "priya"}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"[SEED] POST {url} -> HTTP {response.status}")
            data = json.loads(response.read().decode("utf-8"))
            print(f"       Decision ID:    {data.get('decision_id')}")
            print(f"       Status:         {data.get('status')} ({data.get('decision_label')})")
            print(f"       Ledger Seq:     {data.get('ledger_seq')}")
            print(f"       Policy ID:      {data.get('policy_id')}")
            print(f"       Model Commit:   {data.get('model_commitment')[:18]}...")
            return data.get("status") == "VERIFIED"
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[ERROR] Failed to seed demo decision: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Check /healthz without seeding data")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Lender API base URL")
    args = parser.parse_args()

    healthy = check_health(args.base_url)
    if not healthy:
        return 1

    if args.check_only:
        print("Health check passed. No records were modified.")
        return 0

    print("\nExecuting live conformance verification for Priya Sharma (Prime Salaried)...")
    success = seed_demo(args.base_url)
    if success:
        print("\nDemo environment successfully seeded! Ready for presentation.")
        print(f"Dashboard available at: {args.base_url}/")
        print(f"Borrower portal at:     {args.base_url}/borrower")
        print(f"Audit ledger at:        {args.base_url}/ledger")
        print(f"Interactive lab at:     {args.base_url}/demo")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
