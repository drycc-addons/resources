from scheduler.resources.__resource import Resource  # noqa

# Only load svcat resource for the resources service
from scheduler.resources import svcat  # noqa
from scheduler.resources import secret  # noqa
