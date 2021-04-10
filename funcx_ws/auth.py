import logging
import aiohttp

logger = logging.getLogger(__name__)


class AuthClient:
    def __init__(self, funcx_service_address):
        self.funcx_service_address = funcx_service_address

    async def authenticate(self, headers):
        try:
            auth_header = headers['Authorization']
        except Exception:
            return (401, [], b'You must be logged in to perform this function.\n')
        req_headers = {'Authorization': auth_header}

        r = await self.get('/authenticate', req_headers)
        if r.status != 200:
            return (400, [], b'Failed to authenticate user.\n')

        return None

    async def authorize_task(self, headers, task_id):
        try:
            auth_header = headers['Authorization']
        except Exception:
            return False
        req_headers = {'Authorization': auth_header}

        r = await self.get(f'/authorize_task/{task_id}', req_headers)
        if r.status != 200:
            return False

        return True

    async def get(self, path, headers):
        full_path = f'{self.funcx_service_address}{path}'
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(full_path) as r:
                return r
