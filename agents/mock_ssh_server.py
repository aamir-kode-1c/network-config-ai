import socketserver

class MockSSHHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print(f"[MockSSH] Connection from {self.client_address}")
        self.request.sendall(b"Mock SSH Server Ready\n")
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            cmd = data.decode().strip()
            print(f"[MockSSH] Received: {cmd}")
            if cmd.lower() == "exit":
                self.request.sendall(b"Bye!\n")
                break
            self.request.sendall(b"OK\n")

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 22
    with socketserver.TCPServer((HOST, PORT), MockSSHHandler) as server:
        print(f"Mock SSH server running on {HOST}:{PORT}")
        server.serve_forever()
