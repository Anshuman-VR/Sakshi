from policy.sign import generate_signed_policy, verify_policy


def test_policy_has_two_valid_signatures_and_hash(tmp_path):
    policy = generate_signed_policy(
        "model-commitment", "circuit-hash",
        policy_path=tmp_path / "policy.json",
        lsp_private_key_path=tmp_path / "lsp-key.pem",
        lender_private_key_path=tmp_path / "lender-key.pem",
    )
    assert verify_policy(policy)
    changed = dict(policy)
    changed["hard_rules"] = []
    assert not verify_policy(changed)


def test_checked_in_example_policy_has_valid_demo_signatures():
    from pathlib import Path
    import json
    template = json.loads((Path(__file__).resolve().parents[1] / "policy" / "example_policy.json").read_text())
    assert verify_policy(template)
    assert template["signing_mode"] == "demo-local-keys-not-production-trust"
