import os
import time
import asyncio
import websockets
import redis

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = os.environ.get('REDIS_PORT')

if REDIS_HOST is None:
    REDIS_HOST = '127.0.0.1'

if REDIS_PORT is None:
    REDIS_PORT = 6379

rc = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
# task_id = '123'
# print(rc.hget(f"task_{task_id}", 'result'))

async def consumer(ws, msg):
    await ws.send('hello')
    data = str(rc.blpop(['a'], timeout=0))
    await ws.send(data)

async def handler(ws, path):
    async for msg in ws:
        await consumer(ws, msg)
    # await print_letters()

start_server = websockets.serve(handler, '0.0.0.0', 6000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
