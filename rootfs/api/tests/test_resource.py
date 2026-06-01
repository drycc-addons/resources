"""
Tests for the Resource model and views.
"""
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from api.models import Resource
from api.passthrough import LightweightUser


class ResourceModelTest(TestCase):
    """Test the Resource model."""

    def setUp(self):
        self.resource = Resource.objects.create(
            app_id='test-app',
            workspace_id='test-workspace',
            name='test-resource',
            plan='postgresql:default',
            options={'size': 'small'}
        )

    def test_resource_creation(self):
        """Test that a resource can be created."""
        self.assertEqual(self.resource.app_id, 'test-app')
        self.assertEqual(self.resource.workspace_id, 'test-workspace')
        self.assertEqual(self.resource.name, 'test-resource')
        self.assertEqual(self.resource.plan, 'postgresql:default')

    def test_resource_str(self):
        """Test the string representation of a resource."""
        self.assertEqual(str(self.resource), 'test-resource')

    def test_resource_unique_constraint(self):
        """Test that app_id and name must be unique together."""
        with self.assertRaises(Exception):
            Resource.objects.create(
                app_id='test-app',
                workspace_id='test-workspace',
                name='test-resource',
                plan='postgresql:default'
            )

    @patch('api.models.resource.get_scheduler')
    def test_resource_services(self, mock_get_scheduler):
        """Test listing available services."""
        mock_scheduler = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            'items': [
                {
                    'spec': {
                        'externalID': 'service-1',
                        'externalName': 'postgresql',
                        'planUpdatable': True
                    }
                }
            ]
        }
        mock_scheduler.svcat.get_serviceclasses.return_value = mock_response
        mock_get_scheduler.return_value = mock_scheduler

        services = Resource.services()
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]['name'], 'postgresql')


@override_settings(
    DRYCC_CONTROLLER_URL='http://test-controller',
    DRYCC_CONTROLLER_AUTH_CACHE_TTL=30
)
class ResourceAPITest(APITestCase):
    """Test the Resource API endpoints."""

    def setUp(self):
        self.user = LightweightUser(
            id=1,
            username='testuser',
            is_admin=False
        )
        self.resource = Resource.objects.create(
            app_id='test-app',
            workspace_id='test-workspace',
            name='test-resource',
            plan='postgresql:default',
            status='Ready',
            binding=None
        )

    @patch('api.passthrough.ControllerClient.whoami')
    def test_list_resources(self, mock_whoami):
        """Test listing resources for an app."""
        mock_whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.get('/apps/test-app/resources/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'test-resource')

    @patch('api.passthrough.ControllerClient.get_workspace')
    @patch('api.passthrough.ControllerClient.whoami')
    def test_retrieve_resource(self, mock_whoami, mock_get_workspace):
        """Test retrieving a single resource."""
        mock_whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }
        mock_get_workspace.return_value = {
            'id': 'test-workspace',
            'members': [{'user': 1, 'role': 'member'}]
        }

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.get('/apps/test-app/resources/test-resource/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test-resource')

    @patch('api.views.ControllerClient.get_app')
    @patch('api.passthrough.ControllerClient.get_workspace')
    @patch('api.passthrough.ControllerClient.whoami')
    @patch('api.models.resource.Resource.attach')
    def test_create_resource(self, mock_attach, mock_whoami, mock_get_workspace, mock_get_app):
        """Test creating a new resource."""
        mock_whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }
        mock_get_workspace.return_value = {
            'id': 'test-workspace',
            'members': [{'user': 1, 'role': 'member'}]
        }
        mock_get_app.return_value = {
            'id': 'test-app',
            'workspace': 'test-workspace'
        }
        mock_attach.return_value = None

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        data = {
            'name': 'new-resource',
            'plan': 'postgresql:default',
            'options': {'size': 'small'}
        }
        response = self.client.post('/apps/test-app/resources/', data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'new-resource')
        self.assertEqual(response.data['workspace_id'], 'test-workspace')

    @patch('api.passthrough.ControllerClient.get_workspace')
    @patch('api.passthrough.ControllerClient.whoami')
    @patch('api.models.resource.Resource.delete')
    def test_delete_resource(self, mock_delete, mock_whoami, mock_get_workspace):
        """Test deleting a resource."""
        mock_whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }
        mock_get_workspace.return_value = {
            'id': 'test-workspace',
            'members': [{'user': 1, 'role': 'admin'}]
        }
        mock_delete.return_value = None

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.delete('/apps/test-app/resources/test-resource/')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PassthroughAuthTest(TestCase):
    """Test the passthrough authentication."""

    @patch('api.clients.controller.ControllerClient.whoami')
    def test_authentication_success(self, mock_whoami):
        """Test successful authentication."""
        mock_whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }

        from api.passthrough import ControllerPassthroughAuthentication
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/', HTTP_AUTHORIZATION='token test-token')
        
        auth = ControllerPassthroughAuthentication()
        user, token = auth.authenticate(request)
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(token, 'test-token')

    def test_authentication_no_header(self):
        """Test authentication with no authorization header."""
        from api.passthrough import ControllerPassthroughAuthentication
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/')
        
        auth = ControllerPassthroughAuthentication()
        result = auth.authenticate(request)
        
        self.assertIsNone(result)


class PermissionTest(TestCase):
    """Test the permission system."""

    @patch('api.clients.controller.ControllerClient.get_workspace')
    def test_permission_member_role(self, mock_get_workspace):
        """Test that members have full access."""
        mock_get_workspace.return_value = {
            'id': 'test-workspace',
            'members': [{'user': 1, 'role': 'member'}]
        }

        from api.passthrough import IsAppUser, LightweightUser
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get('/', HTTP_AUTHORIZATION='token test-token')
        request.user = LightweightUser(id=1, username='testuser')
        
        resource = Resource(
            app_id='test-app',
            workspace_id='test-workspace',
            name='test-resource'
        )
        
        perm = IsAppUser()
        result = perm.has_object_permission(request, None, resource)
        
        self.assertTrue(result)

    @patch('api.clients.controller.ControllerClient.get_workspace')
    def test_permission_viewer_readonly(self, mock_get_workspace):
        """Test that viewers have read-only access."""
        mock_get_workspace.return_value = {
            'id': 'test-workspace',
            'members': [{'user': 1, 'role': 'viewer'}]
        }

        from api.passthrough import IsAppUser, LightweightUser
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        
        # Test GET request (should be allowed)
        request = factory.get('/', HTTP_AUTHORIZATION='token test-token')
        request.user = LightweightUser(id=1, username='testuser')
        
        resource = Resource(
            app_id='test-app',
            workspace_id='test-workspace',
            name='test-resource'
        )
        
        perm = IsAppUser()
        result = perm.has_object_permission(request, None, resource)
        self.assertTrue(result)
        
        # Test POST request (should be denied)
        request = factory.post('/', HTTP_AUTHORIZATION='token test-token')
        request.user = LightweightUser(id=1, username='testuser')
        
        result = perm.has_object_permission(request, None, resource)
        self.assertFalse(result)
