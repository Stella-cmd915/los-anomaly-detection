import argparse
import os
import re
import json
import time
import sqlite3
from datetime import datetime, timezone

HDFS_RX = re.compile(
    r'^(?P<date>\d+)\s+(?P<time>\d+)\s+(?P<pid>\d+)\s+(?P<level>[A-Z]+)\s+(?P<component>[^:]+):\s+(?P<content>.*)$'
)

def utc_ts():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def ensure_schema(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs_raw (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        raw TEXT NOT NULL,
        source TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs_parsed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        raw_id INTEGER NOT NULL,
        date TEXT,
        time TEXT,
        pid INTEGER,
        level TEXT,
        component TEXT,
        content TEXT,
        FOREIGN KEY(raw_id) REFERENCES logs_raw(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parsed_id INTEGER NOT NULL,
        feature_json TEXT NOT NULL,
        FOREIGN KEY(parsed_id) REFERENCES logs_parsed(id)
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_parsed_level ON logs_parsed(level);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_parsed_component ON logs_parsed(component);")
    conn.commit()

def parse_line(raw_line):
    m = HDFS_RX.match(raw_line)
    if not m:
        return None
    d = m.groupdict()
    d["pid"] = int(d["pid"])
    return d

def make_features(parsed):
    content = parsed["content"]
    feats = {
        "msg_len": len(content),
        "has_exception": 1 if "exception" in content.lower() else 0,
        "has_warn": 1 if parsed["level"] == "WARN" else 0,
        "component": parsed["component"],
    }
    return feats

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "stream_input.log"))
    ap.add_argument("--db", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "logs.db"))
    ap.add_argument("--source", default="HDFS_stream_input")
    ap.add_argument("--max_lines", type=int, default=600)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.db), exist_ok=True)

    conn = sqlite3.connect(args.db)
    ensure_schema(conn)
    cur = conn.cursor()

    inserted_raw = 0
    inserted_parsed = 0
    inserted_feat = 0

    start = time.time()
    with open(args.input, "r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, start=1):
            if i > args.max_lines:
                break
            raw_line = line.rstrip("\n")
            ts = utc_ts()

            cur.execute("INSERT INTO logs_raw(ts, raw, source) VALUES (?,?,?)", (ts, raw_line, args.source))
            raw_id = cur.lastrowid
            inserted_raw += 1

            parsed = parse_line(raw_line)
            if parsed:
                cur.execute(
                    """INSERT INTO logs_parsed(raw_id, date, time, pid, level, component, content)
                       VALUES (?,?,?,?,?,?,?)""",
                    (raw_id, parsed["date"], parsed["time"], parsed["pid"], parsed["level"], parsed["component"], parsed["content"])
                )
                parsed_id = cur.lastrowid
                inserted_parsed += 1

                feats = make_features(parsed)
                cur.execute("INSERT INTO features(parsed_id, feature_json) VALUES (?,?)", (parsed_id, json.dumps(feats, ensure_ascii=False)))
                inserted_feat += 1

    conn.commit()
    elapsed = time.time() - start

    print("Ολοκληρώθηκε preprocessing -> SQLite")
    print(f"DB: {args.db}")
    print(f"Raw inserted: {inserted_raw}")
    print(f"Parsed inserted: {inserted_parsed}")
    print(f"Features inserted: {inserted_feat}")
    print(f"Time: {elapsed:.2f}s")

    conn.close()

if __name__ == "__main__":
    main()