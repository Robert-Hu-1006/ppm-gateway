# ppm-gateway

VS Code : virtualenv
Cmd + Shift + P : Python create terminal
pip install virtualenv
virtualenv .venv

# Docker Buildx
docker login
docker buildx create --name builder-x --use 
docker buildx build --push --platform linux/arm64/v8,linux/amd64 -t roberthu1006/savills-webhook:1.0.3 .


# 開機自動執行
sudo nano /etc/systemd/system/gateway_docker.service

[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WrokingDirectory=/home/robert/Code
ExecStart=/usr/bin/docker-compose -f /home/robert/Code/ppm-gateway/production.yml  up -d
ExecStop=/usr/bin/docker-compose -f /home/robert/Code/ppm-gateway/production.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target

sudo systemctl enable savills_docker.service
sudo systemctl start savills_docker.service