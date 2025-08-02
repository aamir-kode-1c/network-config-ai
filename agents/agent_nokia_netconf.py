from fastapi import FastAPI
from pydantic import BaseModel
from ncclient import manager

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
    port = 830
    try:
        with manager.connect(host=device_ip, port=port, username=username, password=password, hostkey_verify=False, timeout=10) as m:
            # This assumes 'data.config' is valid XML or a NETCONF snippet
            response = m.edit_config(target='running', config=data.config)
            return {"status": "success", "message": "Config applied via NETCONF", "output": str(response)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5002)
