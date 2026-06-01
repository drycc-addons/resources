"""
HTTP middleware for the Drycc Resources API.
"""

from api import __version__


class DjangoAPIVersionMiddleware(object):
    """
    Include the REST API version with each response.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """
        Include the resources REST API major and minor version in
        a response header.
        """
        response = self.get_response(request)
        # clients shouldn't care about the patch release
        version = __version__.rsplit('.', 1)[0]
        response['DRYCC_API_VERSION'] = version
        response['DRYCC_PLATFORM_VERSION'] = __version__
        return response
