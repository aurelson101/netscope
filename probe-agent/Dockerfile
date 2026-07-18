FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends nmap arp-scan iputils-ping && rm -rf /var/lib/apt/lists/* && groupadd -r netscope && useradd -r -g netscope netscope
WORKDIR /app
RUN pip install --no-cache-dir httpx==0.28.1 dnspython==2.7.0
COPY backend/app app
COPY probe-agent/agent.py agent.py
# arp-scan et l'empreinte OS Nmap nécessitent l'eUID root pour ouvrir la capture.
# Le conteneur reste isolé (réseau hôte uniquement, capacités réseau limitées,
# no-new-privileges dans le compose).
CMD ["python","agent.py"]
