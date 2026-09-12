FROM python:3.11-slim
WORKDIR /simulator
RUN pip install --no-cache-dir paramiko
COPY cisco_simulator.py .
EXPOSE 22
CMD ["python", "cisco_simulator.py"]
