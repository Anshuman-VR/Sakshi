"""Optional explanation adapter. Decision evidence does not require SHAP."""
from pathlib import Path
import pickle
import numpy as np

class ShapLinearAdapter:
    def __init__(self, explainer_path: Path):
        self.data = None
        if explainer_path.is_file():
            try:
                import shap
                self.data = pickle.loads(explainer_path.read_bytes())
                self.data['shap_lib'] = shap
            except Exception:
                self.data = None

    def explain(self, X: np.ndarray, features: dict, feature_names: list[str], labels: dict) -> list[dict]:
        if not self.data: return []
        try:
            X_scaled = self.data['scaler'].transform(X)
            sv = self.data['explainer'].shap_values(X_scaled)
            vals = np.asarray(sv[0] if isinstance(sv, list) else sv).reshape(-1)
            result=[]
            for i, name in enumerate(feature_names):
                if i >= len(vals): break
                result.append({'feature':name,'label':labels.get(name,name),
                    'value':round(float(features.get(name,0)),2),'shap':round(float(vals[i]),4),
                    'impact':'positive' if vals[i] <= 0 else 'negative','output_scale':'log_odds'})
            return sorted(result,key=lambda item:abs(item['shap']),reverse=True)
        except Exception:
            return []
