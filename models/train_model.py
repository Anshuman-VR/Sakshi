"""Train a reproducible Sakshi baseline on the UCI German Credit dataset."""
from pathlib import Path
import hashlib, json, pickle
import numpy as np
import pandas as pd
import shap
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, average_precision_score, confusion_matrix,
    brier_score_loss)
import onnx
from onnx import helper, TensorProto, numpy_helper

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'data' / 'credit.csv'
MODEL_DIR = ROOT / 'models'
REGISTRY_PATH = ROOT / 'gateway' / 'registry.json'
EXPLAINER_PATH = MODEL_DIR / 'shap_explainer.pkl'
FEATURES = ['duration_months','credit_amount','installment_rate','present_residence','age',
            'existing_credits','num_dependents','checking_account','credit_history',
            'employment_years','savings_account']
FEATURE_LABELS = {
 'duration_months':'Credit duration (months)', 'credit_amount':'Credit amount (historical dataset units)',
 'installment_rate':'Installment rate (% of disposable income)', 'present_residence':'Years at current residence',
 'age':'Age (years)', 'existing_credits':'Existing credits at this bank',
 'num_dependents':'People supported', 'checking_account':'Checking account category',
 'credit_history':'Credit history category', 'employment_years':'Employment duration category',
 'savings_account':'Savings account category'}

if not DATA_PATH.exists():
    raise FileNotFoundError('Missing data/credit.csv. Restore it from the official UCI German Credit dataset; synthetic fallback is intentionally disabled.')
df = pd.read_csv(DATA_PATH)
if not set(FEATURES + ['default']).issubset(df.columns):
    raise ValueError('Dataset schema does not match the documented UCI-derived Sakshi feature subset.')
X = df[FEATURES].to_numpy(dtype=np.float32)
y = df['default'].to_numpy(dtype=np.int64)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
pipeline = Pipeline([('scaler', StandardScaler()), ('clf', LogisticRegression(max_iter=2000, C=0.5, class_weight='balanced', random_state=42))])
pipeline.fit(X_train, y_train)
prob_train = pipeline.predict_proba(X_train)[:,1]
prob_test = pipeline.predict_proba(X_test)[:,1]
threshold = 0.5
pred_train, pred_test = (prob_train >= threshold).astype(int), (prob_test >= threshold).astype(int)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_validate(pipeline, X, y, cv=cv, scoring={
 'accuracy':'accuracy','balanced_accuracy':'balanced_accuracy','precision':'precision','recall':'recall','f1':'f1','roc_auc':'roc_auc','average_precision':'average_precision'}, n_jobs=1)
metrics = {
 'dataset':'UCI Statlog German Credit Data (1994)', 'n_rows':int(len(df)), 'n_features':len(FEATURES),
 'target_definition':'default=1 for UCI class 2 (bad risk), default=0 for UCI class 1 (good risk)',
 'split':{'method':'stratified train/test','random_state':42,'test_size':0.2,'train_rows':len(y_train),'test_rows':len(y_test)},
 'threshold':threshold,
 'train':{'accuracy':accuracy_score(y_train,pred_train),'balanced_accuracy':balanced_accuracy_score(y_train,pred_train),'precision_default':precision_score(y_train,pred_train,zero_division=0),'recall_default':recall_score(y_train,pred_train,zero_division=0),'f1_default':f1_score(y_train,pred_train,zero_division=0),'roc_auc':roc_auc_score(y_train,prob_train),'average_precision':average_precision_score(y_train,prob_train),'brier_score':brier_score_loss(y_train,prob_train),'confusion_matrix':confusion_matrix(y_train,pred_train).tolist()},
 'test':{'accuracy':accuracy_score(y_test,pred_test),'balanced_accuracy':balanced_accuracy_score(y_test,pred_test),'precision_default':precision_score(y_test,pred_test,zero_division=0),'recall_default':recall_score(y_test,pred_test,zero_division=0),'f1_default':f1_score(y_test,pred_test,zero_division=0),'roc_auc':roc_auc_score(y_test,prob_test),'average_precision':average_precision_score(y_test,prob_test),'brier_score':brier_score_loss(y_test,prob_test),'confusion_matrix':confusion_matrix(y_test,pred_test).tolist()},
 'cross_validation_5_fold':{k:{'mean':float(np.mean(v)),'std':float(np.std(v,ddof=1))} for k,v in cv_scores.items() if k.startswith('test_')},
 'limitations':['Historical German credit dataset, not representative of Indian applicants.','Only 11 of the source predictors are used.','Ordinal coding of categorical variables imposes ordering assumptions.','This is a reproducible prototype baseline, not a production credit model.']
}
(MODEL_DIR/'evaluation_metrics.json').write_text(json.dumps(metrics,indent=2))
# Linear SHAP on standardized model input. Each attribution maps directly to one raw feature.
X_train_scaled = pipeline.named_steps['scaler'].transform(X_train)
explainer = shap.LinearExplainer(pipeline.named_steps['clf'], X_train_scaled)
with EXPLAINER_PATH.open('wb') as f: pickle.dump({'explainer':explainer,'scaler':pipeline.named_steps['scaler'],'features':FEATURES,'labels':FEATURE_LABELS,'method':'SHAP LinearExplainer','output_scale':'log_odds'},f)
# Export the probability calculation as primitive ONNX arithmetic. This avoids
# the opaque LinearClassifier operator and lets EZKL prove the actual inference.
scaler = pipeline.named_steps['scaler']; clf = pipeline.named_steps['clf']
initializers = [
    numpy_helper.from_array(np.concatenate([scaler.mean_.astype(np.float32),np.zeros(4,dtype=np.float32)]).reshape(1,-1), name='mean'),
    numpy_helper.from_array(np.concatenate([scaler.scale_.astype(np.float32),np.ones(4,dtype=np.float32)]).reshape(1,-1), name='scale'),
    numpy_helper.from_array(np.concatenate([clf.coef_.astype(np.float32).T,np.zeros((4,1),dtype=np.float32)],axis=0), name='coef_transposed'),
    numpy_helper.from_array(clf.intercept_.astype(np.float32).reshape(1,1), name='intercept'),
    numpy_helper.from_array(np.array([1],dtype=np.int64), name='squeeze_axes'),
]
nodes = [
    helper.make_node('Sub', ['input','mean'], ['centered']),
    helper.make_node('Div', ['centered','scale'], ['scaled']),
    helper.make_node('MatMul', ['scaled','coef_transposed'], ['linear_no_bias']),
    helper.make_node('Add', ['linear_no_bias','intercept'], ['log_odds']),
    helper.make_node('Sigmoid', ['log_odds'], ['prob_default_matrix']),
    helper.make_node('Squeeze', ['prob_default_matrix','squeeze_axes'], ['prob_default']),
]
graph = helper.make_graph(nodes,'sakshi_logistic_probability',
    [helper.make_tensor_value_info('input',TensorProto.FLOAT,[1,len(FEATURES)+4])],
    [helper.make_tensor_value_info('prob_default',TensorProto.FLOAT,[1])],initializers)
onnx_model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',13)],producer_name='sakshi'); onnx_model.ir_version=10
onnx.checker.check_model(onnx_model)
onnx_path=MODEL_DIR/'sakshi_credit_v1.onnx'
onnx_path.write_bytes(onnx_model.SerializeToString())
# Guard against accidental export drift.
import onnxruntime as ort
session=ort.InferenceSession(str(onnx_path),providers=['CPUExecutionProvider'])
for sample in X_test[:20]:
    actual=float(session.run(None,{'input':np.concatenate([sample.astype(np.float32),np.zeros(4,dtype=np.float32)]).reshape(1,-1)})[0][0])
    expected=float(pipeline.predict_proba(sample.reshape(1,-1))[0,1])
    if abs(actual-expected)>2e-5: raise RuntimeError(f'ONNX probability mismatch: {actual} vs {expected}')
model_hash=hashlib.sha256(onnx_path.read_bytes()).hexdigest()
registry={'version':'2.0.0','model_name':'uci_german_credit_logistic_baseline','model_family':'sklearn_pipeline_logistic_regression','dataset':{'name':'UCI Statlog German Credit Data','source':'https://archive.ics.uci.edu/dataset/144/statloggermancreditdata','license':'CC BY 4.0','rows':1000,'target':'default=1 means UCI class 2 (bad credit risk)'},'onnx_path':'../models/sakshi_credit_v1.onnx','model_hash':model_hash,'output_contract':{'kind':'scalar_probability','output_index':0,'description':'single sigmoid probability of bad credit risk'},'zk_nonce_dimensions':4,'zk_nonce_range':[0,8191],'features':FEATURES,'feature_labels':FEATURE_LABELS,'policy':{'approve_threshold':0.5,'max_credit_amount':20000,'min_age':18},'registered_by':'lender_admin','registered_at':'2026-10-14T00:00:00Z','explanation':{'method':'SHAP LinearExplainer','output_scale':'log_odds','optional':True},'zk_proof':{'system':'EZKL Halo2','enabled':True,'input_visibility':'Hashed (Poseidon commitment with private nonce)','output_visibility':'Public','statement':'Proof binds a private feature vector commitment to the public model probability','decision_output_binding':True}}
REGISTRY_PATH.write_text(json.dumps(registry,indent=2))
print('Model:',registry['model_name'],'hash:',model_hash)
print('Train metrics:',json.dumps(metrics['train'],indent=2))
print('Test metrics:',json.dumps(metrics['test'],indent=2))
print('5-fold CV:',json.dumps(metrics['cross_validation_5_fold'],indent=2))
