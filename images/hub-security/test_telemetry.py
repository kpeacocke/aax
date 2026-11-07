import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

settings.configure(OTEL_ENABLED=False, DOMAIN_ENABLED=False)
util = ModuleType("pulpcore.app.util")
util.get_domain = lambda: SimpleNamespace(name="test-domain")
util.get_worker_name = lambda: "test-worker"
sys.modules["pulpcore.app.util"] = util

from pulpcore.metrics import ArtifactsSizeCounter, init_otel_meter

reader = InMemoryMetricReader()
provider = MeterProvider(metric_readers=[reader])
meter = init_otel_meter("pulp-content", reader=reader, provider=provider)
with patch("pulpcore.metrics.init_otel_meter", return_value=meter):
    ArtifactsSizeCounter().add(42)
data = reader.get_metrics_data()
point = data.resource_metrics[0].scope_metrics[0].metrics[0].data.data_points[0]
assert point.value == 42
assert point.attributes == {"domain_name": "test-domain", "worker_process": "test-worker"}
provider.shutdown()
