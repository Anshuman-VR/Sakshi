import os, json, hashlib, datetime, pickle, threading, secrets
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import numpy as np
from gateway.adapters import OnnxProbabilityAdapter
from gateway.explanations import ShapLinearAdapter

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
        self.model_adapter = self._load_model()
        self.explainer = ShapLinearAdapter(GATEWAY_DIR.parent / 'models' / 'shap_explainer.pkl')
        self.pending_records = self._recover_pending_records()
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

    def _recover_pending_records(self):
        """Recover signed records that were persisted before their Merkle batch was published."""
        witnessed = set()
        if WITNESS_LOG.exists():
            for line in WITNESS_LOG.read_text().splitlines():
                if not line.strip(): continue
                try: witnessed.update(json.loads(line).get('leaves', []))
                except (json.JSONDecodeError, TypeError): continue
        pending = []
        if RECORDS_PATH.exists():
            for line in RECORDS_PATH.read_text().splitlines():
                if not line.strip(): continue
                try: record = json.loads(line)
                except json.JSONDecodeError: continue
                digest = record.get('record_hash')
                if digest and digest not in witnessed and digest not in pending:
                    pending.append(digest)
        return pending

    def _load_model(self):
        return OnnxProbabilityAdapter(self.registry, GATEWAY_DIR.parent)

    def decide(self, application_id, features):
        feat_names  = self.registry['features']
        policy      = self.registry['policy']
        feat_labels = self.registry.get('feature_labels', {})

        if features.get('age', 99) < policy.get('min_age', 18):
            return self._policy_reject(application_id, "Does not meet minimum age requirement")
        if features.get('credit_amount', 0) > policy.get('max_credit_amount', 1e9):
            return self._policy_reject(application_id, "Requested amount exceeds policy limit")

        vec = [float(features.get(f, 0.0)) for f in feat_names]
        # Four random private nonce dimensions make the public Poseidon commitment
        # resistant to offline guessing of low-entropy borrower feature vectors.
        nonce = [secrets.randbelow(8192) for _ in range(int(self.registry.get('zk_nonce_dimensions', 4)))]
        X_features = np.array([vec], dtype=np.float32)
        X_model = np.array([vec + nonce], dtype=np.float32)
        raw_probability = self.model_adapter.predict_default_probability(X_model)
        shap_values = self.explainer.explain(X_features, features, feat_names, feat_labels)

        from zkproof.prove import prove_private_evaluation
        zk_proof = prove_private_evaluation(features, application_id, expected_probability=raw_probability, nonce=nonce)
        # Use the public, quantized output emitted by the verified proof as the canonical result.
        prob_default = float(zk_proof['prob_default'])
        input_commitment = zk_proof['input_commitment']
        decision = 'APPROVE' if prob_default < policy.get('approve_threshold', 0.5) else 'REJECT'
        score = round((1 - prob_default) * 100)

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
            "zk_proof":         zk_proof,
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
