#!/usr/bin/env python
#
# Cart Service - Python Implementation
# Provides shopping cart management functionality

import os
import sys
import time
import traceback
from concurrent import futures

import grpc
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

import demo_pb2
import demo_pb2_grpc

from opentelemetry import trace
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

import googlecloudprofiler

from logger import getJSONLogger
from cart_store import create_cart_store, CartStore

logger = getJSONLogger('cartservice-server')


class CartService(demo_pb2_grpc.CartServiceServicer):
    """Implementation of the CartService gRPC service."""

    def __init__(self, cart_store: CartStore):
        self._store = cart_store

    def AddItem(self, request, context):
        """Add an item to the user's cart."""
        try:
            self._store.add_item(
                user_id=request.user_id,
                product_id=request.item.product_id,
                quantity=request.item.quantity
            )
            return demo_pb2.Empty()
        except Exception as e:
            logger.error(f"AddItem failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to add item to cart: {e}")
            return demo_pb2.Empty()

    def GetCart(self, request, context):
        """Get the user's cart."""
        try:
            return self._store.get_cart(request.user_id)
        except Exception as e:
            logger.error(f"GetCart failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get cart: {e}")
            return demo_pb2.Cart()

    def EmptyCart(self, request, context):
        """Empty the user's cart."""
        try:
            self._store.empty_cart(request.user_id)
            return demo_pb2.Empty()
        except Exception as e:
            logger.error(f"EmptyCart failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to empty cart: {e}")
            return demo_pb2.Empty()


class HealthServicer(health_pb2_grpc.HealthServicer):
    """Implementation of the gRPC Health service."""

    def __init__(self, cart_store: CartStore):
        self._store = cart_store

    def Check(self, request, context):
        if self._store.ping():
            return health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.SERVING
            )
        else:
            return health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.NOT_SERVING
            )

    def Watch(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.UNIMPLEMENTED
        )


def init_profiling():
    """Initialize Google Cloud Profiler."""
    project_id = os.environ.get("GCP_PROJECT_ID")

    for retry in range(1, 4):
        try:
            if project_id:
                googlecloudprofiler.start(
                    service='cart_server',
                    service_version='1.0.0',
                    verbose=0,
                    project_id=project_id
                )
            else:
                googlecloudprofiler.start(
                    service='cart_server',
                    service_version='1.0.0',
                    verbose=0
                )
            logger.info("Successfully started Stackdriver Profiler.")
            return
        except Exception as exc:
            logger.info(f"Unable to start Stackdriver Profiler: {exc}")
            if retry < 4:
                logger.info(f"Sleeping {retry * 10}s to retry initializing Stackdriver Profiler")
                time.sleep(retry * 10)
            else:
                logger.warning("Could not initialize Stackdriver Profiler after retrying, giving up")


def init_tracing():
    """Initialize OpenTelemetry tracing."""
    try:
        if os.environ.get("ENABLE_TRACING") == "1":
            otel_endpoint = os.getenv("COLLECTOR_SERVICE_ADDR", "localhost:4317")
            trace.set_tracer_provider(TracerProvider())
            trace.get_tracer_provider().add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=otel_endpoint,
                        insecure=True
                    )
                )
            )
            logger.info("Tracing enabled.")

        grpc_server_instrumentor = GrpcInstrumentorServer()
        grpc_server_instrumentor.instrument()
    except Exception as e:
        logger.warning(f"Exception on tracing setup: {traceback.format_exc()}, tracing disabled.")


def serve():
    """Start the gRPC server."""
    # Create cart store
    cart_store = create_cart_store()

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add services
    demo_pb2_grpc.add_CartServiceServicer_to_server(CartService(cart_store), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(cart_store), server)

    port = os.environ.get('PORT', '7070')
    server.add_insecure_port(f'[::]:{port}')
    server.start()

    logger.info(f"Cart Service started, listening on port {port}")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down Cart Service")
        server.stop(0)


if __name__ == '__main__':
    logger.info("CartService starting.")

    # # Initialize profiling
    # if os.environ.get("DISABLE_PROFILER"):
    #     logger.info("Profiler disabled.")
    # else:
    #     logger.info("Profiler enabled.")
    #     init_profiling()

    # # Initialize tracing
    # if os.environ.get("DISABLE_TRACING"):
    #     logger.info("Tracing disabled.")
    # else:
    #     init_tracing()

    serve()
