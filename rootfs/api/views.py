"""
RESTful view classes for presenting Drycc Resources API objects.
"""
import logging
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from api import models, serializers
from api.exceptions import DryccException
from api.clients.controller import ControllerClient

logger = logging.getLogger(__name__)


class BaseResourceViewSet(GenericViewSet):
    """Base viewset for resource-related views."""
    model = models.Resource
    serializer_class = serializers.ResourceSerializer
    lookup_field = 'id'

    controller = ControllerClient()

    def _get_token(self, request):
        """Extract token from request."""
        from rest_framework.authentication import get_authorization_header
        auth_header = get_authorization_header(request).split()
        if len(auth_header) >= 2:
            return auth_header[1].decode()
        return None


class AppResourcesViewSet(BaseResourceViewSet):
    """RESTful views for resources."""

    def services(self, request, *args, **kwargs):
        def _load():
            results = self.model.services()
            return {'results': results, 'count': len(results)}

        data = cache.get_or_set(
            "resources:services",
            _load,
            timeout=settings.DRYCC_RESOURCES_CATALOG_CACHE_TTL,
        )
        return Response(data=data)

    def plans(self, request, *args, **kwargs):
        serviceclass_name = kwargs["id"]

        def _load():
            results = self.model.plans(serviceclass_name)
            return {'results': results, 'count': len(results)}

        data = cache.get_or_set(
            "resources:services:%s:plan" % serviceclass_name,
            _load,
            timeout=settings.DRYCC_RESOURCES_CATALOG_CACHE_TTL,
        )
        return Response(data=data)

    def list(self, request, *args, **kwargs):
        app_id = self.kwargs['id']
        queryset = self.model.objects.filter(app_id=app_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        app_id = self.kwargs['id']
        token = self._get_token(request)
        # Fetch workspace_id from controller
        cache_key = f"app:{app_id}"
        app_data = cache.get(cache_key)
        if not app_data:
            app_data = self.controller.get_app(token, app_id)
            cache.set(cache_key, app_data,
                      timeout=settings.DRYCC_CONTROLLER_AUTH_CACHE_TTL)

        workspace_id = app_data.get('workspace', '')
        # Build the resource data
        data = request.data.copy()
        data['app_id'] = app_id
        data['workspace_id'] = workspace_id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        resource = serializer.save(app_id=app_id, workspace_id=workspace_id)
        return Response(
            self.get_serializer(resource).data,
            status=status.HTTP_201_CREATED
        )


class AppSingleResourceViewSet(BaseResourceViewSet):
    """RESTful views for a single resource."""

    def get_object(self):
        return get_object_or_404(
            models.Resource,
            app_id=self.kwargs['id'],
            name=self.kwargs['name']
        )

    def retrieve(self, request, *args, **kwargs):
        resource = self.get_object()
        resource.retrieve(request)
        serializer = self.get_serializer(resource)
        data = serializer.data
        data["message"] = resource.message
        return Response(data)

    def destroy(self, request, *args, **kwargs):
        resource = self.get_object()
        resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        resource = self.get_object()
        serializer = serializers.ResourceSerializer(
            data=request.data,
            instance=resource,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
        return Response(serializer.data)


class AppResourceBindingViewSet(BaseResourceViewSet):
    """RESTful views for resource binding."""

    def get_object(self):
        return get_object_or_404(
            models.Resource,
            app_id=self.kwargs['id'],
            name=self.kwargs['name']
        )

    def binding(self, request, *args, **kwargs):
        resource = self.get_object()
        bind_action = self.request.data.get('bind_action', '').lower()
        if bind_action == 'bind':
            resource.bind()
            serializer = self.get_serializer(resource, many=False)
            logger.info("resource bind response data: {}".format(serializer))
            return Response(serializer.data)
        elif bind_action == 'unbind':
            resource.unbind()
            serializer = self.get_serializer(resource, many=False)
            logger.info("resource unbind response data: {}".format(serializer))
            return Response(serializer.data)
        else:
            return Response("unknown action",
                            status=status.HTTP_404_NOT_FOUND)
