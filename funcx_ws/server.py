import asyncio
import json
import websockets
import aioredis


class WebSocketServer:
    def __init__(self, redis_host, redis_port):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.rc = None

        start_server = websockets.serve(self.handle_connection, '0.0.0.0', 6000)

        asyncio.get_event_loop().run_until_complete(self.init_redis_client())
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

    async def init_redis_client(self):
        self.rc = await aioredis.create_redis_pool((self.redis_host, self.redis_port))

    async def poll_task(self, task_id):
        task_hname = f'task_{task_id}'
        exists = await self.rc.exists(task_hname)
        if not exists:
            return {
                'task_id': task_id,
                'status': 'Failed',
                'reason': 'Unknown task id'
            }

        task_result = await self.rc.hget(task_hname, 'result')
        task_exception = await self.rc.hget(task_hname, 'exception')
        if task_result is None and task_exception is None:
            return None

        task_status = await self.rc.hget(task_hname, 'status')
        task_completion_t = await self.rc.hget(task_hname, 'completion_time')

        return {
            'task_id': task_id,
            'status': task_status,
            'result': task_result,
            'completion_t': task_completion_t,
            'exception': task_exception
        }

    async def poll_tasks(self, ws, task_ids):
        remaining_task_ids = set(task_ids)
        for i in range(30):
            for task_id in remaining_task_ids:
                poll_result = await self.poll_task(task_id)
                if poll_result:
                    remaining_task_ids.remove(task_id)
                    await ws.send(json.dumps(poll_result))

            if len(remaining_task_ids) == 0:
                return

            # poll every 1s
            await asyncio.sleep(1)

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
        async for msg in ws:
            await self.message_consumer(ws, msg)
