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
from funcx_websocket_service.connection import WebSocketConnection
from funcx_websocket_service.version import VERSION, MIN_SDK_VERSION

logger = logging.getLogger(__name__)


class WebSocketServer:
    """An async WebSocket server that authenticates WebSocket clients, listens
    for RabbitMQ messages, and sends along those task updates to the intended
    clients.
    """

    def __init__(
        self,
        redis_host: str,
        redis_port: str,
        rabbitmq_host: str,
        web_service_uri: str
    ):
        """Initialize and run the server

        Parameters
        ----------
        redis_host : str
            Redis host

        redis_port : str
            Redis port

        rabbitmq_host : str
            RabbitMQ host

        web_service_uri : str
            Web Service URI to use, likely an internal k8s DNS name
        """
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
        logger.info(f'WebSocket Server started on port {self.ws_port}')
        self.loop.run_forever()

    def get_redis(self):
        """Gets redis instance using provided redis host and port for this server

        Returns
        -------
        Redis instance
        """
        url = f"redis://{self.redis_host}:{self.redis_port}"
        redis = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
        return redis

    async def get_task_data(self, rc: aioredis.Redis, task_id: str):
        """Gets additional useful properties about a task
        (user_id, function_id, etc.)

        Parameters
        ----------
        rc : aioredis.Redis
            Async redis client to use for getting task info

        task_id : str
            Task ID to query

        Returns
        -------
        Dict
            Task data values
        """
        task_hname = f'task_{task_id}'
        exists = await rc.exists(task_hname)

        # these are the keys we need to pull from the redis task object
        keys = ['user_id', 'function_id', 'endpoint', 'container']
        # these are the keys we want to assign to the results in a dict,
        # in the same order as the keys we are fetching above
        final_keys = ['user_id', 'function_id', 'endpoint_id', 'container_id']

        empty_dict = dict.fromkeys(final_keys, None)
        if not exists:
            return empty_dict

        values = await rc.hmget(task_hname, keys)
        if not values:
            return empty_dict

        res = dict(zip(final_keys, values))
        res['user_id'] = int(res['user_id'])
        return res

    async def poll_task(self, rc: aioredis.Redis, task_id: str):
        """Gets task info from redis

        Parameters
        ----------
        rc : aioredis.Redis
            Async redis client to use for getting task info

        task_id : str
            Task ID to query

        Returns
        -------
        None: if task exists in redis but is not complete
        Dict of task status: if task is not found or is complete
        """
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

        res = {
            'task_id': task_id,
            'status': task_status,
            'result': task_result,
            'completion_t': task_completion_t,
            'exception': task_exception
        }

        return res

    async def handle_mq_message(self, ws_conn: WebSocketConnection, task_group_id: str, message):
        """Handles new messages coming off of the RabbitMQ queue

        Parameters
        ----------
        ws_conn : WebSocketConnection
            WebSocket connection

        task_group_id : str
            Task group ID for the queue

        message : RabbitMQ message
            Message containing data sent through the queue
        """
        extra_logging = None
        task_id = message.body.decode('utf-8')
        try:
            redis = self.get_redis()

            async with redis.client() as rc:
                task_data = await self.get_task_data(rc, task_id)
                extra_logging = {
                    "task_id": task_id,
                    "task_group_id": task_group_id,
                    "log_type": "task_transition"
                }
                extra_logging.update(task_data)

                poll_result = await self.poll_task(rc, task_id)

            if poll_result:
                # If the asyncio task is cancelled when a WebSocket message is being sent,
                # it is because the WebSocket connection has been closed. This means that
                # either a ConnectionClosedOK exception should occur here, or a CancelledError
                # should occur here. Regardless, the RabbitMQ message will be requeued safely
                await ws_conn.send(json.dumps(poll_result))
        except Exception:
            logger.debug(f'Task {task_id} requeued due to exception', extra={
                "log_type": "task_requeued_rabbitmq",
                "task_id": task_id
            })
            raise
        else:
            logger.info('dispatched_to_user', extra=extra_logging)

    async def mq_receive_task(self, ws_conn: WebSocketConnection, task_group_id: str):
        """asyncio awaitable which handles expected exceptions from the
        RabbitMQ message handler

        Parameters
        ----------
        ws_conn : WebSocketConnection
            WebSocket connection

        task_group_id : str
            Task group ID to wait for RabbitMQ messages on
        """
        try:
            await self.mq_receive(ws_conn, task_group_id)
        except CancelledError:
            logger.debug(f'Message consumer {task_group_id} stopped due to cancellation')
        except ConnectionClosedOK:
            logger.debug(f'Message consumer {task_group_id} stopped due to WebSocket connection close')
        except Exception as e:
            logger.exception(e)

    async def mq_receive(self, ws_conn: WebSocketConnection, task_group_id: str):
        """
        Receives completed tasks based on task_group_id on a RabbitMQ queue and sends them back
        to the user, after first confirming they own the task group they have requested

        Parameters
        ----------
        ws_conn : WebSocketConnection
            WebSocket connection

        task_group_id : str
            Task group ID to wait for RabbitMQ messages on
        """
        ws = ws_conn.ws
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
                        await self.handle_mq_message(ws_conn, task_group_id, message)

    def ws_message_consumer(self, ws_conn: WebSocketConnection, msg: str):
        """Consumer for incoming WebSocket messages

        Parameters
        ----------
        ws_conn : WebSocketConnection
            WebSocket connection

        msg : str
            Incoming message

        Returns
        -------
        asyncio.Task
            async Task to process incoming task updates based on the sent WebSocket message
        """
        return self.loop.create_task(self.mq_receive_task(ws_conn, msg))

    async def handle_connection(self, ws, path):
        """Handles new WebSocket connection by creating new asyncio task to process
        incoming messages, then cancels all of these tasks when the WebSocket closes

        Parameters
        ----------
        ws : WebSocket connection
            New WebSocket connection

        path : str
            Path of request
        """
        logger.debug('New WebSocket connection created')
        ws_conn = WebSocketConnection(ws)
        check_idle_task = self.loop.create_task(ws_conn.check_idle())
        conn_tasks = [check_idle_task]
        try:
            async for msg in ws:
                conn_tasks.append(self.ws_message_consumer(ws_conn, msg))
        # this will likely happen from the connected client not calling
        # ws.close() to have a clean closing handshake
        except Exception as e:
            logger.debug(f'Connection closed with exception: {e}')

        logger.info('WebSocket connection closed, cancelling message consumers')
        for task in conn_tasks:
            task.cancel()

    async def process_request(self, path, headers):
        """Processes HTTP request before upgrading to WebSocket connection. This
        includes an HTTP health check that does not become a WebSocket connection.
        If this health path is not requested, the new WebSocket connection will be
        authenticated based on headers sent in this initial handshake.

        Parameters
        ----------
        path : str
            Path of request

        headers : websockets.datastructures.Headers
            Request headers

        Returns
        -------
        None: if the user is authenticated successfully and a WebSocket
            connection should be made
        (status, headers, response): if a WebSocket connection should not be created
            and a simple HTTP response should be sent instead, either because the health
            check path was requested or because the user could not be authenticated
        """
        if path == '/v2/health':
            version_data = {
                "version": VERSION,
                "min_sdk_version": MIN_SDK_VERSION
            }
            json_str = json.dumps(version_data)
            res_str = f"{json_str}\n"

            return http.HTTPStatus.OK, [], res_str.encode()
        return await self.auth_client.authenticate(headers)
