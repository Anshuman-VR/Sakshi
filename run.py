"""Launch Sakshi: train reproducible baseline, set up EZKL, then start dashboard."""
import os, subprocess, sys
BASE=os.path.dirname(os.path.abspath(__file__))

def run(args, description):
    print(f"\n{'='*64}\n{description}\n{'='*64}",flush=True)
    return subprocess.run([sys.executable,*args],cwd=BASE).returncode

if __name__=='__main__':
    if run(['models/train_model.py'],'Step 1: Train and evaluate the UCI German Credit baseline'):
        raise SystemExit('Training failed; dashboard not started.')
    if run(['zkproof/setup.py'],'Step 2: Compile model circuit and verify EZKL setup proof'):
        raise SystemExit('EZKL setup failed; dashboard not started.')
    print('\nStarting Sakshi at http://127.0.0.1:9000',flush=True)
    os.environ.setdefault('PORT','9000')
    os.execv(sys.executable,[sys.executable,os.path.join(BASE,'dashboard','app.py')])
