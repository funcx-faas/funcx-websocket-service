import logging
import aiohttp

logger = logging.getLogger(__name__)


class AuthClient:
    """An auth client that authenticates users and authorizes them to receive
    task group updates by sending HTTP requests to the web service
    """
    def __init__(self, funcx_service_address: str):
        """Initialize auth client

        Parameters
        ----------
        funcx_service_address : str
            Full FuncX service address
        """
        self.funcx_service_address = funcx_service_address
        timeout = aiohttp.ClientTimeout(total=10)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def authenticate(self, headers):
        """Authenticates a user based on an Authorization header by passing the header
        along to test authentication with the web service

        Parameters
        ----------
        headers : websockets.datastructures.Headers
            Request headers

        Returns
        -------
        None: if the user is authenticated successfully and a WebSocket
            connection should be made
        (status, headers, response): if authentication fails and a failure response
            is needed
        """
        try:
            auth_header = headers['Authorization']
        except Exception:
            return (401, [], b'You must be logged in to perform this function.\n')
        req_headers = {'Authorization': auth_header}

        async with self.session.get(self.full_path('/authenticate'), headers=req_headers) as r:
            if r.status != 200:
                return (400, [], b'Failed to authenticate user.\n')

        return None

    async def authorize_task_group(self, headers, task_group_id: str):
        """Authorizes a user to get status updates from a Task Group by sending an
        HTTP request to the web service to confirm they are authorized

        Parameters
        ----------
        headers : websockets.datastructures.Headers
            Request headers

        task_group_id : str
            Task Group ID to authorize for

        Returns
        -------
        None: if the user is not authorized
        Dict of task group data: if the user is authorized
        """
        try:
            auth_header = headers['Authorization']
        except Exception:
            return None
        req_headers = {'Authorization': auth_header}

        async with self.session.get(self.full_path(f'/task_groups/{task_group_id}'), headers=req_headers) as r:
            if r.status != 200:
                return None
            return await r.json()

    def full_path(self, path: str):
        """Create a full FuncX web service path to make an HTTP request

        Parameters
        ----------
        path : str
            Request path for building full path

        Returns
        -------
        str
            Full path for HTTP request
        """
        return f'{self.funcx_service_address}{path}'
