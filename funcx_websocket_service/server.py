import asyncio
import json
import logging
import websockets
import aioredis
import aio_pika
import http
from concurrent.futures import CancelledError
from websockets.exceptions import ConnectionClosedOK
from funcx_websocket_service.auth import AuthClient
from funcx_websocket_service.version import VERSION, MIN_SDK_VERSION

logger = logging.getLogger(__name__)


class WebSocketServer:
    def __init__(self, redis_host, redis_port, rabbitmq_host, web_service_uri):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.rabbitmq_host = rabbitmq_host
        self.funcx_service_address = f'{web_service_uri}/v2'
        logger.info(f"funcx_service_address : {self.funcx_service_address}")
        self.auth_client = AuthClient(self.funcx_service_address)

        self.loop = asyncio.get_event_loop()

        self.ws_port = 6000

        start_server = websockets.serve(self.handle_connection, '0.0.0.0', self.ws_port, process_request=self.process_request)

        self.loop.run_until_complete(start_server)
        self.loop.run_until_complete(self.on_server_started())
        self.loop.run_forever()

    async def on_server_started(self):
        logger.info(f'WebSocket Server started on port {self.ws_port}')

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

    async def mq_receive_task(self, ws, task_group_id):
        try:
            await self.mq_receive(ws, task_group_id)
        except CancelledError:
            logger.debug(f'Message consumer {task_group_id} stopped due to cancellation')
        except ConnectionClosedOK:
            logger.debug(f'Message consumer {task_group_id} stopped due to WebSocket connection close')
        except Exception as e:
            logger.exception(e)

    async def mq_receive(self, ws, task_group_id):
        """
        Receives completed tasks based on task_group_id on a RabbitMQ queue and sends them back
        to the user, assuming they own the task group they have requested
        """
        # confirm with the web service that this user can access this task_group_id
        headers = ws.request_headers
        task_group_info = await self.auth_client.authorize_task_group(headers, task_group_id)
        if not task_group_info:
            return

        logger.debug(f'Message consumer {task_group_id} started')

        uri = f'amqp://funcx:rabbitmq@{self.rabbitmq_host}/'
        mq_connection = await aio_pika.connect_robust(uri, loop=self.loop)

        async with mq_connection:
            channel = await mq_connection.channel()
            exchange = await channel.declare_exchange('tasks', aio_pika.ExchangeType.DIRECT)
            queue = await channel.declare_queue(task_group_id)
            await queue.bind(exchange, routing_key=task_group_id)

            async with queue.iterator() as queue_iter:
                # If the asyncio task is cancelled when no previous queue message is being processed,
                # a CancelledError will occur here allowing a clean exit from the asyncio task
                async for message in queue_iter:
                    # Setting requeue to True indicates that if an exception occurs within this
                    # context manager, the message should be requeued. This is useful because it
                    # allows requeueing of RabbitMQ messages that are not successfully sent over
                    # the WebSocket connection. Usually this is because this async message handler
                    # task has been cancelled externally, due to the WebSocket connection being
                    # closed.
                    async with message.process(requeue=True):
                        task_id = message.body.decode('utf-8')
                        try:
                            logger.debug(f'Got Task ID: {task_id}')
                            poll_result = await self.poll_task(task_id)
                            if poll_result:
                                # If the asyncio task is cancelled when a WebSocket message is being sent,
                                # it is because the WebSocket connection has been closed. This means that
                                # either a ConnectionClosedOK exception should occur here, or a CancelledError
                                # should occur here. Regardless, the RabbitMQ message will be requeued safely
                                await ws.send(json.dumps(poll_result))
                        except Exception as e:
                            logger.debug(f'Task {task_id} requeued due to exception')
                            raise e

    def ws_message_consumer(self, ws, msg):
        return self.loop.create_task(self.mq_receive_task(ws, msg))

    async def handle_connection(self, ws, path):
        logger.debug('New WebSocket connection created')
        message_consumer_tasks = []
        try:
            async for msg in ws:
                message_consumer_tasks.append(self.ws_message_consumer(ws, msg))
        # this will likely happen from the connected client not calling
        # ws.close() to have a clean closing handshake
        except Exception as e:
            logger.debug(f'Connection closed with exception: {e}')

        logger.info('WebSocket connection closed, cancelling message consumers')
        for task in message_consumer_tasks:
            task.cancel()

    async def process_request(self, path, headers):
        if path == '/v2/health':
            version_data = {
                "version": VERSION,
                "min_sdk_version": MIN_SDK_VERSION
            }
            json_str = json.dumps(version_data)
            res_str = f"{json_str}\n"

            return http.HTTPStatus.OK, [], res_str.encode()
        return await self.auth_client.authenticate(headers)
