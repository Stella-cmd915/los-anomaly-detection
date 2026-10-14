import argparse
import os
import time

def follow(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        f.seek(0, os.SEEK_SET)
        for line in f:
            yield line.rstrip("\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "stream_input.log"))
    ap.add_argument("--sleep_ms", type=int, default=30)
    ap.add_argument("--max_lines", type=int, default=120)
    args = ap.parse_args()

    count = 0
    start = time.time()

    for line in follow(args.input):
        count += 1
        print(f"{count:06d} | {line[:120]}")
        time.sleep(args.sleep_ms / 1000.0)
        if count >= args.max_lines:
            break

    elapsed = time.time() - start
    eps = count / elapsed if elapsed > 0 else 0
    print(f"\nIngestion ολοκληρώθηκε, γραμμές {count}, χρόνος {elapsed:.2f}s, ρυθμός {eps:.1f} γραμμές ανά δευτερόλεπτο")

if __name__ == "__main__":
    main()