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

## Testing

First install test requirements:

```
python -m pip install -r test-requirements.txt
```

Then run tests with pytest:

```
pytest funcx_websocket_service/tests
```

## CLI

When this repository is installed as a package, it is run as follows (Running this outside of a Helm chart deployment is not recommended):

```
websocket-service [--debug]
```

### CLI Arguments

`--debug` - If this flag is present or the `FUNCX_WEBSOCKET_SERVICE_DEBUG` environment variable is set, the debug log level is shown

## Environment Variables

`FUNCX_WEBSOCKET_SERVICE_DEBUG` - If this is set to anything or the debug CLI argument above is set, the debug log level is shown

`REDIS_HOST` - redis host (defaults to `127.0.0.1`)

`FUNCX_REDIS_MASTER_SERVICE_HOST` - redis host set by Helm deployment (`REDIS_HOST` overrides this if set)

`REDIS_PORT` - redis port (defaults to `6379`)

`RABBITMQ_HOST` - RabbitMQ host (defaults to `127.0.0.1`)

`FUNCX_RABBITMQ_SERVICE_HOST` - RabbitMQ host set by Helm deployment (`RABBITMQ_HOST` overrides this if set)

`WEB_SERVICE_URI` - funcX web service URI (defaults to `http://127.0.0.1:5000`)

## Example

Run an endpoint with `funcx_service_address='https://api.dev.funcx.org/v2'`, then set your `endpoint_id` in the script below. This example uses a `FuncXExecutor` to double 10 random numbers, then prints the results when they arrive back from the WebSocket service.

```python
import random
from funcx import FuncXClient
from funcx.sdk.executor import FuncXExecutor

def double(x):
    return x * 2

service_url = 'https://api.dev.funcx.org/v2'
# Set your endpoint_id here
endpoint_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
fx = FuncXExecutor(FuncXClient(funcx_service_address=service_url,
                               results_ws_uri='wss://api.dev.funcx.org/ws/v2/'))

futures = []
for i in range(10):
    x = random.randint(0, 100)
    future = fx.submit(double, x, endpoint_id=endpoint_id)
    futures.append(future)

for future in futures:
    print(future.result())
```
