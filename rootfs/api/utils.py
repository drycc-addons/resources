"""
Helper functions used by the Drycc Resources server.
"""
import os
import re
import logging
import hashlib
import requests
from copy import deepcopy
from urllib.parse import urljoin
from django.conf import settings
from django.utils import timezone
from requests_toolbelt import user_agent
from api import __version__ as drycc_version
from rest_framework.exceptions import ValidationError


logger = logging.getLogger(__name__)


def get_httpclient():
    session = requests.Session()
    session.headers = {
        'User-Agent': user_agent('Drycc Resources', drycc_version),
    }
    session.mount('http://', requests.adapters.HTTPAdapter(max_retries=10))
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=10))
    return session


def get_scheduler(metadata=None):
    import importlib
    mod = importlib.import_module(settings.SCHEDULER_MODULE)
    metadata = metadata if metadata is not None else {}
    metadata = dict_merge(metadata, {"annotations": {"app.kubernetes.io/managed-by": "drycc"}})
    return mod.SchedulerClient(settings.SCHEDULER_URL, settings.K8S_API_VERIFY_TLS, metadata)


def validate_label(value):
    """
    Check that the value follows the kubernetes name constraints
    http://kubernetes.io/v1.1/docs/design/identifiers.html
    """
    match = re.match(r'^[a-z0-9-]+$', value)
    if not match:
        raise ValidationError("Can only contain a-z (lowercase), 0-9 and hyphens")
    validate_reserved_names(value)


def validate_reserved_names(value):
    """A value cannot use some reserved names."""
    for reserved_name_pattern in settings.RESERVED_NAME_PATTERNS:
        if re.match(reserved_name_pattern, value):
            raise ValidationError('{} is a reserved name.'.format(value))


def send_app_log(app_id, msg, level=logging.INFO):
    if not settings.QUICKWIT_INDEXER_URL:
        return
    pod_ip = os.environ.get("POD_IP", "unknown")
    pod_name = os.environ.get("POD_NAME", "unknown")
    namespace = os.environ.get("NAMESPACE", "unknown")
    docker_id = hashlib.sha256(f"{namespace}:{pod_name}:{pod_ip}".encode("utf-8")).hexdigest()
    data = {
        "kubernetes": {
            "container_name": "drycc-resources",
            "docker_id": docker_id,
            "namespace_name": app_id,
            "pod_name": pod_name,
        },
        "log": f"{logging.getLevelName(level)}\t{app_id}\t{msg}",
        "offset": int(timezone.now().timestamp()),
        "stream": "stdout",
        "timestamp": timezone.now().isoformat(),
    }
    index = f"{settings.QUICKWIT_LOG_INDEX_PREFIX}{app_id}"
    with get_httpclient() as session:
        session.post(urljoin(settings.QUICKWIT_INDEXER_URL, f"/api/v1/{index}/ingest"), json=data)


def dict_merge(origin, merge):
    """
    Recursively merges dict's.
    """
    if not isinstance(merge, dict):
        return merge

    result = deepcopy(origin)
    for key, value in merge.items():
        if key in result and isinstance(result[key], dict):
            result[key] = dict_merge(result[key], value)
        else:
            if isinstance(value, list):
                if key not in result:
                    result[key] = value
                else:
                    for item in value:
                        if item in result[key]:
                            continue
                        result[key].append(item)
            else:
                result[key] = deepcopy(value)
    return result
