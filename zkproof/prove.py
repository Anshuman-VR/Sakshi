"""Create and verify an EZKL proof binding private input commitment to public probability."""
from pathlib import Path
import json, hashlib, uuid, secrets
import ezkl
ROOT=Path(__file__).resolve().parents[1]; ZK=ROOT/'zkproof'
REGISTRY=json.loads((ROOT/'gateway'/'registry.json').read_text())
MODEL=(ROOT/'gateway'/REGISTRY.get('onnx_path','../models/sakshi_credit_v1.onnx')).resolve()
COMPILED=ZK/'compiled.ezkl'; SRS=ZK/'kzg.srs'; SETTINGS=ZK/'settings.json'; VK=ZK/'keys'/'verification.key'; PK=ZK/'keys'/'proving.key'

def _decode_public_instances(instances, settings):
    if not instances or not instances[0] or len(instances[0]) < 2:
        raise RuntimeError('EZKL proof did not expose the expected input commitment and model output')
    commitment=instances[0][0]
    probability=float(ezkl.felt_to_float(instances[0][1],settings['model_output_scales'][0]))
    if not 0.0 <= probability <= 1.0:
        raise RuntimeError(f'Proof output is not a probability: {probability}')
    return commitment, probability

def prove_private_evaluation(features:dict, application_id, expected_probability=None, nonce=None):
    if not all(p.exists() for p in [COMPILED,SRS,SETTINGS,VK,PK]):
        raise RuntimeError('EZKL keys are not initialized. Run python3 zkproof/setup.py first.')
    model_hash=hashlib.sha256(MODEL.read_bytes()).hexdigest()
    if model_hash != REGISTRY['model_hash']: raise RuntimeError('ZK circuit model hash does not match the active registry.')
    vals=[float(features.get(f,0.0)) for f in REGISTRY['features']]
    nonce = list(nonce) if nonce is not None else [secrets.randbelow(8192) for _ in range(int(REGISTRY.get('zk_nonce_dimensions',4)))]
    if len(nonce) != int(REGISTRY.get('zk_nonce_dimensions',4)) or any(int(v)<0 or int(v)>8191 for v in nonce):
        raise ValueError('Invalid private nonce dimensions')
    vals.extend(float(v) for v in nonce)
    ZK.joinpath('proofs').mkdir(exist_ok=True)
    tmp=ZK/'tmp'; tmp.mkdir(exist_ok=True)
    token=uuid.uuid4().hex
    data=tmp/f'{token}.json'; witness=tmp/f'{token}.witness.json'; proof=ZK/'proofs'/f'{application_id}.proof'
    data.write_text(json.dumps({'input_data':[vals]}))
    try:
        witness_obj=ezkl.gen_witness(str(data),str(COMPILED),str(witness))
        if not witness_obj: raise RuntimeError('EZKL witness generation failed')
        proof_obj=ezkl.prove(str(witness),str(COMPILED),str(PK),str(proof),str(SRS))
        if not proof_obj: raise RuntimeError('EZKL proof generation failed')
        valid=bool(ezkl.verify(str(proof),str(SETTINGS),str(VK),str(SRS)))
        if not valid: raise RuntimeError('EZKL verifier rejected generated proof')
        settings=json.loads(SETTINGS.read_text())
        commitment, probability=_decode_public_instances(proof_obj.get('instances'),settings)
        if expected_probability is not None and abs(probability-float(expected_probability)) > 0.01:
            raise RuntimeError(f'ZK output {probability:.6f} disagrees with ONNX output {expected_probability:.6f}')
        digest=hashlib.sha256(proof.read_bytes()).hexdigest()
        return {'system':'EZKL Halo2','proof_id':str(application_id),'proof_hash':digest,'verified':True,
                'model_hash':model_hash,'input_visibility':'Hashed (Poseidon commitment with private nonce)','output_visibility':'Public',
                'statement':'There exists a private feature vector matching the public Poseidon input commitment whose registered ONNX evaluation yields the public probability.',
                'decision_output_binding':True,'input_commitment':commitment,'prob_default':probability,
                'output_scale':settings['model_output_scales'][0]}
    finally:
        for p in (data,witness):
            try: p.unlink()
            except FileNotFoundError: pass

def verify_proof(application_id, expected_input_commitment=None, expected_probability=None, expected_model_hash=None):
    proof=ZK/'proofs'/f'{application_id}.proof'
    if not proof.exists(): return {'verified':False,'error':'Proof file not found'}
    try:
        settings=json.loads(SETTINGS.read_text()); proof_obj=json.loads(proof.read_text())
        valid=bool(ezkl.verify(str(proof),str(SETTINGS),str(VK),str(SRS)))
        commitment, probability=_decode_public_instances(proof_obj.get('instances'),settings)
        digest=hashlib.sha256(proof.read_bytes()).hexdigest()
        model_hash=hashlib.sha256(MODEL.read_bytes()).hexdigest()
        commitment_matches=expected_input_commitment is None or commitment==expected_input_commitment
        output_matches=expected_probability is None or abs(probability-float(expected_probability)) <= 0.00011
        model_matches=expected_model_hash is None or model_hash==expected_model_hash
        return {'verified':bool(valid and commitment_matches and output_matches and model_matches),
                'proof_valid':valid,'input_commitment':commitment,'prob_default':probability,
                'proof_hash':digest,'system':'EZKL Halo2','decision_output_binding':True,
                'input_commitment_matches':commitment_matches,'output_matches_record':output_matches,
                'model_hash_matches':model_matches,'model_hash':model_hash}
    except Exception as exc: return {'verified':False,'error':str(exc)}
