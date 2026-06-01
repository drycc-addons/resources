from .. import KubeHTTPClient


class ResourceRegistry(type):
    """
    A registry of all Resources subclassed
    """
    def __init__(cls, name, bases, nmspc):
        super().__init__(name, bases, nmspc)
        if not hasattr(cls, 'registry'):
            cls.registry = set()

        cls.registry.add(cls)
        cls.registry -= set(bases)

    def __iter__(cls):
        return iter(cls.registry)


class Resource(KubeHTTPClient, metaclass=ResourceRegistry):
    api_version = 'v1'
    api_prefix = 'api'
    short_name = None

    def api(self, tmpl, *args):
        return "/{}/{}".format(self.api_prefix, self.api_version) + tmpl.format(*args)
