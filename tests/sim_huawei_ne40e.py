import socketserver

class HuaweiNE40EHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.sendall(b"Huawei NE40E> ")
        while True:
            data = self.request.recv(1024)
            if not data:
                break
            cmd = data.decode().strip()
            print(f"Received: {cmd}")
            if cmd.lower() in ["exit", "quit"]:
                self.request.sendall(b"Bye!\n")
                break
            self.request.sendall(b"OK\nHuawei NE40E> ")

if __name__ == "__main__":
    HOST, PORT = "localhost", 2225
    with socketserver.TCPServer((HOST, PORT), HuaweiNE40EHandler) as server:
        print(f"Huawei NE40E Simulator running on {HOST}:{PORT}")
        server.serve_forever()
