"""
Passthrough authentication and permissions for Drycc Resources.

Authenticates users by forwarding tokens to the Drycc Controller API.
"""
import logging
from django.core.cache import cache
from django.conf import settings
from rest_framework import authentication, permissions
from rest_framework import exceptions

from api.clients.controller import ControllerClient

logger = logging.getLogger(__name__)


class LightweightUser:
    """
    A lightweight user object that mimics Django's User interface
    for authentication purposes.
    """
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin
        self.is_authenticated = True
        self.is_superuser = is_admin
        self.is_staff = is_admin

    def __str__(self):
        return self.username


class ControllerPassthroughAuthentication(authentication.BaseAuthentication):
    """
    Authentication class that validates tokens by calling the Drycc Controller's
    /v2/auth/whoami/ endpoint.
    """
    keywords = ('token', 'bearer')
    controller = ControllerClient()

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).split()
        if not auth_header or auth_header[0].decode().lower() not in self.keywords:
            return None

        if len(auth_header) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided.')
        elif len(auth_header) > 2:
            raise exceptions.AuthenticationFailed(
                'Invalid token header. Token string should not contain spaces.')

        token = auth_header[1].decode()

        # Check cache first
        cache_key = f"auth:{token}"
        cached_user = cache.get(cache_key)
        if cached_user:
            return cached_user, token

        # Call controller to validate token
        try:
            user_data = self.controller.whoami(token)
            user = LightweightUser(
                id=user_data['id'],
                username=user_data['username'],
                is_admin=user_data.get('is_superuser', False)
            )
            # Cache the user object
            cache.set(cache_key, user, timeout=settings.DRYCC_CONTROLLER_AUTH_CACHE_TTL)
            return user, token
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            raise exceptions.AuthenticationFailed('Invalid token.')

    def authenticate_header(self, request):
        return 'token'


class IsAppUser(permissions.BasePermission):
    """
    Permission class that checks if the current user has access to the app's workspace.

    - Non-viewer roles have full permissions
    - Viewer roles only have read-only access (GET/HEAD/OPTIONS)
    """
    controller = ControllerClient()

    def _get_token(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '').split()
        if len(auth_header) >= 2:
            return auth_header[1]
        return None

    def has_permission(self, request, view):
        # Superusers always have access
        if getattr(request.user, 'is_superuser', False):
            return True

        token = self._get_token(request)
        if not token:
            return False

        app_id = view.kwargs.get('id')
        if not app_id:
            # For views not tied to specific app (like /services/)
            return request.method in permissions.SAFE_METHODS

        try:
            app_data = self.controller.get_app(token, app_id)
            workspace_id = app_data.get('workspace')
            if not workspace_id:
                return False

            workspace_data = self.controller.get_workspace(token, workspace_id)
            role = workspace_data.get('role', 'viewer')

            if request.method in ["GET", "HEAD", "OPTIONS"]:
                allowed_roles = ["viewer", "member", "admin"]
            elif request.method in ["POST", "PUT", "PATCH"]:
                allowed_roles = ["member", "admin"]
            else:
                allowed_roles = ["admin"]

            return role in allowed_roles
        except Exception as e:
            logger.warning("Permission check failed: %s", e)
            return False

    def has_object_permission(self, request, view, obj):
        # Superusers always have access
        if getattr(request.user, 'is_superuser', False):
            return True

        token = self._get_token(request)
        if not token:
            return False

        try:
            workspace_data = self.controller.get_workspace(token, obj.workspace_id)
            role = workspace_data.get('role', 'viewer')

            if request.method in ["GET", "HEAD", "OPTIONS"]:
                allowed_roles = ["viewer", "member", "admin"]
            elif request.method in ["POST", "PUT", "PATCH"]:
                allowed_roles = ["member", "admin"]
            else:
                allowed_roles = ["admin"]

            return role in allowed_roles
        except Exception as e:
            logger.warning("Object permission check failed: %s", e)
            return False
