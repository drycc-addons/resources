"""
Classes to serialize the RESTful representation of Drycc Resources API models.
"""
import logging
from rest_framework import serializers
from api.models import Resource
from api.exceptions import DryccException

logger = logging.getLogger(__name__)


def validate_name(value):
    """Validate kubernetes-compatible name."""
    import re
    match = re.match(r'^[a-z0-9-]+$', value)
    if not match:
        raise serializers.ValidationError(
            "Can only contain a-z (lowercase), 0-9 and hyphens")
    return value


class JSONFieldSerializer(serializers.JSONField):
    """JSON field that handles binary data."""
    def to_internal_value(self, data):
        if isinstance(data, bytes):
            import json
            data = json.loads(data.decode('utf-8'))
        return super().to_internal_value(data)


class ResourceSerializer(serializers.ModelSerializer):
    """Serialize a :class:`~api.models.resource.Resource` model."""
    app_id = serializers.CharField(max_length=63, required=True)
    name = serializers.CharField(max_length=63, required=True)
    plan = serializers.CharField(max_length=128, required=True)
    data = JSONFieldSerializer(required=False)
    options = JSONFieldSerializer(required=False)

    class Meta:
        """Metadata options for a :class:`ResourceSerializer`."""
        model = Resource
        fields = '__all__'
        read_only_fields = ('app_id', 'uuid', 'created', 'updated', 'workspace_id',
                            'status', 'binding')

    def update(self, instance, validated_data):
        if instance.plan.split(':')[0] != validated_data.get('plan', '').split(':')[0]:
            raise DryccException("the resource instance cann't changed")
        if instance.status == "Provisioning":
            raise DryccException("this resource instance is in progress")
        instance.plan = validated_data.get('plan')
        instance.options.update(validated_data.get('options', {}))
        instance.attach_update()
        instance.save()
        return instance

    validate_name = staticmethod(validate_name)
