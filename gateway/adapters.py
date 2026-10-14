"""Model adapter boundary: evidence code consumes a probability, not a model family."""
from pathlib import Path
import hashlib
import onnxruntime as rt
import numpy as np

class OnnxProbabilityAdapter:
    def __init__(self, registry: dict, project_root: Path):
        model_path = Path(registry.get('onnx_path', ''))
        if not model_path.is_absolute(): model_path = (project_root / 'gateway' / model_path).resolve()
        if not model_path.is_file(): model_path = project_root / 'models' / 'sakshi_credit_v1.onnx'
        actual = hashlib.sha256(model_path.read_bytes()).hexdigest()
        if actual != registry['model_hash']:
            raise RuntimeError('MODEL HASH MISMATCH — refusing inference')
        self.path = model_path
        self.session = rt.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
        self.input_name = self.session.get_inputs()[0].name
        self.output_contract = registry.get('output_contract', {'kind':'scalar_probability','output_index':0})

    def predict_default_probability(self, X: np.ndarray) -> float:
        outputs = self.session.run(None, {self.input_name: np.asarray(X, dtype=np.float32)})
        kind = self.output_contract.get('kind', 'scalar_probability')
        index = int(self.output_contract.get('output_index', 0))
        out = np.asarray(outputs[index])
        if kind == 'scalar_probability': value = float(out.reshape(-1)[0])
        elif kind == 'binary_probability_matrix': value = float(out.reshape(out.shape[0], -1)[0, int(self.output_contract.get('class_index',1))])
        else: raise ValueError(f'Unsupported model output contract: {kind}')
        if not 0.0 <= value <= 1.0: raise ValueError(f'Model output is not a probability: {value}')
        return value
