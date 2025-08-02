import os
import socket
import sys

def push_config_to_asr9000(config, host="localhost", port=2222):
    try:
        with socket.create_connection((host, port), timeout=5) as s:
            s.recv(1024)  # Read initial prompt
            for line in config.splitlines():
                s.sendall(line.encode() + b"\n")
                resp = s.recv(1024)
                print(resp.decode())
            s.sendall(b"exit\n")
            resp = s.recv(1024)
            print(resp.decode())
    except Exception as e:
        print(f"Socket error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/cisco_asr_9000_config_latest.txt"
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        config = f.read()
    push_config_to_asr9000(config)
