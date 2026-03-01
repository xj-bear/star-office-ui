import subprocess
import json
import time
import sys

def test_logs():
    print("Testing openclaw logs output...")
    try:
        # Get last 10 lines to see format
        res = subprocess.run(["openclaw", "logs", "--plain", "--limit", "10"], capture_output=True, text=True)
        print("--- RAW OUTPUT START ---")
        print(res.stdout)
        print("--- RAW OUTPUT END ---")
        
        lines = res.stdout.splitlines()
        for i, line in enumerate(lines):
            print(f"\nProcessing line {i}: {line[:100]}...")
            if not line.strip(): continue
            
            # Try plain text check
            check_str = line.lower()
            print(f"  Plain check: {check_str}")
            
            # Try JSON check
            try:
                if line.strip().startswith('{'):
                    data = json.loads(line)
                    check_str = (str(data.get("0", "")) + " " + str(data.get("1", ""))).lower()
                    print(f"  JSON detected! Checked content: {check_str}")
                else:
                    print("  Not a JSON line (no starting {)")
            except Exception as e:
                print(f"  JSON parse failed: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_logs()
