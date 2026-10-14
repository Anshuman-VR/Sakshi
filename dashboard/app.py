import sys, json, time, os
from pathlib import Path
from flask import Flask, render_template_string, request, jsonify

sys.path.insert(0, str(Path(__file__).parent.parent))
from gateway.gateway import SakshiGateway
from verifier.verifier import verify_decision

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
        rec = gateway.decide(
            str(d.get('application_id') or ('APP-' + str(int(time.time()*1000))[-8:])), features)
        return jsonify(rec)
    except (TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid application data: {e}"}), 400
    except Exception as e:
        app.logger.exception('Decision processing failed')
        return jsonify({"error": "Decision processing failed"}), 500

@app.route('/api/verify/<app_id>')
def verify(app_id):
    return jsonify(verify_decision(app_id))

@app.route('/api/stats')
def stats():
    rp   = Path(__file__).parent.parent / 'gateway' / 'decision_records.jsonl'
    recs = []
    if rp.exists():
        for line in rp.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                recs.append({k: r.get(k) for k in [
                    'application_id','decision','credit_score','record_hash',
                    'model_name','model_version','timestamp','prob_default']})
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

@app.route('/api/registry')
def registry():
    reg = dict(gateway.registry)
    reg.pop('onnx_path', None)
    return jsonify(reg)

if __name__ == '__main__':
    print(f"[Sakshi] http://0.0.0.0:{os.environ.get('PORT', '9000')}")
    app.run(port=int(os.environ.get('PORT', '9000')), host='0.0.0.0', debug=False)
