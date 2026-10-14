import os
import csv
import sqlite3
import math
from statistics import mean
import matplotlib.pyplot as plt

HOME = os.path.expanduser("~")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "logs.db")
GT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "ground_truth.csv")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "evaluation")
os.makedirs(OUT_DIR, exist_ok=True)

def load_ground_truth(gt_path):
    gt = {}
    gt_type = {}
    with open(gt_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            line_id = int(row["line_id"])
            gt[line_id] = row["label"].strip()
            gt_type[line_id] = row["anomaly_type"].strip()
    return gt, gt_type

def percentile(xs, p):
    if not xs:
        return 0.0
    xs = sorted(xs)
    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(xs[int(k)])
    return float(xs[f] * (c - k) + xs[c] * (k - f))

def metrics(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1

def main():
    gt, gt_type = load_ground_truth(GT_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Χαρτογράφηση σειράς σε line_id (1..N) πάνω στο logs_parsed id
    cur.execute("SELECT id FROM logs_parsed ORDER BY id ASC")
    parsed_ids = [r[0] for r in cur.fetchall()]
    line_of_parsed = {pid: i+1 for i, pid in enumerate(parsed_ids)}  # line_id -> 1-based

    # Models
    cur.execute("SELECT DISTINCT model_name FROM predictions ORDER BY model_name")
    models = [r[0] for r in cur.fetchall()]
    if not models:
        print("Δεν βρέθηκαν predictions. Τρέξε πρώτα run_detection.py")
        return

    results_rows = []
    latency_rows = []

    # Για σφάλματα
    fp_examples = {}
    fn_examples = {}

    for model in models:
        cur.execute("""
        SELECT pr.parsed_id, pr.label, pr.score, pr.infer_ms, r.raw
        FROM predictions pr
        JOIN logs_parsed p ON p.id = pr.parsed_id
        JOIN logs_raw r ON r.id = p.raw_id
        WHERE pr.model_name = ?
        """, (model,))
        rows = cur.fetchall()

        tp = fp = fn = tn = 0
        infer_ms_list = []

        fp_examples[model] = []
        fn_examples[model] = []

        for parsed_id, pred_label, score, infer_ms, raw in rows:
            line_id = line_of_parsed.get(parsed_id)
            if line_id is None:
                continue
            true_label = gt.get(line_id, "normal")

            infer_ms_list.append(float(infer_ms))

            pred_is_anom = (pred_label == "anomaly")
            true_is_anom = (true_label == "anomaly")

            if pred_is_anom and true_is_anom:
                tp += 1
            elif pred_is_anom and (not true_is_anom):
                fp += 1
                if len(fp_examples[model]) < 5:
                    fp_examples[model].append((line_id, score, raw[:140]))
            elif (not pred_is_anom) and true_is_anom:
                fn += 1
                if len(fn_examples[model]) < 5:
                    fn_examples[model].append((line_id, score, raw[:140]))
            else:
                tn += 1

        precision, recall, f1 = metrics(tp, fp, fn)

        results_rows.append([model, tp, fp, fn, tn, round(precision, 4), round(recall, 4), round(f1, 4)])

        if infer_ms_list:
            latency_rows.append([
                model,
                len(infer_ms_list),
                round(mean(infer_ms_list), 4),
                round(percentile(infer_ms_list, 0.95), 4),
                round(max(infer_ms_list), 4),
                round(1000.0 / mean(infer_ms_list), 2)  # approx inferences/sec
            ])

    # Save metrics table
    metrics_csv = os.path.join(OUT_DIR, "metrics_by_model.csv")
    with open(metrics_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "TP", "FP", "FN", "TN", "precision", "recall", "f1"])
        w.writerows(results_rows)

    # Save latency table
    latency_csv = os.path.join(OUT_DIR, "latency_by_model.csv")
    with open(latency_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "N", "mean_infer_ms", "p95_infer_ms", "max_infer_ms", "approx_throughput_infer_per_sec"])
        w.writerows(latency_rows)

    # Plot F1 comparison
    models_plot = [r[0] for r in results_rows]
    f1s = [r[7] for r in results_rows]
    plt.figure(figsize=(7,4.2))
    plt.bar(models_plot, f1s)
    plt.ylabel("F1")
    plt.xlabel("Αλγόριθμος")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "f1_by_model.png"), dpi=220, bbox_inches="tight")
    plt.close()

    # Plot mean infer time
    if latency_rows:
        models_lat = [r[0] for r in latency_rows]
        mean_ms = [r[2] for r in latency_rows]
        plt.figure(figsize=(7,4.2))
        plt.bar(models_lat, mean_ms)
        plt.ylabel("Mean inference time (ms)")
        plt.xlabel("Αλγόριθμος")
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, "mean_infer_ms_by_model.png"), dpi=220, bbox_inches="tight")
        plt.close()

    # Print summary to terminal
    print("Αποτελέσματα (Precision/Recall/F1) ανά αλγόριθμο")
    for r in results_rows:
        print(f"{r[0]} | TP {r[1]} FP {r[2]} FN {r[3]} TN {r[4]} | P {r[5]} R {r[6]} F1 {r[7]}")

    print("\nΧρόνοι inference και throughput")
    for r in latency_rows:
        print(f"{r[0]} | N {r[1]} | mean {r[2]}ms | p95 {r[3]}ms | max {r[4]}ms | ~{r[5]} inf/s")

    # Save error examples
    err_txt = os.path.join(OUT_DIR, "error_examples.txt")
    with open(err_txt, "w", encoding="utf-8") as f:
        for model in models:
            f.write(f"MODEL: {model}\n")
            f.write("False Positives (line_id, score, raw_snippet)\n")
            for ex in fp_examples[model]:
                f.write(f"{ex[0]} | {ex[1]} | {ex[2]}\n")
            f.write("\nFalse Negatives (line_id, score, raw_snippet)\n")
            for ex in fn_examples[model]:
                f.write(f"{ex[0]} | {ex[1]} | {ex[2]}\n")
            f.write("\n" + "-"*60 + "\n\n")

    print("\nΑρχεία που δημιουργήθηκαν στον φάκελο results\\evaluation")
    print(metrics_csv)
    print(latency_csv)
    print(os.path.join(OUT_DIR, "f1_by_model.png"))
    print(os.path.join(OUT_DIR, "mean_infer_ms_by_model.png"))
    print(err_txt)

    conn.close()

if __name__ == "__main__":
    main()