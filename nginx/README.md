# Domain
put into user.json
更換平台，記得改IP
Grafana 不吃 env 變數，只好把設定放到 nginx 底下

# Docker Buildx
docker login
docker buildx create --name mybuilder --use 
docker buildx build --push --platform linux/arm64/v8,linux/amd64 -t roberthu1006/savills-nginx:1.0.3 .