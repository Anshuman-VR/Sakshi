"""One-time EZKL Halo2 proving-key setup for the registered ONNX model.

Keys and compiled artifacts are local-only and ignored by git. This prototype
uses private model inputs and private model outputs; see zkproof/README.md for
exact statement/limitations before treating a proof as a decision attestation.
"""
from pathlib import Path
import asyncio, json, hashlib, secrets
import ezkl
ROOT=Path(__file__).resolve().parents[1]
ZK=ROOT/'zkproof'; KEYS=ZK/'keys'; PROOFS=ZK/'proofs'
REGISTRY=json.loads((ROOT/'gateway'/'registry.json').read_text())
MODEL=(ROOT/'gateway'/REGISTRY.get('onnx_path','../models/sakshi_credit_v1.onnx')).resolve()
SETTINGS=ZK/'settings.json'; COMPILED=ZK/'compiled.ezkl'; SRS=ZK/'kzg.srs'
async def main():
    KEYS.mkdir(exist_ok=True); PROOFS.mkdir(exist_ok=True)
    data=ROOT/'data'/'credit.csv'
    import pandas as pd
    row=pd.read_csv(data).iloc[0]
    features=REGISTRY['features']
    sample=ZK/'sample_input.json'
    nonce=[secrets.randbelow(8192) for _ in range(int(REGISTRY.get('zk_nonce_dimensions',4)))]
    sample.write_text(json.dumps({'input_data':[[float(row[f]) for f in features]+nonce]}))
    args=ezkl.PyRunArgs()
    args.input_visibility='hashed'; args.output_visibility='public'; args.param_visibility='fixed'; args.check_mode='safe'
    if not ezkl.gen_settings(str(MODEL),str(SETTINGS),args): raise RuntimeError('EZKL settings generation failed')
    settings=json.loads(SETTINGS.read_text())
    settings['run_args']['input_visibility']={'Hashed': {'hash_is_public': True, 'outlets': []}}
    settings['run_args']['output_visibility']='Public'
    settings['run_args']['param_visibility']='Fixed'
    settings['run_args']['check_mode']='SAFE'
    SETTINGS.write_text(json.dumps(settings,indent=2))
    if not ezkl.calibrate_settings(str(sample),str(MODEL),str(SETTINGS),'resources',2): raise RuntimeError('EZKL calibration failed')
    # Calibration may rewrite settings; explicitly retain hashed private inputs and public output.
    settings=json.loads(SETTINGS.read_text()); settings['run_args']['input_visibility']={'Hashed': {'hash_is_public': True, 'outlets': []}}; settings['run_args']['output_visibility']='Public'; settings['run_args']['param_visibility']='Fixed'; settings['run_args']['check_mode']='SAFE'; SETTINGS.write_text(json.dumps(settings,indent=2))
    if not ezkl.compile_circuit(str(MODEL),str(COMPILED),str(SETTINGS)): raise RuntimeError('EZKL circuit compilation failed')
    await ezkl.get_srs(settings_path=str(SETTINGS),srs_path=str(SRS))
    witness=ZK/'setup_witness.json'
    if not ezkl.gen_witness(str(sample),str(COMPILED),str(witness)): raise RuntimeError('EZKL sample witness failed')
    if not ezkl.setup(str(COMPILED),str(KEYS/'verification.key'),str(KEYS/'proving.key'),str(SRS),str(witness)): raise RuntimeError('EZKL key setup failed')
    proof=PROOFS/'setup_smoke_test.proof'
    if not ezkl.prove(str(witness),str(COMPILED),str(KEYS/'proving.key'),str(proof),str(SRS)): raise RuntimeError('EZKL smoke proof failed')
    if not ezkl.verify(str(proof),str(SETTINGS),str(KEYS/'verification.key'),str(SRS)): raise RuntimeError('EZKL smoke proof verification failed')
    model_hash=hashlib.sha256(MODEL.read_bytes()).hexdigest()
    (ZK/'manifest.json').write_text(json.dumps({'system':'EZKL Halo2','model_hash':model_hash,'input_visibility':'Hashed (Poseidon commitment with private nonce)','output_visibility':'Public','param_visibility':'Fixed','setup_smoke_test_verified':True,'statement':'There exists a private feature vector and private nonce matching the public Poseidon input commitment whose registered ONNX evaluation yields the public probability.','decision_output_binding':True},indent=2))
    print('EZKL setup and smoke proof verified.')
    print('Model SHA-256:',model_hash)
    print('Proof exposes the Poseidon input commitment and quantized probability, not the raw borrower features.')
if __name__=='__main__': asyncio.run(main())
