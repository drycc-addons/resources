from collections import OrderedDict
from datetime import datetime, timezone
import logging
import requests
import requests.exceptions
import urllib3
from requests_toolbelt import user_agent
from urllib.parse import urljoin

from api import utils, __version__ as drycc_version
from scheduler.exceptions import KubeException


logger = logging.getLogger(__name__)
session = None


def get_k8s_session(k8s_api_verify_tls):
    global session
    if session is None:
        with open('/var/run/secrets/kubernetes.io/serviceaccount/token') as token_file:
            token = token_file.read().strip("\r\n\t")
        session = requests.Session()
        session.headers = {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            'User-Agent': user_agent('Drycc Resources', drycc_version)
        }
        if k8s_api_verify_tls:
            session.verify = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
        else:
            session.verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return session


class KubeHTTPClient(object):
    api_version = 'v1'
    api_prefix = 'api'
    DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
    resource_mapping = OrderedDict()

    def __init__(self, url, k8s_api_verify_tls=True, metadata=None):
        self.url = url
        self.k8s_api_verify_tls = k8s_api_verify_tls
        self.session = get_k8s_session(self.k8s_api_verify_tls)
        self.metadata = {} if metadata is None else metadata

        # map the various k8s Resources to an internal property
        from scheduler.resources import Resource  # lazy load
        if not isinstance(self, Resource):
            KubeHTTPClient.resource_mapping = OrderedDict()
        for res in Resource:
            name = str(res.__name__).lower()
            component = name + 's'
            if component in self.resource_mapping:
                continue
            self.resource_mapping[component] = ''
            self.resource_mapping[component] = res(
                self.url, self.k8s_api_verify_tls, metadata=self.metadata)
            self.resource_mapping[name] = component
            if res.short_name is not None:
                self.resource_mapping[str(res.short_name).lower()] = component

    def api(self, tmpl, *args):
        return "/{}/{}".format(self.api_prefix, self.api_version) + tmpl.format(*args)

    def __getattr__(self, name):
        if name in self.resource_mapping:
            component = self.resource_mapping[name]
            if type(component) is not str:
                return component
            return self.resource_mapping[component]
        return object.__getattribute__(self, name)

    @staticmethod
    def parse_date(date):
        return datetime.strptime(date, KubeHTTPClient.DATETIME_FORMAT).replace(tzinfo=timezone.utc)

    @staticmethod
    def unhealthy(status_code):
        return not 200 <= status_code <= 299

    @staticmethod
    def query_params(labels=None, fields=None, resource_version=None, pretty=False):
        query = {}
        if labels:
            selectors = []
            for key, value in labels.items():
                if '__notin' in key:
                    key = key.replace('__notin', '')
                    selectors.append('{} notin({})'.format(key, ','.join(value)))
                elif '__in' in key or isinstance(value, list):
                    key = key.replace('__in', '')
                    selectors.append('{} in({})'.format(key, ','.join(value)))
                elif value is None:
                    selectors.append(key)
                elif isinstance(value, str):
                    selectors.append('{}={}'.format(key, value))
            query['labelSelector'] = ','.join(selectors)
        if fields:
            fields = ['{}={}'.format(key, value) for key, value in fields.items()]
            query['fieldSelector'] = ','.join(fields)
        if resource_version:
            query['resourceVersion'] = resource_version
        if pretty:
            query['pretty'] = pretty
        return query

    @staticmethod
    def log(namespace, message, level=logging.INFO):
        utils.send_app_log(namespace, message, level)
        logger.log(level, "[{}]: {}".format(namespace, message))

    def http_get(self, path, params=None, **kwargs):
        try:
            url = urljoin(self.url, path)
            response = self.session.get(url, params=params, **kwargs)
        except requests.exceptions.ConnectionError as err:
            message = "There was a problem retrieving data from " \
                      "the Kubernetes API server. URL: {}, params: {}".format(url, params)
            logger.error(message)
            raise KubeException(message) from err
        return response

    def http_post(self, path, json=None, **kwargs):
        try:
            url = urljoin(self.url, path)
            if json is not None and "metadata" in json:
                json["metadata"] = utils.dict_merge(json["metadata"], self.metadata)
            response = self.session.post(url, json=json, **kwargs)
        except requests.exceptions.ConnectionError as err:
            message = "There was a problem posting data to " \
                      "the Kubernetes API server. URL: {}, json: {}".format(url, json)
            logger.error(message)
            raise KubeException(message) from err
        return response

    def http_put(self, path, json=None, **kwargs):
        try:
            url = urljoin(self.url, path)
            if json is not None and "metadata" in json:
                json["metadata"] = utils.dict_merge(json["metadata"], self.metadata)
            response = self.session.put(url, json=json, **kwargs)
        except requests.exceptions.ConnectionError as err:
            message = "There was a problem putting data to " \
                      "the Kubernetes API server. URL: {}, json: {}".format(url, json)
            logger.error(message)
            raise KubeException(message) from err
        return response

    def http_patch(self, path, json=None, **kwargs):
        try:
            url = urljoin(self.url, path)
            if json is not None and "metadata" in json:
                json["metadata"] = utils.dict_merge(json["metadata"], self.metadata)
            response = self.session.patch(url, json=json, **kwargs)
        except requests.exceptions.ConnectionError as err:
            message = "There was a problem patching data to " \
                      "the Kubernetes API server. URL: {}, json: {}".format(url, json)
            logger.error(message)
            raise KubeException(message) from err
        return response

    def http_delete(self, path, **kwargs):
        try:
            url = urljoin(self.url, path)
            response = self.session.delete(url, **kwargs)
        except requests.exceptions.ConnectionError as err:
            message = "There was a problem deleting data from " \
                      "the Kubernetes API server. URL: {}".format(url)
            logger.error(message)
            raise KubeException(message) from err
        return response


class SchedulerClient(KubeHTTPClient):
    """Scheduler client for the resources service.

    Only loads svcat resources, not the full set of K8s resources.
    """
    pass
