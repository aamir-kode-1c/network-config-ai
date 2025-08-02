import socketserver

class OpenetPMHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b"Openet Policy Manager> ")
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            cmd = data.decode().strip()
            print(f"Received: {cmd}")
            if cmd.lower() in ["exit", "quit"]:
                self.request.sendall(b"Bye!\n")
                continue
            self.request.sendall(b"OK\nOpenet Policy Manager> ")

if __name__ == "__main__":
    HOST, PORT = "localhost", 2226
    with socketserver.TCPServer((HOST, PORT), OpenetPMHandler) as server:
        print(f"Openet Policy Manager Simulator running on {HOST}:{PORT}")
        server.serve_forever()
