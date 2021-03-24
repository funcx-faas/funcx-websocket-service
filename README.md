### FuncX SDK and test script

You will need to use the `ws_async_interface` branch of the SDK (https://github.com/funcx-faas/funcX/tree/ws_async_interface)

Here is the test script, which should just log 'Hello World!':

```python
from funcx.sdk.client import FuncXClient
fxc = FuncXClient(funcx_service_address='http://localhost:5000/api/v1', asynchronous=True)

def hello_world():
    return "Hello World!"

async def task():
    endpoint = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
    func_uuid = fxc.register_function(hello_world, endpoint)
    res = fxc.run(endpoint_id=endpoint, function_id=func_uuid)
    print(await res)

fxc.loop.run_until_complete(task())
```

### How to set up and run the WebSocket server with Helm chart:

First, check out and use the `funcx_ws_draft` branch of the helm-chart repo (https://github.com/funcx-faas/helm-chart/tree/funcx_ws_draft)

This branch adds a `ws` deployment with a configuration that pulls from a Docker Hub image I created:

```yaml
ws:
  image: loonride/funcx_ws
  tag: latest
  pullPolicy: Always
```

You should also use the latest dev versions of funcx-web-service and funcx-forwarder. You should deploy as usual like:

```
helm install -f deployed_values/values.yaml funcx funcx
```

Port 5000 will need to be exposed for the web service, and the WebSocket server uses port 6000. I expose these like this:

```
export POD_NAME=$(kubectl get pods --namespace default -l "app=funcx-funcx-web-service" -o jsonpath="{.items[0].metadata.name}") && kubectl port-forward $POD_NAME 5000:5000
export POD_NAME=$(kubectl get pods --namespace default -l "app=funcx-funcx-ws" -o jsonpath="{.items[0].metadata.name}") && kubectl port-forward $POD_NAME 6000:6000
```

Now, deploy an endpoint, replace the endpoint UUID you received or chose with the one in the test script above, and run the test script.

### How to set up and run the WebSocket server as a Python script without deploying it to a pod:

First, deploy the normal helm-chart `main` branch with the latest dev versions of everything. Next, expose the web service port 5000 and redis port 6379:

```
export POD_NAME=$(kubectl get pods --namespace default -l "app=funcx-funcx-web-service" -o jsonpath="{.items[0].metadata.name}") && kubectl port-forward $POD_NAME 5000:5000
kubectl port-forward funcx-redis-master-0 6379:6379
```

Clone this repository and run it with `python run.py`.

Now, deploy an endpoint, replace the endpoint UUID you received or chose with the one in the test script above, and run the test script.
