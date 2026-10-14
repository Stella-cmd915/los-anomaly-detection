import re
import time
import json
from datetime import datetime

LOG_PATTERNS = [
    (re.compile(r"Failed password for (?P<user>\w+) from (?P<ip>[\d\.]+) port (?P<port>\d+)"),
     "FAILED_LOGIN"),
    (re.compile(r"Accepted password for (?P<user>\w+) from (?P<ip>[\d\.]+) port (?P<port>\d+)"),
     "OK_LOGIN"),
    (re.compile(r"Connection closed by (?P<ip>[\d\.]+) port (?P<port>\d+)"),
     "CONN_CLOSED"),
]

def parse_log(line: str):
    line = line.strip()
    for rx, event in LOG_PATTERNS:
        m = rx.search(line)
        if m:
            data = m.groupdict()
            return {
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "raw": line,
                "event": event,
                "fields": data
            }
    return {
        "ts": datetime.utcnow().isoformat() + "Z",
        "raw": line,
        "event": "UNKNOWN",
        "fields": {}
    }

def anomaly_score(parsed):
    event = parsed["event"]
    score = 0.0

    # ενδεικτική λογική scoring (όχι ML): αποτυπώνει “ύποπτα” patterns
    if event == "FAILED_LOGIN":
        score += 0.7
    if event == "UNKNOWN":
        score += 0.4

    # πιο “σπάνια” ports μπορεί να πάρουν λίγο παραπάνω βάρος
    port = parsed["fields"].get("port")
    if port and int(port) > 50000:
        score += 0.2

    return min(score, 1.0)

def stream_logs(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            yield line
            time.sleep(0.05)  # προσομοίωση real-time ροής

def main():
    input_file = "sample_logs.txt"
    output_file = "labeled_logs.jsonl"

    with open(output_file, "w", encoding="utf-8") as out:
        for line in stream_logs(input_file):
            parsed = parse_log(line)
            score = anomaly_score(parsed)
            label = "anomaly" if score >= 0.7 else "normal"

            record = {
                **parsed,
                "score": score,
                "label": label
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(record["event"], record["label"], record["score"])

if __name__ == "__main__":
    main()
