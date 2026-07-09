import sys

def calc():
    while True:
        try:
            line = input(">> ").strip()
            if line.lower() in ("q", "quit", "exit"):
                break
            if not line:
                continue
            result = eval(line)
            print(result)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    calc()
