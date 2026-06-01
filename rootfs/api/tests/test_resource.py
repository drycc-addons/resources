"""
Tests for the Resource model and views.
"""
from unittest.mock import MagicMock, Mock, patch
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
        # Create a mock controller to replace both instances
        self.mock_controller = MagicMock()
        self.mock_controller.whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }
        self.mock_controller.get_app.return_value = {
            'id': 'test-app',
            'workspace': 'test-workspace'
        }
        self.mock_controller.get_workspace.return_value = {
            'id': 'test-workspace',
            'role': 'member'
        }
        # Patch the class-level controller attributes
        from api.passthrough import (
            ControllerPassthroughAuthentication,
            IsAppUser,
        )
        from api.views import BaseResourceViewSet
        self.auth_ctrl_patcher = patch.object(
            ControllerPassthroughAuthentication, 'controller',
            self.mock_controller)
        self.isapp_ctrl_patcher = patch.object(
            IsAppUser, 'controller', self.mock_controller)
        self.view_ctrl_patcher = patch.object(
            BaseResourceViewSet, 'controller', self.mock_controller)
        self.auth_ctrl_patcher.start()
        self.isapp_ctrl_patcher.start()
        self.view_ctrl_patcher.start()

    def _setup_common_mocks(self, role='member'):
        """Configure common mock return values."""
        user_data = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }
        self.mock_controller.whoami.return_value = user_data
        self.mock_controller.get_app.return_value = {
            'id': 'test-app',
            'workspace': 'test-workspace'
        }
        self.mock_controller.get_workspace.return_value = {
            'id': 'test-workspace',
            'role': role
        }

    def tearDown(self):
        self.auth_ctrl_patcher.stop()
        self.isapp_ctrl_patcher.stop()
        self.view_ctrl_patcher.stop()

    def test_list_resources(self):
        """Test listing resources for an app."""
        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.get('/apps/test-app/resources/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'test-resource')

    def test_retrieve_resource(self):
        """Test retrieving a single resource."""
        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.get('/apps/test-app/resources/test-resource/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test-resource')

    @patch('api.models.resource.Resource.attach')
    def test_create_resource(self, mock_attach):
        """Test creating a new resource."""
        mock_attach.return_value = None

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        data = {
            'name': 'new-resource',
            'plan': 'postgresql:default',
            'options': {'size': 'small'}
        }
        response = self.client.post(
            '/apps/test-app/resources/', data, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'new-resource')
        self.assertEqual(response.data['workspace_id'], 'test-workspace')

    @patch('api.models.resource.Resource.delete')
    def test_delete_resource(self, mock_delete):
        """Test deleting a resource."""
        self._setup_common_mocks(role='admin')
        mock_delete.return_value = None

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.delete(
            '/apps/test-app/resources/test-resource/'
        )

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


class ResourceSerializerTest(TestCase):
    """Test the ResourceSerializer."""

    def setUp(self):
        self.resource = Resource.objects.create(
            app_id='test-app',
            workspace_id='test-workspace',
            name='test-resource',
            plan='postgresql:default',
            options={'size': 'small'}
        )

    def test_serializer_fields(self):
        """Test that serializer includes expected fields."""
        from api.serializers import ResourceSerializer
        serializer = ResourceSerializer(self.resource)
        data = serializer.data
        self.assertIn('app_id', data)
        self.assertIn('workspace_id', data)
        self.assertIn('name', data)
        self.assertIn('plan', data)
        self.assertIn('status', data)
        self.assertIn('binding', data)
        self.assertIn('options', data)
        self.assertIn('data', data)
        self.assertIn('uuid', data)
        self.assertIn('created', data)
        self.assertIn('updated', data)

    def test_serializer_read_only_fields(self):
        """Test that read-only fields are in Meta."""
        from api.serializers import ResourceSerializer
        serializer = ResourceSerializer(Resource())
        # Check that read_only_fields are defined in Meta
        self.assertIn('app_id', serializer.Meta.read_only_fields)
        self.assertIn('workspace_id', serializer.Meta.read_only_fields)
        self.assertIn('uuid', serializer.Meta.read_only_fields)

    def test_validate_name_invalid(self):
        """Test that invalid names are rejected."""
        from api.serializers import validate_name
        from rest_framework import serializers as drf_serializers
        with self.assertRaises(drf_serializers.ValidationError):
            validate_name('Invalid_Name')

    def test_validate_name_valid(self):
        """Test that valid names are accepted."""
        from api.serializers import validate_name
        result = validate_name('valid-name-123')
        self.assertEqual(result, 'valid-name-123')

    @patch('api.models.resource.Resource.attach_update')
    def test_serializer_update(self, mock_attach_update):
        """Test updating a resource through serializer."""
        from api.serializers import ResourceSerializer
        data = {'plan': 'postgresql:default', 'options': {'size': 'large'}}
        serializer = ResourceSerializer(
            instance=self.resource, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())
        instance = serializer.save()
        self.assertEqual(instance.plan, 'postgresql:default')
        mock_attach_update.assert_called_once()

    @patch('api.models.resource.Resource.attach_update')
    def test_serializer_update_different_class(self, mock_attach_update):
        """Test that updating to different service class is rejected."""
        from api.serializers import ResourceSerializer
        from api.exceptions import DryccException
        data = {'plan': 'mysql:default'}
        serializer = ResourceSerializer(
            instance=self.resource, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())
        with self.assertRaises(DryccException):
            serializer.save()

    @patch('api.models.resource.Resource.attach_update')
    def test_serializer_update_while_provisioning(self, mock_attach_update):
        """Test that updating while provisioning is rejected."""
        from api.serializers import ResourceSerializer
        from api.exceptions import DryccException
        self.resource.status = 'Provisioning'
        self.resource.save()
        data = {'plan': 'postgresql:default', 'options': {'size': 'large'}}
        serializer = ResourceSerializer(
            instance=self.resource, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())
        with self.assertRaises(DryccException):
            serializer.save()


class ResourceBindingAPITest(APITestCase):
    """Test the Resource Binding API endpoints."""

    def setUp(self):
        self.resource = Resource.objects.create(
            app_id='test-app',
            workspace_id='test-workspace',
            name='test-resource',
            plan='postgresql:default',
            status='Ready',
            binding=None
        )
        # Create a mock controller
        self.mock_controller = MagicMock()
        self.mock_controller.whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }
        self.mock_controller.get_app.return_value = {
            'id': 'test-app',
            'workspace': 'test-workspace'
        }
        self.mock_controller.get_workspace.return_value = {
            'id': 'test-workspace',
            'role': 'member'
        }
        from api.passthrough import (
            ControllerPassthroughAuthentication,
            IsAppUser,
        )
        from api.views import BaseResourceViewSet
        self.auth_ctrl_patcher = patch.object(
            ControllerPassthroughAuthentication, 'controller',
            self.mock_controller)
        self.isapp_ctrl_patcher = patch.object(
            IsAppUser, 'controller', self.mock_controller)
        self.view_ctrl_patcher = patch.object(
            BaseResourceViewSet, 'controller', self.mock_controller)
        self.auth_ctrl_patcher.start()
        self.isapp_ctrl_patcher.start()
        self.view_ctrl_patcher.start()

    def tearDown(self):
        self.auth_ctrl_patcher.stop()
        self.isapp_ctrl_patcher.stop()
        self.view_ctrl_patcher.stop()

    @patch('api.models.resource.Resource.bind')
    def test_bind_resource(self, mock_bind):
        """Test binding a resource."""
        mock_bind.return_value = None

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        data = {'bind_action': 'bind'}
        response = self.client.patch(
            '/apps/test-app/resources/test-resource/binding/',
            data, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_bind.assert_called_once()

    @patch('api.models.resource.Resource.unbind')
    def test_unbind_resource(self, mock_unbind):
        """Test unbinding a resource."""
        mock_unbind.return_value = None
        self.resource.binding = 'Ready'
        self.resource.save()

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        data = {'bind_action': 'unbind'}
        response = self.client.patch(
            '/apps/test-app/resources/test-resource/binding/',
            data, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_unbind.assert_called_once()

    def test_invalid_bind_action(self):
        """Test that invalid bind actions return 404."""
        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        data = {'bind_action': 'invalid'}
        response = self.client.patch(
            '/apps/test-app/resources/test-resource/binding/',
            data, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ResourceServicesAPITest(APITestCase):
    """Test the Resource Services API endpoints."""

    def setUp(self):
        self.mock_controller = MagicMock()
        self.mock_controller.whoami.return_value = {
            'id': 1,
            'username': 'testuser',
            'is_superuser': False
        }
        self.mock_controller.get_app.return_value = {
            'id': 'test-app',
            'workspace': 'test-workspace'
        }
        self.mock_controller.get_workspace.return_value = {
            'id': 'test-workspace',
            'role': 'member'
        }
        from api.passthrough import ControllerPassthroughAuthentication, IsAppUser
        from api.views import BaseResourceViewSet
        self.auth_ctrl_patcher = patch.object(
            ControllerPassthroughAuthentication, 'controller',
            self.mock_controller)
        self.isapp_ctrl_patcher = patch.object(
            IsAppUser, 'controller', self.mock_controller)
        self.view_ctrl_patcher = patch.object(
            BaseResourceViewSet, 'controller', self.mock_controller)
        self.auth_ctrl_patcher.start()
        self.isapp_ctrl_patcher.start()
        self.view_ctrl_patcher.start()

    def tearDown(self):
        self.auth_ctrl_patcher.stop()
        self.isapp_ctrl_patcher.stop()
        self.view_ctrl_patcher.stop()

    @patch('api.models.resource.Resource.services')
    def test_list_services(self, mock_services):
        """Test listing available services."""
        mock_services.return_value = [
            {'id': 'svc-1', 'name': 'postgresql', 'updateable': True}
        ]

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.get('/resources/services/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('api.models.resource.Resource.plans')
    def test_list_plans(self, mock_plans):
        """Test listing plans for a service."""
        mock_plans.return_value = [
            {'id': 'plan-1', 'name': 'default', 'description': 'Default plan'}
        ]

        self.client.credentials(HTTP_AUTHORIZATION='token test-token')
        response = self.client.get('/resources/services/postgresql/plans/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResourceModelMethodTest(TestCase):
    """Test Resource model methods."""

    def setUp(self):
        self.resource = Resource.objects.create(
            app_id='test-app',
            workspace_id='test-workspace',
            name='test-resource',
            plan='postgresql:default',
            status='Ready',
            binding=None
        )

    @patch('api.models.resource.get_scheduler')
    def test_resource_plans(self, mock_get_scheduler):
        """Test listing plans for a service class."""
        mock_scheduler = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            'items': [
                {
                    'spec': {
                        'externalID': 'plan-1',
                        'externalName': 'default',
                        'description': 'Default plan',
                        'clusterServiceClassRef': {'name': 'svc-1'}
                    }
                }
            ]
        }
        mock_scheduler.svcat.get_serviceplans.return_value = mock_response
        mock_get_scheduler.return_value = mock_scheduler

        # Mock services to return the service class
        with patch.object(Resource, 'services', return_value=[
            {'id': 'svc-1', 'name': 'postgresql', 'updateable': True}
        ]):
            plans = Resource.plans('postgresql')
            self.assertEqual(len(plans), 1)
            self.assertEqual(plans[0]['name'], 'default')

    @patch('api.models.resource.get_scheduler')
    def test_resource_delete_while_binding(self, mock_get_scheduler):
        """Test that deleting a binding resource raises exception."""
        from api.exceptions import DryccException
        self.resource.binding = 'Ready'
        self.resource.save()

        with self.assertRaises(DryccException):
            self.resource.delete()

    @patch('api.models.resource.get_scheduler')
    def test_resource_delete_while_provisioning(self, mock_get_scheduler):
        """Test that deleting a provisioning resource raises exception."""
        from api.exceptions import DryccException
        self.resource.status = 'Provisioning'
        self.resource.save()

        with self.assertRaises(DryccException):
            self.resource.delete()

    @patch('api.models.resource.get_scheduler')
    def test_resource_bind_not_ready(self, mock_get_scheduler):
        """Test that binding a non-ready resource raises exception."""
        from api.exceptions import DryccException
        self.resource.status = 'Provisioning'
        self.resource.save()

        with self.assertRaises(DryccException):
            self.resource.bind()

    @patch('api.models.resource.get_scheduler')
    def test_resource_bind_already_binding(self, mock_get_scheduler):
        """Test that binding an already binding resource raises exception."""
        from api.exceptions import DryccException
        self.resource.binding = 'Ready'
        self.resource.save()

        with self.assertRaises(DryccException):
            self.resource.bind()

    @patch('api.models.resource.get_scheduler')
    def test_resource_unbind_not_binding(self, mock_get_scheduler):
        """Test that unbinding a non-binding resource raises exception."""
        from api.exceptions import DryccException
        self.resource.binding = None
        self.resource.save()

        with self.assertRaises(DryccException):
            self.resource.unbind()

    def test_resource_to_usage(self):
        """Test the to_usage method."""
        import time
        timestamp = time.time()
        usage = self.resource.to_usage(timestamp)
        self.assertEqual(len(usage), 1)
        self.assertEqual(usage[0]['app_id'], 'test-app')
        self.assertEqual(usage[0]['workspace'], 'test-workspace')
        self.assertEqual(usage[0]['type'], 'resource')
        self.assertEqual(usage[0]['usage'], 1)
        self.assertEqual(usage[0]['kwargs']['name'], 'test-resource')
