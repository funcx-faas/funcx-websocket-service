import asyncio
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

    async def message_consumer(self, ws, msg):
        await ws.send('hello')
        res = await self.rc.blpop('a', timeout=0)
        data = str(res)
        await ws.send(data)

    async def handle_connection(self, ws, path):
        async for msg in ws:
            await self.message_consumer(ws, msg)
