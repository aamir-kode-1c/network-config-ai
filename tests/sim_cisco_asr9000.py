import socketserver

class CiscoASR9000Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b"ASR9000> ")
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            cmd = data.decode().strip()
            print(f"Received: {cmd}")
            if cmd.lower() in ["exit", "quit"]:
                self.request.sendall(b"Bye!\n")
                break
            self.request.sendall(b"OK\nASR9000> ")

if __name__ == "__main__":
    HOST, PORT = "localhost", 2222
    with socketserver.TCPServer((HOST, PORT), CiscoASR9000Handler) as server:
        print(f"Cisco ASR 9000 Simulator running on {HOST}:{PORT}")
        server.serve_forever()
