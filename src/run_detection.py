import os
import time
import json
import sqlite3
from collections import Counter

from detectors.simple_threshold import SimpleThresholdDetector
from detectors.rare_component import RareComponentDetector

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "logs.db")

def ensure_predictions(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parsed_id INTEGER NOT NULL,
        model_name TEXT NOT NULL,
        score REAL NOT NULL,
        label TEXT NOT NULL,
        infer_ms REAL NOT NULL,
        created_ts TEXT NOT NULL,
        FOREIGN KEY(parsed_id) REFERENCES logs_parsed(id)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_label ON predictions(label);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_model ON predictions(model_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_score ON predictions(score);")
    conn.commit()

def load_parsed_and_features(conn: sqlite3.Connection, limit: int = 400):
    cur = conn.cursor()
    cur.execute("""
    SELECT p.id, p.level, p.component, p.content, f.feature_json
    FROM logs_parsed p
    JOIN features f ON f.parsed_id = p.id
    ORDER BY p.id ASC
    LIMIT ?
    """, (limit,))
    rows = []
    for pid, level, component, content, feat_json in cur.fetchall():
        parsed = {"id": pid, "level": level, "component": component, "content": content}
        feats = json.loads(feat_json)
        rows.append((parsed, feats))
    return rows

def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_predictions(conn)

    data = load_parsed_and_features(conn, limit=400)
    if not data:
        print("Δεν βρέθηκαν εγγραφές για ανίχνευση.")
        return

    component_counts = Counter([p["component"] for (p, _) in data])

    detectors = [
        SimpleThresholdDetector(),
        RareComponentDetector(component_counts=component_counts, min_count=10),
    ]

    cur = conn.cursor()

    inserted = 0
    for det in detectors:
        cur.execute("DELETE FROM predictions WHERE model_name = ?", (det.name,))
        conn.commit()

        start = time.perf_counter()
        for (parsed, feats) in data:
            t0 = time.perf_counter()
            res = det.predict(parsed, feats)
            t1 = time.perf_counter()

            infer_ms = (t1 - t0) * 1000.0
            created_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            cur.execute(
                "INSERT INTO predictions(parsed_id, model_name, score, label, infer_ms, created_ts) VALUES (?,?,?,?,?,?)",
                (parsed["id"], det.name, float(res.score), res.label, float(infer_ms), created_ts)
            )
            inserted += 1

        conn.commit()
        total_ms = (time.perf_counter() - start) * 1000.0

        cur.execute("SELECT COUNT(*) FROM predictions WHERE model_name=? AND label='anomaly'", (det.name,))
        anom = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM predictions WHERE model_name=?", (det.name,))
        total = cur.fetchone()[0]
        print(f"Detector {det.name} ολοκληρώθηκε, εγγραφές {total}, anomalies {anom}, συνολικός χρόνος {total_ms:.2f}ms")

    conn.close()
    print("Ολοκληρώθηκε, τα αποτελέσματα γράφτηκαν στον πίνακα predictions.")

if __name__ == "__main__":
    main()