import asyncio
import json
import logging
import websockets
from websockets.exceptions import ConnectionClosedError
import aioredis
import aio_pika
from funcx_ws.auth import AuthClient


logger = logging.getLogger(__name__)


class WebSocketServer:
    def __init__(self, redis_host, redis_port):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.funcx_service_address = 'http://localhost:5000/v1'
        # self.funcx_service_address = 'https://api.funcx.org/v1'
        self.auth_client = AuthClient(self.funcx_service_address)

        self.loop = asyncio.get_event_loop()

        start_server = websockets.serve(self.handle_connection, '0.0.0.0', 6000, process_request=self.process_request)

        self.loop.run_until_complete(self.mq_connect())
        self.loop.run_until_complete(start_server)
        self.loop.run_forever()

    async def mq_connect(self):
        self.mq_connection = await aio_pika.connect_robust(
            "amqp://funcx:rabbitmq@127.0.0.1/", loop=self.loop
        )

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

        # TODO: delete task from redis

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

    async def mq_receive(self, ws, batch_id):
        async with self.mq_connection:
            channel = await self.mq_connection.channel()
            exchange = await channel.declare_exchange('tasks', aio_pika.ExchangeType.DIRECT)
            queue = await channel.declare_queue(batch_id)
            await queue.bind(exchange, routing_key=batch_id)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        task_id = message.body.decode('utf-8')
                        poll_result = await self.poll_task(task_id)
                        if poll_result:
                            await ws.send(json.dumps(poll_result))

    async def message_consumer(self, ws, msg):
        await self.mq_receive(ws, msg)
        # try:
        #     data = json.loads(msg)
        #     assert type(data) is list
        #     for s in data:
        #         assert isinstance(s, str)
        # except Exception:
        #     return

        # task_ids = data
        # await self.poll_tasks(ws, task_ids)

    async def handle_connection(self, ws, path):
        # headers = ws.request_headers
        try:
            async for msg in ws:
                await self.message_consumer(ws, msg)
        # this will likely happen from the connected client not calling
        # ws.close() to have a clean closing handshake
        except ConnectionClosedError:
            logger.debug('connection closed with errors')

    async def process_request(self, path, headers):
        return await self.auth_client.authenticate(headers)
