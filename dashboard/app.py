import sys, json, time, os
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify, send_file, abort

sys.path.insert(0, str(Path(__file__).parent.parent))
from gateway.gateway import SakshiGateway
from verifier.verifier import verify_decision
from zkproof.prove import verify_proof

app     = Flask(__name__)
gateway = SakshiGateway()

@app.route('/')
def index():
    return open(Path(__file__).parent / 'index.html').read()

@app.route('/api/decide', methods=['POST'])
def decide():
    d   = request.json or {}
    try:
        features = d.get('features', {})
        if not isinstance(features, dict):
            return jsonify({"error": "features must be a JSON object"}), 400
        for key in ('age', 'credit_amount', 'duration_months'):
            if key in features and float(features[key]) < 0:
                return jsonify({"error": f"{key} cannot be negative"}), 400
        raw_id = d.get('application_id')
        if raw_id in (None, ''):
            app_id = int(time.time_ns() // 1_000_000)
        else:
            if isinstance(raw_id, bool) or not str(raw_id).isdigit():
                return jsonify({"error": "application_id must contain digits only"}), 400
            app_id = int(raw_id)
        for key in ('checking_account', 'credit_history', 'employment_years', 'savings_account'):
            if key in features and not float(features[key]).is_integer():
                return jsonify({"error": f"{key} must be a category code"}), 400
        rec = gateway.decide(app_id, features)
        return jsonify(rec)
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid application data: {e}"}), 400
    except Exception as e:
        app.logger.exception('Decision processing failed')
        return jsonify({"error": "Decision processing failed"}), 500

@app.route('/api/zkproof/file/<app_id>')
def download_zkproof(app_id):
    if not app_id.isdigit():
        return jsonify({"error": "application ID must be numeric"}), 400
    proof_path = Path(__file__).parent.parent / 'zkproof' / 'proofs' / f'{app_id}.proof'
    records_path = Path(__file__).parent.parent / 'gateway' / 'decision_records.jsonl'
    expected_hash = None
    if records_path.exists():
        for line in records_path.read_text().splitlines():
            if not line.strip(): continue
            record = json.loads(line)
            if str(record.get('application_id')) == app_id:
                expected_hash = (record.get('zk_proof') or {}).get('proof_hash')
    if not proof_path.exists() or not expected_hash:
        return jsonify({"error": "No proof artifact for this application"}), 404
    import hashlib
    if hashlib.sha256(proof_path.read_bytes()).hexdigest() != expected_hash:
        return jsonify({"error": "Proof artifact hash does not match the signed record"}), 409
    return send_file(proof_path, as_attachment=True, download_name=f'sakshi-{app_id}-proof.json', mimetype='application/json')

@app.route('/api/zkproof/public-settings')
def zk_public_settings():
    return send_file(Path(__file__).parent.parent / 'zkproof' / 'settings.json', mimetype='application/json')

@app.route('/api/zkproof/verification-key')
def zk_verification_key():
    return send_file(Path(__file__).parent.parent / 'zkproof' / 'keys' / 'verification.key', mimetype='application/json')

@app.route('/api/zkproof/srs')
def zk_srs():
    return send_file(Path(__file__).parent.parent / 'zkproof' / 'kzg.srs', as_attachment=True, download_name='sakshi-kzg.srs', mimetype='application/octet-stream')

@app.route('/api/zkproof/<app_id>')
def verify_zkproof(app_id):
    if not app_id.isdigit():
        return jsonify({"verified": False, "error": "application ID must be numeric"}), 400
    records_path = Path(__file__).parent.parent / 'gateway' / 'decision_records.jsonl'
    record = None
    if records_path.exists():
        for line in records_path.read_text().splitlines():
            if line.strip():
                candidate = json.loads(line)
                if str(candidate.get('application_id')) == app_id:
                    record = candidate
    if record is None:
        return jsonify({"verified": False, "error": "Decision record not found"}), 404
    zk = record.get('zk_proof') or {}
    result = verify_proof(int(app_id), record.get('input_commitment'), record.get('prob_default'), record.get('model_hash'))
    import hashlib
    proof_path = Path(__file__).parent.parent / 'zkproof' / 'proofs' / f'{app_id}.proof'
    result['proof_hash_matches_record'] = bool(proof_path.exists() and hashlib.sha256(proof_path.read_bytes()).hexdigest() == zk.get('proof_hash'))
    result['verified'] = bool(result.get('verified') and result['proof_hash_matches_record'] and zk.get('decision_output_binding'))
    return jsonify(result)

@app.route('/api/verify/<app_id>')
def verify(app_id):
    if not app_id.isdigit():
        return jsonify({"error": "application ID must be numeric"}), 400
    gateway.flush_batch()
    return jsonify(verify_decision(app_id))

@app.route('/api/stats')
def stats():
    rp   = Path(__file__).parent.parent / 'gateway' / 'decision_records.jsonl'
    recs = []
    if rp.exists():
        for line in rp.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get('model_hash') != gateway.registry.get('model_hash') or not str(r.get('application_id', '')).isdigit():
                    continue
                recs.append({k: r.get(k) for k in [
                    'application_id','decision','credit_score','record_hash',
                    'model_name','model_version','timestamp','prob_default','zk_proof']})
    return jsonify({"total": len(recs), "records": list(reversed(recs))})

@app.route('/api/batches')
def batches():
    wp = Path(__file__).parent.parent / 'gateway' / 'merkle_witness.jsonl'
    count = sum(1 for l in wp.read_text().splitlines() if l.strip()) if wp.exists() else 0
    return jsonify({"count": count})

@app.route('/api/flush', methods=['POST'])
def flush():
    gateway.flush_batch()
    return jsonify({"ok": True, "message": "Pending records published to the local Merkle witness log"})

@app.route('/api/metrics')
def metrics():
    mp = Path(__file__).parent.parent / 'models' / 'evaluation_metrics.json'
    if not mp.exists():
        return jsonify({"error": "Model evaluation metrics not found"}), 404
    return jsonify(json.loads(mp.read_text()))

@app.route('/api/registry')
def registry():
    reg = dict(gateway.registry)
    reg.pop('onnx_path', None)
    return jsonify(reg)

if __name__ == '__main__':
    print(f"[Sakshi] http://0.0.0.0:{os.environ.get('PORT', '9000')}")
    app.run(port=int(os.environ.get('PORT', '9000')), host='0.0.0.0', debug=False)
