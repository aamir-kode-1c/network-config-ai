import socketserver

class EricssonRouter6000Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b"Ericsson Router 6000> ")
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            cmd = data.decode().strip()
            print(f"Received: {cmd}")
            if cmd.lower() in ["exit", "quit"]:
                self.request.sendall(b"Bye!\n")
                break
            self.request.sendall(b"OK\nEricsson Router 6000> ")

if __name__ == "__main__":
    HOST, PORT = "localhost", 2224
    with socketserver.TCPServer((HOST, PORT), EricssonRouter6000Handler) as server:
        print(f"Ericsson Router 6000 Simulator running on {HOST}:{PORT}")
        server.serve_forever()
