"""
Sakshi — One-command launcher
Runs the full demo: train → decide → verify → dashboard
"""
import subprocess, sys, os
BASE = os.path.dirname(__file__)

def run(cmd, desc):
    print(f"\n{'='*60}\n▶ {desc}\n{'='*60}")
    result = subprocess.run([sys.executable] + cmd, cwd=BASE)
    if result.returncode != 0:
        print(f"⚠️  Step exited with code {result.returncode}")
    return result.returncode

if __name__ == '__main__':
    run(['models/train_model.py'], 'Step 1: Train model + register hash')
    run(['gateway/gateway.py'],   'Step 2: Run 3 decisions + Merkle batch')
    run(['verifier/verifier.py'], 'Step 3: Verify decisions + tamper detection demo')
    print("\n" + "="*60)
    print("✅ Demo complete. Starting dashboard at http://localhost:5001")
    print("   Press Ctrl+C to stop")
    print("="*60 + "\n")
    os.execv(sys.executable, [sys.executable, os.path.join(BASE, 'dashboard/app.py')])
