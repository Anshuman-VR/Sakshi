import hashlib, json, re, unittest, secrets, time
from pathlib import Path
import numpy as np
import pandas as pd
import onnxruntime as ort

ROOT=Path(__file__).resolve().parents[1]

class SakshiPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=json.loads((ROOT/'gateway'/'registry.json').read_text())
        cls.data=pd.read_csv(ROOT/'data'/'credit.csv')

    def test_real_dataset_schema_and_target(self):
        self.assertEqual(len(self.data),1000)
        self.assertEqual(int(self.data['default'].sum()),300)
        self.assertEqual(self.registry['features'],[c for c in self.data.columns if c!='default'])
        self.assertIn('Statlog (German Credit Data)',(ROOT/'data'/'DATASET.md').read_text())

    def test_no_synthetic_fallback(self):
        script=(ROOT/'models'/'train_model.py').read_text()
        self.assertNotIn('generate_synthetic_credit_data',script)
        self.assertIn('raise FileNotFoundError',script)

    def test_registered_model_hash_and_probability(self):
        model=ROOT/'models'/'sakshi_credit_v1.onnx'
        self.assertEqual(hashlib.sha256(model.read_bytes()).hexdigest(),self.registry['model_hash'])
        session=ort.InferenceSession(str(model),providers=['CPUExecutionProvider'])
        row=self.data[self.registry['features']].iloc[[0]].to_numpy(dtype=np.float32)
        row=np.concatenate([row,np.zeros((1,int(self.registry.get('zk_nonce_dimensions',4))),dtype=np.float32)],axis=1)
        prob=float(session.run(None,{session.get_inputs()[0].name:row})[0].reshape(-1)[0])
        self.assertGreaterEqual(prob,0.0); self.assertLessEqual(prob,1.0)

    def test_metrics_present(self):
        m=json.loads((ROOT/'models'/'evaluation_metrics.json').read_text())
        for k in ['accuracy','roc_auc','average_precision','brier_score','confusion_matrix']:
            self.assertIn(k,m['test'])
        self.assertIn('test_roc_auc',m['cross_validation_5_fold'])


    def test_zkproof_binds_private_input_commitment_and_public_output(self):
        required=[ROOT/'zkproof'/'compiled.ezkl',ROOT/'zkproof'/'kzg.srs',ROOT/'zkproof'/'keys'/'proving.key',ROOT/'zkproof'/'keys'/'verification.key']
        if not all(p.exists() for p in required): self.skipTest('Run python3 zkproof/setup.py first')
        from gateway.adapters import OnnxProbabilityAdapter
        from zkproof.prove import prove_private_evaluation, verify_proof
        row=self.data.iloc[0]
        features={k:float(row[k]) for k in self.registry['features']}
        nonce=[secrets.randbelow(8192) for _ in range(int(self.registry.get('zk_nonce_dimensions',4)))]
        x=np.array([[features[k] for k in self.registry['features']]+nonce],dtype=np.float32)
        raw=OnnxProbabilityAdapter(self.registry,ROOT).predict_default_probability(x)
        app_id=int(time.time_ns()%9000000000000000)+1000000000000000
        proof=prove_private_evaluation(features,app_id,expected_probability=raw,nonce=nonce)
        checked=verify_proof(app_id,proof['input_commitment'],round(proof['prob_default'],4),self.registry['model_hash'])
        self.assertTrue(proof['verified'])
        self.assertTrue(proof['decision_output_binding'])
        self.assertTrue(checked['verified'])
        self.assertTrue(checked['input_commitment_matches'])
        self.assertTrue(checked['output_matches_record'])
        (ROOT/'zkproof'/'proofs'/f'{app_id}.proof').unlink(missing_ok=True)

    def test_frontend_has_no_emoji_and_numeric_ids(self):
        html=(ROOT/'dashboard'/'index.html').read_text()
        self.assertIsNone(re.search(r'[\U0001F300-\U0001FAFF\U0001F1E6-\U0001F1FF\u2600-\u27BF\uFE0F]',html))
        self.assertNotIn('APP-',html)
        self.assertIn("const appId=String(Date.now())",html)

if __name__=='__main__': unittest.main()
