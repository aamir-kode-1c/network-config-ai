from fastapi import FastAPI
from pydantic import BaseModel
import paramiko

app = FastAPI()

class ConfigPush(BaseModel):
    config: str
    token: str = None

@app.post("/push-config")
def push_config(data: ConfigPush):
    # Replace with your device's real IP, username, and password
    device_ip = "192.168.1.100"  # TODO: Set your real Nokia device IP
    username = "admin"           # TODO: Set your username
    password = "your_password"   # TODO: Set your password
    port = 22
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
        shell = ssh.invoke_shell()
        output = ""
        for line in data.config.strip().splitlines():
            shell.send(line + "\n")
            output += shell.recv(1024).decode()
        shell.send("exit\n")
        output += shell.recv(1024).decode()
        ssh.close()
        return {"status": "success", "message": "Config applied via SSH", "output": output}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
