import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings.production")
django.setup()

from api.models.resource import Resource
print("Before init")
r = Resource(app_id="test", workspace_id="test", name="test", plan="test:test")
print("adding:", r._state.adding)
