#!/usr/bin/env python
#
# Ad Service - Python Implementation
# Serves advertisements based on context keywords

import os
import sys
import time
import random
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

# Set the service name for Datadog APM
config.service = "adservice"
config.grpc["service_name"] = "adservice"  # For gRPC client spans
config.grpc_server["service_name"] = "adservice"  # For gRPC server spans

# Initialize Datadog tracing (auto-patches grpc, etc.)
patch_all()

# Configure logging with Datadog trace correlation
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "service": "adservice", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger('adservice-server')

def emit_ad_metrics(ads_requested: int, ads_served: int, categories_matched: int, total_categories: int):
    """Emit custom ad service metrics to Datadog"""
    span = tracer.current_span()
    if span:
        span.set_tag("ad.request.count", ads_requested)
        span.set_tag("ad.served.count", ads_served)
        if total_categories > 0:
            match_rate = categories_matched / total_categories
            span.set_tag("ad.category.match_rate", match_rate)

# ============================================

# Maximum number of ads to serve per request
MAX_ADS_TO_SERVE = 2

# Ads database - maps categories to ads
ADS_MAP = {
    "clothing": [
        {"redirect_url": "/product/66VCHSJNUP", "text": "Tank top for sale. 20% off."}
    ],
    "accessories": [
        {"redirect_url": "/product/1YMWWN1N4O", "text": "Watch for sale. Buy one, get second kit for free"}
    ],
    "footwear": [
        {"redirect_url": "/product/L9ECAV7KIM", "text": "Loafers for sale. Buy one, get second one for free"}
    ],
    "hair": [
        {"redirect_url": "/product/2ZYFJ3GM2N", "text": "Hairdryer for sale. 50% off."}
    ],
    "decor": [
        {"redirect_url": "/product/0PUK6V6EV0", "text": "Candle holder for sale. 30% off."}
    ],
    "kitchen": [
        {"redirect_url": "/product/9SIQT8TOJO", "text": "Bamboo glass jar for sale. 10% off."},
        {"redirect_url": "/product/6E92ZMYYFZ", "text": "Mug for sale. Buy two, get third one for free"}
    ],
}


def get_all_ads():
    """Returns a flat list of all ads."""
    all_ads = []
    for ads in ADS_MAP.values():
        all_ads.extend(ads)
    return all_ads


def get_ads_by_category(category):
    """Returns ads for a specific category."""
    return ADS_MAP.get(category.lower(), [])


def get_random_ads(count=MAX_ADS_TO_SERVE):
    """Returns a random selection of ads."""
    all_ads = get_all_ads()
    if len(all_ads) <= count:
        return all_ads
    return random.sample(all_ads, count)


class AdService(demo_pb2_grpc.AdServiceServicer):
    """Implementation of the AdService gRPC service."""

    def GetAds(self, request, context):
        """Retrieves ads based on context keywords provided in the request."""
        context_keys = list(request.context_keys)
        logger.info(f"received ad request (context_keys={context_keys})")

        ads = []
        categories_matched = 0

        # If context keys are provided, get ads for those categories
        if context_keys:
            for key in context_keys:
                category_ads = get_ads_by_category(key)
                if category_ads:
                    categories_matched += 1
                for ad_data in category_ads:
                    ad = demo_pb2.Ad(
                        redirect_url=ad_data["redirect_url"],
                        text=ad_data["text"]
                    )
                    ads.append(ad)

        # If no ads found for the context, return random ads
        if not ads:
            random_ads = get_random_ads()
            for ad_data in random_ads:
                ad = demo_pb2.Ad(
                    redirect_url=ad_data["redirect_url"],
                    text=ad_data["text"]
                )
                ads.append(ad)

        # Emit ad metrics
        emit_ad_metrics(
            ads_requested=1,
            ads_served=len(ads),
            categories_matched=categories_matched,
            total_categories=len(context_keys) if context_keys else 0
        )

        return demo_pb2.AdResponse(ads=ads)


class HealthServicer(health_pb2_grpc.HealthServicer):
    """Implementation of the gRPC Health service."""

    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING
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
                    service='ad_server',
                    service_version='1.0.0',
                    verbose=0,
                    project_id=project_id
                )
            else:
                googlecloudprofiler.start(
                    service='ad_server',
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
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add services
    demo_pb2_grpc.add_AdServiceServicer_to_server(AdService(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)

    port = os.environ.get('PORT', '9555')
    server.add_insecure_port(f'[::]:{port}')
    server.start()

    logger.info(f"Ad Service started, listening on port {port}")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down Ad Service")
        server.stop(0)


if __name__ == '__main__':
    logger.info("AdService starting.")

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
