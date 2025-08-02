from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class ConfigPush(BaseModel):
    config: str
    token: str = None

@app.post("/push-config")
def push_config(data: ConfigPush):
    # Here, connect to the physical Nokia device and apply config
    print("[Nokia Agent] Received config for push:")
    print(data.config)
    # Simulate device application
    # TODO: Implement SSH/NETCONF/RESTCONF logic here
    return {"status": "success", "message": "Config applied to Nokia device"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
