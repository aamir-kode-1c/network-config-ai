import os

import paramiko
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()


class ConfigPush(BaseModel):
    config: str
    token: str | None = None


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    print(f"[Agent Error] Exception: {exc}")
    return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})


@app.post("/push-config")
def push_config(data: ConfigPush):
    device_ip = os.getenv("CISCO_DEVICE_HOST", "cisco-simulator")
    username = os.getenv("CISCO_DEVICE_USERNAME", "admin")
    password = os.getenv("CISCO_DEVICE_PASSWORD", "cisco")
    port = int(os.getenv("CISCO_DEVICE_PORT", "22"))
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(device_ip, port=port, username=username, password=password, timeout=10)
        shell = ssh.invoke_shell()
        shell.settimeout(5)
        output = ""
        for line in data.config.strip().splitlines():
            shell.send(line + "\n")
            try:
                output += shell.recv(4096).decode(errors="replace")
            except TimeoutError:
                break
        shell.send("exit\n")
        try:
            output += shell.recv(4096).decode(errors="replace")
        except TimeoutError:
            pass
        ssh.close()
        return {"status": "success", "message": "Config applied via Cisco agent SSH", "output": output}
    except Exception as exc:
        print(f"[Cisco Agent] Exception: {exc}")
        return {"status": "error", "message": str(exc)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
