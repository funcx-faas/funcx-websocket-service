import asyncio
import json
import websockets
import aioredis
from globus_sdk import ConfidentialAppAuthClient


class WebSocketServer:
    def __init__(self, redis_host, redis_port, globus_client, globus_key):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.globus_client = globus_client
        self.globus_key = globus_key

        start_server = websockets.serve(self.handle_connection, '0.0.0.0', 6000, process_request=self.process_request)

        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def get_redis_client(self):
        redis_client = await aioredis.create_redis((self.redis_host, self.redis_port))
        return redis_client

    async def poll_task(self, task_id):
        rc = await self.get_redis_client()
        task_hname = f'task_{task_id}'
        exists = await rc.exists(task_hname)
        if not exists:
            return {
                'task_id': task_id,
                'status': 'Failed',
                'reason': 'Unknown task id'
            }

        task_result = await rc.hget(task_hname, 'result')
        task_exception = await rc.hget(task_hname, 'exception')
        if task_result is None and task_exception is None:
            return None

        task_status = await rc.hget(task_hname, 'status')
        task_completion_t = await rc.hget(task_hname, 'completion_time')

        if task_result:
            task_result = task_result.decode('utf-8')
        if task_exception:
            task_exception = task_exception.decode('utf-8')
        if task_status:
            task_status = task_status.decode('utf-8')
        if task_completion_t:
            task_completion_t = task_completion_t.decode('utf-8')

        res = {
            'task_id': task_id,
            'status': task_status,
            'result': task_result,
            'completion_t': task_completion_t,
            'exception': task_exception
        }

        rc.close()
        await rc.wait_closed()
        return res

    async def poll_tasks(self, ws, task_ids):
        remaining_task_ids = set(task_ids)
        for i in range(30):
            to_remove = set()
            for task_id in remaining_task_ids:
                poll_result = await self.poll_task(task_id)
                if poll_result:
                    to_remove.add(task_id)
                    await ws.send(json.dumps(poll_result))

            remaining_task_ids = remaining_task_ids - to_remove

            if len(remaining_task_ids) == 0:
                return

            # poll every 1s
            await asyncio.sleep(1)

        # tasks that exist but never got a result/exception
        for task_id in remaining_task_ids:
            timeout_result = {
                'task_id': task_id,
                'status': 'Failed',
                'reason': 'Task polling timeout'
            }
            await ws.send(json.dumps(timeout_result))

    async def message_consumer(self, ws, msg):
        try:
            data = json.loads(msg)
            assert type(data) is list
            for s in data:
                assert isinstance(s, str)
        except Exception:
            return

        task_ids = data
        await self.poll_tasks(ws, task_ids)

    async def handle_connection(self, ws, path):
        # headers = ws.request_headers
        async for msg in ws:
            await self.message_consumer(ws, msg)

    async def process_request(self, path, headers):
        try:
            token = headers['Authorization']
        except Exception:
            return (401, [], b'You must be logged in to perform this function.\n')
        token = str.replace(str(token), 'Bearer ', '')

        try:
            client = self.get_auth_client()
            auth_detail = client.oauth2_token_introspect(token)
            user_name = auth_detail['username']
        except Exception:
            return (400, [], b'Failed to authenticate user.\n')

        return None

    def get_auth_client(self):
        return ConfidentialAppAuthClient(self.globus_client, self.globus_key)
