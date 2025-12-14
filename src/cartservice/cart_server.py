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

# ============================================
# Datadog APM Setup
# ============================================
from ddtrace import tracer, patch_all, config
import logging

# Set service name before patching
config.service = "cartservice"
config.grpc["service_name"] = "cartservice"  # For gRPC client spans
config.grpc_server["service_name"] = "cartservice"  # For gRPC server spans

# Initialize Datadog tracing (auto-patches grpc, redis, etc.)
patch_all()

# Configure logging with Datadog trace correlation
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "service": "cartservice", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger('cartservice-server')

def emit_cart_metrics(operation: str, user_id: str, item_count: int = 0, redis_latency_ms: float = None):
    """Emit custom cart service metrics to Datadog"""
    span = tracer.current_span()
    if span:
        span.set_tag("cart.operation", operation)
        span.set_tag("cart.user_id", user_id)
        if operation == "add":
            span.set_tag("cart.item.add.count", 1)
        elif operation == "get":
            span.set_tag("cart.item.count", item_count)
        elif operation == "empty":
            span.set_tag("cart.item.remove.count", item_count)
        if redis_latency_ms is not None:
            span.set_tag("cart.redis.latency_ms", redis_latency_ms)

# ============================================

from cart_store import create_cart_store, CartStore


class CartService(demo_pb2_grpc.CartServiceServicer):
    """Implementation of the CartService gRPC service."""

    def __init__(self, cart_store: CartStore):
        self._store = cart_store

    def AddItem(self, request, context):
        """Add an item to the user's cart."""
        start_time = time.time()
        try:
            self._store.add_item(
                user_id=request.user_id,
                product_id=request.item.product_id,
                quantity=request.item.quantity
            )
            redis_latency = (time.time() - start_time) * 1000
            emit_cart_metrics("add", request.user_id, redis_latency_ms=redis_latency)
            return demo_pb2.Empty()
        except Exception as e:
            logger.error(f"AddItem failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to add item to cart: {e}")
            return demo_pb2.Empty()

    def GetCart(self, request, context):
        """Get the user's cart."""
        start_time = time.time()
        try:
            cart = self._store.get_cart(request.user_id)
            redis_latency = (time.time() - start_time) * 1000
            item_count = len(cart.items) if cart and cart.items else 0
            emit_cart_metrics("get", request.user_id, item_count=item_count, redis_latency_ms=redis_latency)
            return cart
        except Exception as e:
            logger.error(f"GetCart failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get cart: {e}")
            return demo_pb2.Cart()

    def EmptyCart(self, request, context):
        """Empty the user's cart."""
        start_time = time.time()
        try:
            self._store.empty_cart(request.user_id)
            redis_latency = (time.time() - start_time) * 1000
            emit_cart_metrics("empty", request.user_id, redis_latency_ms=redis_latency)
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
