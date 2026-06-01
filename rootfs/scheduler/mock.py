"""
Mock scheduler module for testing.

Provides a SchedulerClient that simulates K8s service catalog operations
without requiring a real Kubernetes cluster.
"""


class MockResponse:
    """Mock HTTP response object."""
    def __init__(self, status_code=200, json_data=None, reason='OK'):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.reason = reason

    def json(self):
        return self._json_data


class MockSvcat:
    """Mock service catalog client."""

    def get_serviceclasses(self, namespace=None):
        return MockResponse(200, {
            "items": [
                {
                    "spec": {
                        "externalID": "postgresql-id",
                        "externalName": "postgresql",
                        "planUpdatable": True,
                    }
                },
                {
                    "spec": {
                        "externalID": "redis-id",
                        "externalName": "redis",
                        "planUpdatable": True,
                    }
                },
            ]
        })

    def get_serviceplans(self, namespace=None):
        return MockResponse(200, {
            "items": [
                {
                    "spec": {
                        "externalID": "postgresql-default-id",
                        "externalName": "default",
                        "description": "Default PostgreSQL plan",
                        "clusterServiceClassRef": {"name": "postgresql-id"},
                    }
                },
                {
                    "spec": {
                        "externalID": "redis-default-id",
                        "externalName": "default",
                        "description": "Default Redis plan",
                        "clusterServiceClassRef": {"name": "redis-id"},
                    }
                },
            ]
        })

    def get_instance(self, namespace, name=None, ignore_exception=False):
        from scheduler.exceptions import KubeHTTPException
        response = MockResponse(404, {"message": "not found"}, "Not Found")
        if not ignore_exception:
            raise KubeHTTPException(response, "get serviceinstances")
        return response

    def create_instance(self, namespace, name, **kwargs):
        return MockResponse(201, {
            "metadata": {"name": name, "namespace": namespace},
            "spec": kwargs,
        })

    def patch_instance(self, namespace, name, version, ignore_exception=False, **kwargs):
        return MockResponse(200, {
            "metadata": {"name": name, "namespace": namespace, "resourceVersion": version},
        })

    def delete_instance(self, namespace, name):
        return MockResponse(200, {})

    def get_binding(self, namespace, name=None):
        return MockResponse(404, {"message": "not found"})

    def create_binding(self, namespace, name, **kwargs):
        return MockResponse(201, {
            "metadata": {"name": name, "namespace": namespace},
        })

    def delete_binding(self, namespace, name):
        return MockResponse(200, {})


class SchedulerClient:
    """Mock scheduler client for testing."""

    def __init__(self, url, k8s_api_verify_tls=True, metadata=None):
        self.url = url
        self.k8s_api_verify_tls = k8s_api_verify_tls
        self.metadata = metadata or {}
        self.svcat = MockSvcat()
