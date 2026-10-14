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
                if str(r.get('application_id')) == str(application_id):
                    record = r
                    break

    if record is None:
        result['verdict'] = 'FAIL — NOT FOUND'
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
        result['checks']['signature'] = 'PASS — valid signature from registered gateway'
    except InvalidSignature:
        result['checks']['signature'] = 'FAIL — signature does not match'
    except Exception as e:
        result['checks']['signature'] = f'WARN — error: {e}'

    # ── Step 3: Verify record hash integrity ──────────────────────────────────
    try:
        signed_record = {k: v for k, v in record.items()
                         if k not in ('signature', 'record_hash')}
        record_bytes = json.dumps(signed_record, sort_keys=True).encode()
        computed_hash = hashlib.sha256(record_bytes).hexdigest()
        stored_hash   = record.get('record_hash', '')
        if computed_hash == stored_hash:
            result['checks']['record_integrity'] = f'PASS — hash matches; record unaltered ({computed_hash[:16]}…)'
        else:
            result['checks']['record_integrity'] = f'FAIL — hash mismatch; record may have been tampered'
    except Exception as e:
        result['checks']['record_integrity'] = f'WARN — error: {e}'

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
                                f'PASS — included in batch {batch["batch_id"]}; '
                                f'Merkle root verified ({batch["merkle_root"][:16]}…)'
                            )
                        else:
                            result['checks']['merkle_inclusion'] = 'FAIL — Merkle path invalid; batch may be corrupted'
                        found = True
                        break
        if not found:
            result['checks']['merkle_inclusion'] = 'WARN — record not yet in a published batch'
    except Exception as e:
        result['checks']['merkle_inclusion'] = f'WARN — error: {e}'

    # ── Step 5: Verify EZKL proof if this record carries one ──────────────────
    zk_meta = record.get('zk_proof') or {}
    if zk_meta.get('proof_hash'):
        try:
            from zkproof.prove import verify_proof
            zk_result = verify_proof(record.get('application_id'), record.get('input_commitment'), record.get('prob_default'), record.get('model_hash'))
            digest_matches = zk_result.get('proof_hash') == zk_meta.get('proof_hash')
            model_matches = zk_meta.get('model_hash') == record.get('model_hash')
            if zk_result.get('verified') and digest_matches and model_matches:
                result['checks']['zk_inference_proof'] = 'PASS — EZKL proof verifies and proof hash matches'
                if zk_meta.get('decision_output_binding', False) and zk_result.get('input_commitment_matches') and zk_result.get('output_matches_record'):
                    result['checks']['zk_output_binding'] = 'PASS — Poseidon input commitment and public probability match the signed decision record'
                    registry = json.loads((GATEWAY_DIR / 'registry.json').read_text())
                    threshold = float(registry.get('policy', {}).get('approve_threshold', 0.5))
                    expected_decision = 'APPROVE' if float(zk_result['prob_default']) < threshold else 'REJECT'
                    if expected_decision == record.get('decision'):
                        result['checks']['decision_consistency'] = 'PASS — decision matches the proof output and registered threshold'
                    else:
                        result['checks']['decision_consistency'] = 'FAIL — decision does not match the proof output and registered threshold'
                else:
                    result['checks']['zk_output_binding'] = 'FAIL — proof input/output does not match the signed decision record'
            else:
                result['checks']['zk_inference_proof'] = 'FAIL — EZKL proof, proof hash, or model hash check failed'
        except Exception as e:
            result['checks']['zk_inference_proof'] = f'WARN — EZKL verification error: {e}'
    else:
        result['checks']['zk_inference_proof'] = 'WARN — no EZKL proof attached (policy-only decision or proof unavailable)'

    # ── Final verdict ─────────────────────────────────────────────────────────
    checks = result['checks']
    any_fail = any(v.startswith('FAIL') for v in checks.values())
    all_pass = all(v.startswith('PASS') for v in checks.values())
    if all_pass:
        result['verdict'] = 'VERIFIED — decision evidence and proof checks passed'
    elif any_fail:
        result['verdict'] = 'VERIFICATION FAILED — one or more checks failed'
    else:
        result['verdict'] = 'PARTIAL — some checks are warnings or incomplete'

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
            if str(r.get('application_id')) == str(application_id) and not modified:
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

    for app_id in ['1000001', '1000002', '1000003']:
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
    tampered_result = tamper_test('1000002')
    for check, status in tampered_result.get('checks', {}).items():
        print(f"  {check}: {status}")
    print(f"\n  VERDICT: {tampered_result['verdict']}")
    print("\n✅ Verifier demo complete.")
