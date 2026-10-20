"""Security tests for binding claims to EZKL public instances."""
import hashlib, json
from node.services.proof_binding import proof_instances_match, load_binding_artifacts


def test_public_instances_must_match_every_claim():
    inputs={"policy_hash":"1"*64,"C":"2"*64,"X":"3"*64,"decision":1,"threshold":0.2,"epoch":20261020}
    def chunks(v): return [str(int(v[:32],16)),str(int(v[32:],16))]
    instances=chunks(inputs["policy_hash"])+chunks(inputs["C"])+chunks(inputs["X"])+["1","205","20261020"]
    settings={"sakshi_public_input_binding":{"version":1,"threshold_scale":1024,
      "indices":{"policy_hash_hi":0,"policy_hash_lo":1,"C_hi":2,"C_lo":3,
      "X_hi":4,"X_lo":5,"decision":6,"threshold_scaled":7,"epoch":8}}}
    assert proof_instances_match({"instances":[instances]},settings,inputs,1024)
    inputs["C"]="4"*64
    assert not proof_instances_match({"instances":[instances]},settings,inputs,1024)


def test_missing_binding_schema_fails_closed():
    inputs={"policy_hash":"1"*64,"C":"2"*64,"X":"3"*64,"decision":1,"threshold":0.2,"epoch":20261020}
    assert not proof_instances_match({"instances":[["1"]]}, {}, inputs, 1024)


def test_compiled_circuit_hash_is_pinned(tmp_path):
    settings=tmp_path/"settings.json"; circuit=tmp_path/"model.compiled"; manifest=tmp_path/"binding.json"
    settings.write_text(json.dumps({"ezkl_native_setting":True}))
    circuit.write_bytes(b"compiled circuit fixture")
    correct=hashlib.sha256(circuit.read_bytes()).hexdigest()
    settings_hash=hashlib.sha256(settings.read_bytes()).hexdigest()
    manifest.write_text(json.dumps({"circuit_hash":correct,"settings_sha256":settings_hash}))
    manifest_hash=hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert load_binding_artifacts(str(settings),str(circuit),correct,settings_hash,str(manifest),manifest_hash) is not None
    assert load_binding_artifacts(str(settings),str(circuit),"0"*64,settings_hash,str(manifest),manifest_hash) is None
    assert load_binding_artifacts(str(settings),str(circuit),correct,"0"*64,str(manifest),manifest_hash) is None
    assert load_binding_artifacts(str(settings),str(circuit),correct,settings_hash,str(manifest),"0"*64) is None


def test_real_verification_fails_closed_without_artifacts(monkeypatch):
    from node.services.verifier import _real_ezkl_verify
    assert _real_ezkl_verify(b'{"instances":[]}', 'e30=', '', '', '0'*64,
                              {"policy_hash":"1"*64,"C":"2"*64,"X":"3"*64,
                               "decision":1,"threshold":0.2,"epoch":20261020}, 1024, []) is False
