import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """A WebSocket connection that has important WebSocket session properties
    for a single connected client, along with holding the client's WebSocket
    object which is created by the server
    """

    def __init__(self, ws, idle_close_time: int = 10 * 60):
        """Initialize the WebSocket connection

        Parameters
        ----------
        ws : WebSocket
            WebSocket connection object created by websockets library

        idle_close_time : int
            Time in seconds to wait for this connection to be idle before
            it is closed. Idle for n seconds mean that no outgoing message has
            been sent to the WebSocket for n seconds
        """
        self.ws = ws
        self.idle_close_time = idle_close_time
        self.last_send_time = time.time()

    async def send(self, msg: str):
        """Send a message to this WebSocket connection. We want to call this
        method for any sending because we want to keep track of when the last
        message was sent to each connected client

        Parameters
        ----------
        msg : str
            Message to send
        """
        self.last_send_time = time.time()
        await self.ws.send(msg)

    async def check_idle(self):
        """Awaitable to check on a regular interval whether or not this
        WebSocket connection has become idle, closing it if it has
        """
        while True:
            now = time.time()
            # if no messages are sent to this connection in a 10 minute
            # time span, close the connection
            if now - self.last_send_time > self.idle_close_time:
                logger.debug("Closing WebSocket connection for being idle too long")
                await self.ws.close()
                return

            await asyncio.sleep(60)
