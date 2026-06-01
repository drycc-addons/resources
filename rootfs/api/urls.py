"""
URL routing patterns for the Drycc Resources API.
"""
from django.conf import settings
from django.urls import re_path
from api import views


# URLs that end with slashes are ugly
app_urlpatterns = [
    # health checks
    re_path(r"^healthz/?$", views.LivenessCheckView.as_view()),
    re_path(r"^readiness/?$", views.ReadinessCheckView.as_view()),
    # resources services
    re_path(r"^resources/services/?$", views.AppResourcesViewSet.as_view({'get': 'services'})),
    re_path(
        r"^resources/services/(?P<id>[-_ \.\d\w]+)/plans/?$",
        views.AppResourcesViewSet.as_view({'get': 'plans'})),
    # application resources
    re_path(
        r"^apps/(?P<id>{})/resources/?$".format(settings.APP_URL_REGEX),
        views.AppResourcesViewSet.as_view({'get': 'list', 'post': 'create'})),
    re_path(
        r"^apps/(?P<id>{})/resources/(?P<name>{})/?$".format(
            settings.APP_URL_REGEX, settings.NAME_REGEX),
        views.AppSingleResourceViewSet.as_view(
            {'get': 'retrieve', 'delete': 'destroy', 'put': 'update'})),
    re_path(
        r"^apps/(?P<id>{})/resources/(?P<name>{})/binding/?$".format(
            settings.APP_URL_REGEX, settings.NAME_REGEX),
        views.AppResourceBindingViewSet.as_view({'patch': 'binding'})),
]

urlpatterns = app_urlpatterns
