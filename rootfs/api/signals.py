# -*- coding: utf-8 -*-

"""
Signal handlers for the Drycc Resources API.
"""
import logging
from django.db.models.signals import post_delete, post_save

from api.models.resource import Resource

logger = logging.getLogger(__name__)


def _log_instance_created(**kwargs):
    if kwargs.get('created'):
        instance = kwargs['instance']
        message = '{} {} created'.format(instance.__class__.__name__.lower(), instance)
        if hasattr(instance, 'log'):
            instance.log(message)
        else:
            logger.info(message)


def _log_instance_updated(**kwargs):
    instance = kwargs['instance']
    message = '{} {} updated'.format(instance.__class__.__name__.lower(), instance)
    if hasattr(instance, 'log'):
        instance.log(message)
    else:
        logger.info(message)


def _log_instance_removed(**kwargs):
    instance = kwargs['instance']
    message = '{} {} removed'.format(instance.__class__.__name__.lower(), instance)
    if hasattr(instance, 'log'):
        instance.log(message)
    else:
        logger.info(message)


post_save.connect(_log_instance_created, sender=Resource, dispatch_uid='api.models.log')
post_delete.connect(_log_instance_removed, sender=Resource, dispatch_uid='api.models.log')
