import base64
import json
from scheduler.resources import Resource
from scheduler.exceptions import KubeHTTPException


class Secret(Resource):
    def get(self, namespace, name=None, **kwargs):
        """
        Fetch a single Secret or a list
        """
        url = '/namespaces/{}/secrets'
        args = [namespace]
        if name is not None:
            args.append(name)
            url += '/{}'
            message = 'get Secret "{}" in Namespace "{}"'
        else:
            message = 'get Secrets in Namespace "{}"'

        url = self.api(url, *args)
        response = self.http_get(url, params=self.query_params(**kwargs))
        if self.unhealthy(response.status_code):
            args.reverse()  # error msg is in reverse order
            raise KubeHTTPException(response, message, *args)

        # return right away if it is a list
        if name is None:
            return response

        # decode the base64 data
        secrets = response.json()
        for key, value in secrets.get('data', {}).items():
            if value is None:
                secrets['data'][key] = ''
                continue

            value = base64.b64decode(value)
            value = value if isinstance(value, bytes) else bytes(str(value), 'UTF-8')
            secrets['data'][key] = value.decode(encoding='UTF-8')

        # tell python-requests it actually hasn't consumed the data
        response._content = bytes(json.dumps(secrets), 'UTF-8')

        return response
