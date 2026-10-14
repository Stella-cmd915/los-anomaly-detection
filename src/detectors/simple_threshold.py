from .base import Detector, DetectionResult, clamp01

class SimpleThresholdDetector(Detector):
    name = "simple_threshold"

    def __init__(self, warn_weight: float = 0.55, exception_weight: float = 0.60, len_weight: float = 0.25, len_norm: int = 160):
        self.warn_weight = warn_weight
        self.exception_weight = exception_weight
        self.len_weight = len_weight
        self.len_norm = max(1, int(len_norm))

    def predict(self, parsed_row, feature_row) -> DetectionResult:
        has_warn = int(feature_row.get("has_warn", 0))
        has_exception = int(feature_row.get("has_exception", 0))
        msg_len = int(feature_row.get("msg_len", 0))

        len_score = clamp01(msg_len / self.len_norm)

        score = 0.0
        score += self.warn_weight * has_warn
        score += self.exception_weight * has_exception
        score += self.len_weight * len_score

        score = clamp01(score)

        label = "anomaly" if score >= 0.65 else "normal"
        return DetectionResult(score=score, label=label)