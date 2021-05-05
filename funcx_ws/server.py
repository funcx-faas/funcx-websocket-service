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
    def __init__(self, redis_host, redis_port, rabbitmq_host, web_service_host):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.rabbitmq_host = rabbitmq_host
        self.funcx_service_address = f'http://{web_service_host}:5000/v1'
        # self.funcx_service_address = 'https://api.funcx.org/v1'
        self.auth_client = AuthClient(self.funcx_service_address)

        self.loop = asyncio.get_event_loop()

        start_server = websockets.serve(self.handle_connection, '0.0.0.0', 6000, process_request=self.process_request)

        self.loop.run_until_complete(start_server)
        self.loop.run_forever()

    async def get_redis_client(self):
        redis_client = await aioredis.create_redis((self.redis_host, self.redis_port))
        return redis_client

    async def poll_task(self, task_id):
        """
        Gets task info from redis
        """
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

    async def mq_receive(self, ws, batch_id):
        """
        Receives completed batch tasks on a RabbitMQ queue and sends them back
        to the user, assuming they own the batch they have requested
        """
        # confirm with the web service that this user can access this batch_id
        headers = ws.request_headers
        batch_info = await self.auth_client.authorize_batch(headers, batch_id)
        if not batch_info:
            return

        uri = f'amqp://funcx:rabbitmq@{self.rabbitmq_host}/'
        mq_connection = await aio_pika.connect_robust(uri, loop=self.loop)

        async with mq_connection:
            channel = await mq_connection.channel()
            exchange = await channel.declare_exchange('tasks', aio_pika.ExchangeType.DIRECT)
            queue = await channel.declare_queue(batch_id)
            await queue.bind(exchange, routing_key=batch_id)

            result_count = 0

            # close everything when the batch runs out of tasks
            # TODO: delete tasks and batches from redis when they are no longer needed
            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        task_id = message.body.decode('utf-8')
                        poll_result = await self.poll_task(task_id)
                        if poll_result:
                            await ws.send(json.dumps(poll_result))
                            result_count += 1
                            if result_count == batch_info['task_count']:
                                break
            await queue.delete()

    async def message_consumer(self, ws, msg):
        await self.mq_receive(ws, msg)

    async def handle_connection(self, ws, path):
        try:
            async for msg in ws:
                await self.message_consumer(ws, msg)
        # this will likely happen from the connected client not calling
        # ws.close() to have a clean closing handshake
        except ConnectionClosedError:
            logger.debug('connection closed with errors')

    async def process_request(self, path, headers):
        return await self.auth_client.authenticate(headers)
