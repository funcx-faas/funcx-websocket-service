# FuncX WebSocket Service

This service sends task updates to FuncX clients via WebSockets.

## How to build docker image

```
docker build -t funcx_websocket_service:develop .
```

## Deploying locally with Helm chart

Use these values:

```yaml
webService:
  host: http://localhost:5000
  globusClient: ...
  globusKey: ...
  image: funcx/web-service
  tag: main
  pullPolicy: Always
endpoint:
  enabled: false
funcx_endpoint:
  image:
    tag: exception
forwarder:
  enabled: true
  image: funcx/forwarder
  tag: main
  pullPolicy: Always
redis:
  master:
    service:
      nodePort: 30379
      type: NodePort
postgresql:
  service:
    nodePort: 30432
    type: NodePort
websocketService:
  image: funcx_websocket_service
  tag: develop
  pullPolicy: Never
```

You should deploy as usual like:

```
helm install -f deployed_values/values.yaml funcx funcx
```

Port 5000 will need to be exposed for the web service, and the WebSocket server uses port 6000:

```
export POD_NAME=$(kubectl get pods --namespace default -l "app=funcx-funcx-web-service" -o jsonpath="{.items[0].metadata.name}") && kubectl port-forward $POD_NAME 5000:5000
export POD_NAME=$(kubectl get pods --namespace default -l "app=funcx-funcx-websocket-service" -o jsonpath="{.items[0].metadata.name}") && kubectl port-forward $POD_NAME 6000:6000
```

## Run the WebSocket server as a Python script without deploying it to a pod

First, deploy the normal helm-chart `main` branch. Next, expose the web service port 5000, redis port 6379, and RabbitMQ port 5672:

```
export POD_NAME=$(kubectl get pods --namespace default -l "app=funcx-funcx-web-service" -o jsonpath="{.items[0].metadata.name}") && kubectl port-forward $POD_NAME 5000:5000
kubectl port-forward funcx-redis-master-0 6379:6379
kubectl port-forward funcx-rabbitmq-0 5672:5672
```

Clone this repository and run it with `python run.py`. The server should connect with your local web service, redis, and RabbitMQ instances by default

## Examples

Coming soon
