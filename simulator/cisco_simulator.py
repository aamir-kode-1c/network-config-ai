"""Small Cisco IOS-like SSH target for local end-to-end testing."""

import os
import socket
import threading

import paramiko


CONFIG_LOCK = threading.Lock()
RUNNING_CONFIG: list[str] = []


class Server(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()

    def check_auth_password(self, username, password):
        expected_user = os.getenv("CISCO_SIMULATOR_USERNAME", "admin")
        expected_password = os.getenv("CISCO_SIMULATOR_PASSWORD", "cisco")
        return paramiko.AUTH_SUCCESSFUL if username == expected_user and password == expected_password else paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, *args):
        return True


def handle_client(client):
    host_key = paramiko.RSAKey.generate(2048)
    transport = paramiko.Transport(client)
    transport.add_server_key(host_key)
    server = Server()
    transport.start_server(server=server)
    channel = transport.accept(10)
    if channel is None:
        transport.close()
        return
    server.event.wait(5)
    channel.send("Cisco IOS Simulator\\r\\nRouter# ")
    while True:
        data = channel.recv(4096)
        if not data:
            break
        for command in data.decode(errors="replace").replace("\r", "").split("\n"):
            command = command.strip()
            if not command:
                continue
            if command.lower() in {"exit", "logout", "quit"}:
                channel.send("Connection closed.\\r\\n")
                channel.close()
                transport.close()
                return
            if command.lower() in {"show running-config", "show run"}:
                with CONFIG_LOCK:
                    current_config = list(RUNNING_CONFIG)
                channel.send("\r\n".join(current_config) + ("\r\n" if current_config else ""))
                channel.send("Router# ")
                continue
            with CONFIG_LOCK:
                if command not in RUNNING_CONFIG:
                    RUNNING_CONFIG.append(command)
            channel.send(f"{command}\\r\\n")
            channel.send("Router# ")
    transport.close()


def main():
    host = os.getenv("CISCO_SIMULATOR_HOST", "0.0.0.0")
    port = int(os.getenv("CISCO_SIMULATOR_PORT", "22"))
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(20)
    print(f"Cisco simulator listening on {host}:{port}", flush=True)
    while True:
        client, _ = listener.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
