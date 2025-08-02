import socketserver

class Nokia7750SRHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b"Nokia 7750 SR> ")
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            cmd = data.decode().strip()
            print(f"Received: {cmd}")
            if cmd.lower() in ["exit", "quit"]:
                self.request.sendall(b"Bye!\n")
                # Don't break here; let client close connection
                continue
            self.request.sendall(b"OK\nNokia 7750 SR> ")

if __name__ == "__main__":
    HOST, PORT = "localhost", 2223
    with socketserver.TCPServer((HOST, PORT), Nokia7750SRHandler) as server:
        print(f"Nokia 7750 SR Simulator running on {HOST}:{PORT}")
        server.serve_forever()
