import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class WebSocketConnection:
    def __init__(self, ws):
        self.ws = ws
        self.last_send_time = time.time()

    async def send(self, msg):
        self.last_send_time = time.time()
        await self.ws.send(msg)

    async def check_idle(self):
        while True:
            now = time.time()
            # if no messages are sent to this connection in a 10 minute
            # time span, close the connection
            if now - self.last_send_time > 10 * 60:
                logger.debug('Closing WebSocket connection for being idle too long')
                await self.ws.close()
                return

            await asyncio.sleep(60)
