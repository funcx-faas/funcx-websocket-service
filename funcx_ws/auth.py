import logging
import aiohttp

logger = logging.getLogger(__name__)


class AuthClient:
    def __init__(self, funcx_service_address):
        self.funcx_service_address = funcx_service_address
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def authenticate(self, headers):
        try:
            auth_header = headers['Authorization']
        except Exception:
            return (401, [], b'You must be logged in to perform this function.\n')
        req_headers = {'Authorization': auth_header}

        async with self.session.get(self.full_path('/authenticate'), headers=req_headers) as r:
            if r.status != 200:
                return (400, [], b'Failed to authenticate user.\n')

        return None

    async def authorize_task_group(self, headers, task_group_id):
        try:
            auth_header = headers['Authorization']
        except Exception:
            return None
        req_headers = {'Authorization': auth_header}

        async with self.session.get(self.full_path(f'/task_groups/{task_group_id}'), headers=req_headers) as r:
            if r.status != 200:
                return None
            return await r.json()

    def full_path(self, path):
        return f'{self.funcx_service_address}{path}'
