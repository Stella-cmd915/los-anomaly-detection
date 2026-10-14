from dataclasses import dataclass
from typing import Dict, Any, Tuple

@dataclass
class DetectionResult:
    score: float
    label: str

class Detector:
    name: str = "base"

    def predict(self, parsed_row: Dict[str, Any], feature_row: Dict[str, Any]) -> DetectionResult:
        raise NotImplementedError("Implement in subclasses")

def clamp01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x