from collections import Counter
from .base import Detector, DetectionResult, clamp01

class RareComponentDetector(Detector):
    name = "rare_component"

    def __init__(self, component_counts: Counter, min_count: int = 8):
        self.component_counts = component_counts
        self.min_count = int(min_count)

    def predict(self, parsed_row, feature_row) -> DetectionResult:
        comp = parsed_row.get("component") or feature_row.get("component") or ""
        c = int(self.component_counts.get(comp, 0))

        rare_score = 1.0 if c < self.min_count else 0.0
        exception_score = 1.0 if int(feature_row.get("has_exception", 0)) == 1 else 0.0

        score = clamp01(0.75 * rare_score + 0.35 * exception_score)
        label = "anomaly" if score >= 0.70 else "normal"
        return DetectionResult(score=score, label=label)