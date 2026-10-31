"""Exercise AWX's real log handler without contacting a collector or database."""

import argparse
import logging

from django.conf import settings
from google.rpc.status_pb2 import Status
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.sdk._logs.export import LogExportResult

settings.configure(COLOR_LOGS=False)

from awx.main.utils import handlers  # noqa: E402


class RecordingExporter:
    instances = []

    def __init__(self, **kwargs):
        self.options = kwargs
        self.requests = []
        self.instances.append(self)

    def export(self, records):
        encoded = encode_logs(records).SerializeToString()
        self.requests.append(ExportLogsServiceRequest.FromString(encoded))
        return LogExportResult.SUCCESS

    def shutdown(self):
        pass


parser = argparse.ArgumentParser()
parser.add_argument("protocol", choices=("grpc", "http"))
args = parser.parse_args()
handlers.OTLPGrpcLogExporter = RecordingExporter
handlers.OTLPHttpLogExporter = RecordingExporter
handler = handlers.OTLPHandler(
    endpoint="http://127.0.0.1:4318", protocol=args.protocol,
    service_name="aax-telemetry-test", instance_id="isolated-test",
)
provider = handler._logger_provider
exporter = RecordingExporter.instances[-1]
record = logging.LogRecord("awx.analytics", logging.INFO, __file__, 0, "aax log %s", ("event",), None)
handler.emit(record)
assert provider.force_flush(timeout_millis=5000)
assert len(exporter.requests) == 1
resource = exporter.requests[0].resource_logs[0]
attributes = {item.key: item.value.string_value for item in resource.resource.attributes}
assert attributes["service.name"] == "aax-telemetry-test"
assert attributes["service.instance.id"] == "isolated-test"
entry = resource.scope_logs[0].log_records[0]
assert entry.body.string_value == "aax log event"
assert entry.severity_number == 9
provider.shutdown()
handler.close()

status = Status(code=0, message="aax-protobuf-roundtrip")
assert Status.FromString(status.SerializeToString()) == status
print("AAX_AWX_TELEMETRY_PASSED")
