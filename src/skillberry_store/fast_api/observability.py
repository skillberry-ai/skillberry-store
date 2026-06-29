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

OTEL_SERVICE_NAME = "skillberry-store"


def observability_setup():
    otel_traces_port = int(os.getenv("OTEL_TRACES_PORT", 0))
    if otel_traces_port == 0:
        logging.info(
            "OpenTelemetry tracing is not configured. Set OTEL_TRACES_PORT to enable."
        )
    else:
        otel_setup(otel_traces_port)
    prometheus_setup()


def prometheus_setup():
    """Configures Prometheus metrics for a FastAPI app."""

    port = int(os.getenv("PROMETHEUS_METRICS_PORT", 8090))

    # Skip Prometheus if port is 0 (disabled)
    if port == 0:
        logging.info("Prometheus metrics disabled (PROMETHEUS_METRICS_PORT=0)")
        return

    # Setup Metrics
    start_http_server(port=port)
    logging.info(f"Prometheus metrics server started on port {port}")


def otel_setup(otel_traces_port: int):
    """Configures OpenTelemetry tracing for a FastAPI app."""

    trace_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME})
    )
    trace_exporter = OTLPSpanExporter(
        endpoint=f"http://localhost:{otel_traces_port}", insecure=True
    )
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

    trace.set_tracer_provider(trace_provider)

    RequestsInstrumentor().instrument()
