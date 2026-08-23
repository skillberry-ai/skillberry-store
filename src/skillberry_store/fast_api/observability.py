import logging
import os

from prometheus_client import start_http_server

# Configuring the logger by name does not import the opentelemetry package --
# the OTel imports themselves live inside ``otel_setup`` (see the note there).
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

    # Imported here rather than at module scope: none of this is reachable
    # unless OTEL_TRACES_PORT is set, and ``observability_setup`` -- the only
    # caller -- already guards on that. Together with the FastAPIInstrumentor
    # import in server.py this keeps ~20 MiB of RSS out of an untraced
    # deployment (measured in-container; the isolated import cost is ~50 MiB,
    # but much of OTel's transitive stack is already resident for other
    # reasons). The OTLP gRPC exporter is the single largest piece.
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    trace_provider = TracerProvider(
        resource=Resource.create({SERVICE_NAME: OTEL_SERVICE_NAME})
    )
    trace_exporter = OTLPSpanExporter(
        endpoint=f"http://localhost:{otel_traces_port}", insecure=True
    )
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))

    trace.set_tracer_provider(trace_provider)

    RequestsInstrumentor().instrument()
