import os, json, hashlib, datetime, pickle, threading
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import numpy as np
import onnxruntime as rt

GATEWAY_DIR   = Path(__file__).parent
REGISTRY_PATH = GATEWAY_DIR / 'registry.json'
KEYS_DIR      = GATEWAY_DIR / 'keys'
RECORDS_PATH  = GATEWAY_DIR / 'decision_records.jsonl'
WITNESS_LOG   = GATEWAY_DIR / 'merkle_witness.jsonl'
BATCH_SIZE    = 10

class SakshiGateway:
    def __init__(self):
        self.registry    = json.loads(REGISTRY_PATH.read_text())
        self.private_key, self.public_key = self._load_or_create_keys()
        self.ort_session = self._load_model()
        self.shap_data   = None
        self._shap_ready = threading.Event()
        self.pending_records = []
        threading.Thread(target=self._load_shap_bg, daemon=True).start()
        print(f"[Gateway] Ready. Model: {self.registry['model_name']} hash={self.registry['model_hash'][:16]}")

    def _load_or_create_keys(self):
        KEYS_DIR.mkdir(exist_ok=True)
        priv = KEYS_DIR / 'gateway_private.pem'
        pub  = KEYS_DIR / 'gateway_public.pem'
        if priv.exists():
            private_key = serialization.load_pem_private_key(priv.read_bytes(), password=None)
        else:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            priv.write_bytes(private_key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        pub.write_bytes(private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        return private_key, private_key.public_key()

    def _load_model(self):
        # Resolve the model relative to this project so the repo works outside
        # the original VirtualBox shared-folder mount too.
        onnx_path = Path(self.registry.get('onnx_path', ''))
        if not onnx_path.is_file():
            onnx_path = GATEWAY_DIR.parent / 'models' / 'sakshi_credit_v1.onnx'
        if not onnx_path.is_file():
            raise FileNotFoundError(f'ONNX model not found: {onnx_path}')
        actual = hashlib.sha256(onnx_path.read_bytes()).hexdigest()
        if actual != self.registry['model_hash']:
            raise RuntimeError("MODEL HASH MISMATCH — halting")
        return rt.InferenceSession(onnx_path)

    def _load_shap_bg(self):
        import warnings; warnings.filterwarnings('ignore')
        p = GATEWAY_DIR.parent / 'models' / 'shap_explainer.pkl'
        if p.exists():
            import shap as shap_lib
            data = pickle.loads(p.read_bytes())
            data['shap_lib'] = shap_lib
            self.shap_data = data
        self._shap_ready.set()
        print("[Gateway] SHAP explainer ready.")

    def decide(self, application_id, features):
        feat_names  = self.registry['features']
        policy      = self.registry['policy']
        feat_labels = self.registry.get('feature_labels', {})

        if features.get('age', 99) < policy.get('min_age', 18):
            return self._policy_reject(application_id, "Does not meet minimum age requirement")
        if features.get('credit_amount', 0) > policy.get('max_credit_amount', 1e9):
            return self._policy_reject(application_id, "Requested amount exceeds policy limit")

        vec = [float(features.get(f, 0.0)) for f in feat_names]
        input_commitment = hashlib.sha256(json.dumps(vec, sort_keys=True).encode()).hexdigest()
        X = np.array([vec], dtype=np.float32)
        prob_default = float(self.ort_session.run(None, {self.ort_session.get_inputs()[0].name: X})[1][0][1])
        decision = 'APPROVE' if prob_default < policy.get('approve_threshold', 0.45) else 'REJECT'
        score    = round((1 - prob_default) * 100)

        shap_values = []
        if self.shap_data:
            try:
                import warnings; warnings.filterwarnings('ignore')
                X_scaled = self.shap_data['scaler'].transform(X)
                sv = self.shap_data['explainer'].shap_values(X_scaled)
                vals = sv[0] if isinstance(sv, list) else sv[0]
                for i, fname in enumerate(feat_names):
                    shap_values.append({
                        'feature': fname,
                        'label':   feat_labels.get(fname, fname),
                        'value':   round(float(features.get(fname, 0)), 2),
                        'shap':    round(float(vals[i]), 4),
                        'impact':  'positive' if vals[i] <= 0 else 'negative'
                    })
                shap_values.sort(key=lambda x: abs(x['shap']), reverse=True)
            except: pass

        record = {
            "application_id":   application_id,
            "timestamp":        datetime.datetime.now(datetime.UTC).isoformat(),
            "model_name":       self.registry['model_name'],
            "model_version":    self.registry['version'],
            "model_hash":       self.registry['model_hash'],
            "input_commitment": input_commitment,
            "decision":         decision,
            "credit_score":     score,
            "prob_default":     round(prob_default, 4),
            "shap_values":      shap_values,
        }
        # Sign and hash the complete decision payload, including its explanation.
        # The verifier reconstructs this exact payload by removing signature/hash.
        rbytes = json.dumps(record, sort_keys=True).encode()
        sig    = self.private_key.sign(rbytes, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        record['signature']   = sig.hex()
        record['record_hash'] = hashlib.sha256(rbytes).hexdigest()

        with open(RECORDS_PATH, 'a') as f:
            f.write(json.dumps(record) + '\n')
        self.pending_records.append(record['record_hash'])
        if len(self.pending_records) >= BATCH_SIZE:
            self._publish_merkle_batch()
        return record

    def _policy_reject(self, app_id, reason):
        record = {
            "application_id": app_id,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "model_name": self.registry['model_name'],
            "model_version": self.registry['version'],
            "model_hash": self.registry['model_hash'],
            "input_commitment": hashlib.sha256(reason.encode()).hexdigest(),
            "decision": "REJECT",
            "reason": reason,
            "policy_reject": True,
            "credit_score": 0,
            "prob_default": 1.0,
            "shap_values": [],
        }
        payload = json.dumps(record, sort_keys=True).encode()
        signature = self.private_key.sign(payload, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        record['signature'] = signature.hex()
        record['record_hash'] = hashlib.sha256(payload).hexdigest()
        with open(RECORDS_PATH, 'a') as f:
            f.write(json.dumps(record) + '\n')
        self.pending_records.append(record['record_hash'])
        if len(self.pending_records) >= BATCH_SIZE:
            self._publish_merkle_batch()
        return record

    def flush_batch(self):
        if self.pending_records: self._publish_merkle_batch()

    def _publish_merkle_batch(self):
        root  = self._merkle_root(self.pending_records)
        entry = {"batch_id": hashlib.sha256(root.encode()).hexdigest()[:16],
                 "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                 "num_records": len(self.pending_records),
                 "leaves": list(self.pending_records), "merkle_root": root}
        with open(WITNESS_LOG, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        self.pending_records = []

    @staticmethod
    def _merkle_root(leaves):
        if not leaves: return hashlib.sha256(b'').hexdigest()
        nodes = [hashlib.sha256(h.encode()).hexdigest() for h in leaves]
        while len(nodes) > 1:
            if len(nodes) % 2 == 1: nodes.append(nodes[-1])
            nodes = [hashlib.sha256((nodes[i]+nodes[i+1]).encode()).hexdigest()
                     for i in range(0, len(nodes), 2)]
        return nodes[0]
