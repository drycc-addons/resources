"""
HTTP client for communicating with the Drycc Controller.
"""
import logging
import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ControllerClient:
    """
    Client for making HTTP requests to the Drycc Controller API.
    """
    def __init__(self, timeout=5, max_retries=2):
        self.base_url = settings.DRYCC_CONTROLLER_URL.rstrip('/')
        self.timeout = timeout
        self.verify_tls = settings.DRYCC_CONTROLLER_VERIFY_TLS

        # Setup session with retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _make_request(self, method, endpoint, token, **kwargs):
        """Make an HTTP request to the controller."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'token {token}',
            'Content-Type': 'application/json',
        }

        try:
            response = self.session.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_tls,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Controller API request failed: {e}")
            raise

    def whoami(self, token):
        """
        Get current user information.

        Returns:
            dict: User data with id, username, is_superuser fields
        """
        return self._make_request('GET', '/v2/auth/whoami/', token)

    def get_workspace(self, token, workspace_id):
        """
        Get workspace information.

        Args:
            token: Authentication token
            workspace_id: Workspace identifier

        Returns:
            dict: Workspace data including members and roles
        """
        return self._make_request('GET', f'/v2/workspaces/{workspace_id}/', token)

    def get_app(self, token, app_id):
        """
        Get application information.

        Args:
            token: Authentication token
            app_id: Application identifier

        Returns:
            dict: App data including workspace field
        """
        return self._make_request('GET', f'/v2/apps/{app_id}/', token)
