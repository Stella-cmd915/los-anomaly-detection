import argparse
import os
import random
import time
from datetime import datetime, timezone

def utc_ts():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def read_lines(path, max_lines=None):
    lines = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            lines.append(line.rstrip("\n"))
            if max_lines is not None and i + 1 >= max_lines:
                break
    return lines

def inject_spike(lines, spike_size=40):
    if not lines:
        return []
    base = random.choice(lines)
    return [base for _ in range(spike_size)]

def inject_rare_events(count=10):
    rare = []
    for _ in range(count):
        ip = f"{random.randint(10,250)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        user = random.choice(["admin", "root", "test", "guest", "unknown"])
        port = random.randint(50000, 65000)
        rare.append(f"{utc_ts()} RARE_EVENT suspicious login user={user} ip={ip} port={port}")
    return rare

def inject_sequence_anomaly():
    seq = [
        f"{utc_ts()} SEQ step=finish status=ok",
        f"{utc_ts()} SEQ step=start status=ok",
        f"{utc_ts()} SEQ step=validate status=ok",
    ]
    return seq

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    ap.add_argument("--hdfs_file", default="HDFS_2k.log")
    ap.add_argument("--out_log", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "stream_input.log"))
    ap.add_argument("--out_gt", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "ground_truth.csv"))
    ap.add_argument("--max_base_lines", type=int, default=600)
    ap.add_argument("--sleep_ms", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    hdfs_path = os.path.join(args.data_dir, args.hdfs_file)
    if not os.path.exists(hdfs_path):
        raise FileNotFoundError(f"Δεν βρέθηκε το αρχείο: {hdfs_path}")

    base_lines = read_lines(hdfs_path, max_lines=args.max_base_lines)

    # κατασκευή stream με injected anomalies
    stream = []
    gt_rows = []

    def add_line(line, label, anomaly_type):
        stream.append(line)
        gt_rows.append((len(stream), label, anomaly_type))

    # normal section
    for line in base_lines[:300]:
        add_line(line, "normal", "none")

    # spike anomaly section
    for line in inject_spike(base_lines[300:450], spike_size=50):
        add_line(line, "anomaly", "spike")

    # more normal
    for line in base_lines[450:520]:
        add_line(line, "normal", "none")

    # rare events
    for line in inject_rare_events(count=12):
        add_line(line, "anomaly", "rare")

    # sequence anomaly (out-of-order)
    for line in inject_sequence_anomaly():
        add_line(line, "anomaly", "sequence")

    # tail normal
    for line in base_lines[520:]:
        add_line(line, "normal", "none")

    os.makedirs(os.path.dirname(args.out_log), exist_ok=True)

    # γράφει ground truth
    with open(args.out_gt, "w", encoding="utf-8") as gt:
        gt.write("line_id,label,anomaly_type\n")
        for (line_id, label, atype) in gt_rows:
            gt.write(f"{line_id},{label},{atype}\n")

    # γράφει stream log “σαν real time” με pacing
    with open(args.out_log, "w", encoding="utf-8") as out:
        for i, line in enumerate(stream, start=1):
            out.write(line + "\n")
            if i <= 15:
                # μικρό preview στην οθόνη για να ξέρεις ότι δουλεύει
                print(f"{i:04d} {gt_rows[i-1][1]} {gt_rows[i-1][2]} | {line[:90]}")
            time.sleep(args.sleep_ms / 1000.0)

    print("\nΟλοκληρώθηκε.")
    print(f"Stream log: {args.out_log}")
    print(f"Ground truth: {args.out_gt}")

if __name__ == "__main__":
    main()