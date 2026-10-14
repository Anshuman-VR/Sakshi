"""
Sakshi Verifier
Given a decision record, independently verifies:
1. Signature validity (was this signed by the registered gateway?)
2. Merkle inclusion (is this record in a published batch?)
3. Record integrity (does the hash match?)

An auditor, lender, or ombudsman runs this — no model or raw data needed.
"""
import json, hashlib, sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

GATEWAY_DIR  = Path(__file__).parent.parent / 'gateway'
PUB_KEY_PATH = GATEWAY_DIR / 'keys' / 'gateway_public.pem'
RECORDS_PATH = GATEWAY_DIR / 'decision_records.jsonl'
WITNESS_LOG  = GATEWAY_DIR / 'merkle_witness.jsonl'


def verify_decision(application_id: str) -> dict:
    """Full verification of a decision by application ID."""
    result = {
        "application_id": application_id,
        "checks": {}
    }

    # ── Step 1: Find the record ───────────────────────────────────────────────
    record = None
    if RECORDS_PATH.exists():
        with open(RECORDS_PATH) as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get('application_id') == application_id:
                    record = r
                    break

    if record is None:
        result['verdict'] = '❌ NOT FOUND'
        result['message'] = f'No record found for {application_id}'
        return result

    result['record'] = {
        "decision":      record.get('decision'),
        "credit_score":  record.get('credit_score'),
        "timestamp":     record.get('timestamp'),
        "model_version": record.get('model_version'),
        "model_name":    record.get('model_name'),
    }

    # ── Step 2: Verify signature ──────────────────────────────────────────────
    try:
        with open(PUB_KEY_PATH, 'rb') as f:
            public_key = serialization.load_pem_public_key(f.read())

        # Reconstruct the signed payload (record without signature and record_hash)
        signed_record = {k: v for k, v in record.items()
                         if k not in ('signature', 'record_hash')}
        record_bytes = json.dumps(signed_record, sort_keys=True).encode()
        signature = bytes.fromhex(record['signature'])

        public_key.verify(
            signature, record_bytes,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        result['checks']['signature'] = '✅ Valid — signed by registered gateway'
    except InvalidSignature:
        result['checks']['signature'] = '❌ INVALID — signature does not match'
    except Exception as e:
        result['checks']['signature'] = f'⚠️ Error: {e}'

    # ── Step 3: Verify record hash integrity ──────────────────────────────────
    try:
        signed_record = {k: v for k, v in record.items()
                         if k not in ('signature', 'record_hash')}
        record_bytes = json.dumps(signed_record, sort_keys=True).encode()
        computed_hash = hashlib.sha256(record_bytes).hexdigest()
        stored_hash   = record.get('record_hash', '')
        if computed_hash == stored_hash:
            result['checks']['record_integrity'] = f'✅ Hash matches — record unaltered ({computed_hash[:16]}…)'
        else:
            result['checks']['record_integrity'] = f'❌ HASH MISMATCH — record may have been tampered'
    except Exception as e:
        result['checks']['record_integrity'] = f'⚠️ Error: {e}'

    # ── Step 4: Verify Merkle inclusion ──────────────────────────────────────
    record_hash = record.get('record_hash', '')
    try:
        found = False
        if WITNESS_LOG.exists():
            with open(WITNESS_LOG) as f:
                for line in f:
                    if not line.strip():
                        continue
                    batch = json.loads(line)
                    if record_hash in batch.get('leaves', []):
                        # Verify the Merkle path
                        computed_root = _verify_merkle_path(record_hash, batch['leaves'])
                        if computed_root == batch['merkle_root']:
                            result['checks']['merkle_inclusion'] = (
                                f'✅ Included in batch {batch["batch_id"]} — '
                                f'Merkle root verified ({batch["merkle_root"][:16]}…)'
                            )
                        else:
                            result['checks']['merkle_inclusion'] = '❌ Merkle path INVALID — batch may be corrupted'
                        found = True
                        break
        if not found:
            result['checks']['merkle_inclusion'] = '⚠️ Record not yet in a published batch (may be pending)'
    except Exception as e:
        result['checks']['merkle_inclusion'] = f'⚠️ Error: {e}'

    # ── Final verdict ─────────────────────────────────────────────────────────
    checks = result['checks']
    all_pass = all('✅' in v for v in checks.values())
    any_fail = any('❌' in v for v in checks.values())
    if all_pass:
        result['verdict'] = '✅ VERIFIED — Decision is authentic and unaltered'
    elif any_fail:
        result['verdict'] = '❌ VERIFICATION FAILED — One or more checks failed'
    else:
        result['verdict'] = '⚠️ PARTIAL — Some checks inconclusive'

    return result


def _verify_merkle_path(target_hash: str, leaves: list) -> str:
    """Recompute Merkle root from leaves to verify inclusion."""
    nodes = [hashlib.sha256(h.encode()).hexdigest() for h in leaves]
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        nodes = [hashlib.sha256((nodes[i] + nodes[i+1]).encode()).hexdigest()
                 for i in range(0, len(nodes), 2)]
    return nodes[0]


def tamper_test(application_id: str):
    """Demonstrate tamper detection by modifying a record and re-verifying."""
    print(f"\n[Tamper Test] Simulating record modification for {application_id}…")
    lines = []
    modified = False
    with open(RECORDS_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get('application_id') == application_id and not modified:
                original = r['decision']
                r['decision'] = 'APPROVE' if original == 'REJECT' else 'REJECT'
                r['credit_score'] = 0.99
                print(f"  Modified: {original} → {r['decision']}")
                modified = True
            lines.append(json.dumps(r))

    # Write tampered file temporarily
    tampered_path = RECORDS_PATH.parent / 'decision_records_tampered.jsonl'
    with open(tampered_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    # Swap and verify
    import shutil
    shutil.copy(RECORDS_PATH, RECORDS_PATH.parent / 'decision_records_backup.jsonl')
    shutil.copy(tampered_path, RECORDS_PATH)
    print("  Running verification on tampered record…")
    result = verify_decision(application_id)
    # Restore original
    shutil.copy(RECORDS_PATH.parent / 'decision_records_backup.jsonl', RECORDS_PATH)
    return result


if __name__ == '__main__':
    print("=" * 60)
    print("SAKSHI VERIFIER — Independent Decision Verification")
    print("=" * 60)

    for app_id in ['APP-001', 'APP-002', 'APP-003']:
        print(f"\n── Verifying {app_id} ─────────────────────────────────")
        result = verify_decision(app_id)
        print(f"Decision: {result.get('record', {}).get('decision', 'N/A')} | "
              f"Score: {result.get('record', {}).get('credit_score', 'N/A')}")
        for check, status in result.get('checks', {}).items():
            print(f"  {check}: {status}")
        print(f"\n  VERDICT: {result['verdict']}")

    # Tamper demonstration
    print("\n" + "=" * 60)
    print("TAMPER DETECTION DEMONSTRATION")
    print("=" * 60)
    tampered_result = tamper_test('APP-002')
    for check, status in tampered_result.get('checks', {}).items():
        print(f"  {check}: {status}")
    print(f"\n  VERDICT: {tampered_result['verdict']}")
    print("\n✅ Verifier demo complete.")
