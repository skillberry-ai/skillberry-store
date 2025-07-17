import logging
import os

from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry import trace
from prometheus_client import start_http_server

logging.getLogger("opentelemetry").setLevel(logging.ERROR)

PROMETHEUS_METRICS_PORT = int(os.getenv("PROMETHEUS_METRICS_PORT", 8090))
OTEL_TRACES_PORT = int(os.getenv("OTEL_TRACES_PORT", 0))
OTEL_SERVICE_NAME = "blueberry-tools-service"


def observability_setup():
    if OTEL_TRACES_PORT == 0:
        logging.info(
            "OpenTelemetry tracing is not configured. Set OTEL_TRACES_PORT to enable."
        )
    else:
        otel_setup()
    prometheus_setup()


def prometheus_setup():
    """Configures Prometheus metrics for a FastAPI app."""

    # Setup Metrics
    start_http_server(port=PROMETHEUS_METRICS_PORT)


def otel_setup():
    """Configures OpenTelemetry tracing for a FastAPI app."""

    trace_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME})
    )
    trace_exporter = OTLPSpanExporter(
        endpoint=f"http://localhost:{OTEL_TRACES_PORT}", insecure=True
    )
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

    trace.set_tracer_provider(trace_provider)

    RequestsInstrumentor().instrument()
