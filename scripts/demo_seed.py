"""Safe demo setup helper.

The hackathon demo fixtures live in the frontend's /demo route. This script
intentionally does not seed fabricated proofs or mark real decisions VERIFIED.
Use --check-api to check that the lender API is reachable without mutating it.
"""
import argparse
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-api", action="store_true", help="Check /healthz without writing data")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Lender API base URL")
    args = parser.parse_args()
    if not args.check_api:
        print("Demo fixtures are isolated in the browser at http://localhost:3000/demo.")
        print("No fake proof payloads were posted and no backend records were changed.")
        print("Pass --check-api to verify the lender health endpoint without mutating data.")
        return 0
    url = args.base_url.rstrip("/") + "/healthz"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            print(f"GET {url} -> HTTP {response.status}")
            print(response.read().decode("utf-8", errors="replace"))
            return 0 if response.status == 200 else 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"Lender API unavailable at {url}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
