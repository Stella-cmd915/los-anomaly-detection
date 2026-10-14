import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "logs.db")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("DB:", DB_PATH)

    # tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [r[0] for r in cur.fetchall()]
    print("\nTables:", tables)

    # counts
    cur.execute("SELECT COUNT(*) FROM logs_raw;")
    print("\nTotal logs_raw:", cur.fetchone()[0])

    cur.execute("SELECT COUNT(*) FROM logs_parsed;")
    print("Total logs_parsed:", cur.fetchone()[0])

    # group by level
    cur.execute("SELECT level, COUNT(*) AS c FROM logs_parsed GROUP BY level ORDER BY c DESC;")
    print("\nCounts by level:")
    for level, c in cur.fetchall():
        print(level, c)

    # indexes
    cur.execute("PRAGMA index_list('logs_parsed');")
    print("\nIndexes on logs_parsed:")
    for row in cur.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    main()