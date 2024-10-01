# Docker Buildx

docker login
docker buildx create --name mybuilder --use 
docker buildx build --no-cache --push --platform linux/arm64/v8,linux/amd64 -t roberthu1006/savills-grafana:1.0.3 .
#docker buildx build --push --platform linux/arm64/v8,linux/amd64 -t roberthu1006/savills-grafana:1.0.3 .