#!/usr/bin/python
#
 

from concurrent import futures
import argparse
import os
import sys
import time
import grpc
import traceback
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateError
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import DefaultCredentialsError

import demo_pb2
import demo_pb2_grpc
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

# ============================================
# Datadog APM Setup
# ============================================
from ddtrace import tracer, patch_all, config
import logging

# Set service name before patching
config.service = "emailservice"
config.grpc["service_name"] = "emailservice"  # For gRPC client spans
config.grpc_server["service_name"] = "emailservice"  # For gRPC server spans

# Initialize Datadog tracing (auto-patches grpc, jinja2, etc.)
patch_all()

# Configure logging with Datadog trace correlation
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "service": "emailservice", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger('emailservice-server')

def emit_email_metrics(email_sent: bool, render_time_ms: float = None, delivery_success: bool = True):
    """Emit custom email service metrics to Datadog"""
    span = tracer.current_span()
    if span:
        span.set_tag("email.sent.count", 1 if email_sent else 0)
        span.set_tag("email.delivery.success", delivery_success)
        if render_time_ms is not None:
            span.set_tag("email.render.duration_ms", render_time_ms)

# ============================================

# Loads confirmation email template from file
env = Environment(
    loader=FileSystemLoader('templates'),
    autoescape=select_autoescape(['html', 'xml'])
)
template = env.get_template('confirmation.html')

class BaseEmailService(demo_pb2_grpc.EmailServiceServicer):
  def Check(self, request, context):
    return health_pb2.HealthCheckResponse(
      status=health_pb2.HealthCheckResponse.SERVING)
  
  def Watch(self, request, context):
    return health_pb2.HealthCheckResponse(
      status=health_pb2.HealthCheckResponse.UNIMPLEMENTED)

class EmailService(BaseEmailService):
  def __init__(self):
    raise Exception('cloud mail client not implemented')
    super().__init__()

  @staticmethod
  def send_email(client, email_address, content):
    response = client.send_message(
      sender = client.sender_path(project_id, region, sender_id),
      envelope_from_authority = '',
      header_from_authority = '',
      envelope_from_address = from_address,
      simple_message = {
        "from": {
          "address_spec": from_address,
        },
        "to": [{
          "address_spec": email_address
        }],
        "subject": "Your Confirmation Email",
        "html_body": content
      }
    )
    logger.info("Message sent: {}".format(response.rfc822_message_id))

  def SendOrderConfirmation(self, request, context):
    email = request.email
    order = request.order

    try:
      confirmation = template.render(order = order)
    except TemplateError as err:
      context.set_details("An error occurred when preparing the confirmation mail.")
      logger.error(err.message)
      context.set_code(grpc.StatusCode.INTERNAL)
      return demo_pb2.Empty()

    try:
      EmailService.send_email(self.client, email, confirmation)
    except GoogleAPICallError as err:
      context.set_details("An error occurred when sending the email.")
      print(err.message)
      context.set_code(grpc.StatusCode.INTERNAL)
      return demo_pb2.Empty()

    return demo_pb2.Empty()

class DummyEmailService(BaseEmailService):
  def SendOrderConfirmation(self, request, context):
    start_time = time.time()
    logger.info('A request to send order confirmation email to {} has been received.'.format(request.email))
    
    # Emit metrics for the email send operation
    render_time = (time.time() - start_time) * 1000
    emit_email_metrics(email_sent=True, render_time_ms=render_time, delivery_success=True)
    
    return demo_pb2.Empty()

class HealthCheck():
  def Check(self, request, context):
    return health_pb2.HealthCheckResponse(
      status=health_pb2.HealthCheckResponse.SERVING)

def start(dummy_mode):
  server = grpc.server(futures.ThreadPoolExecutor(max_workers=10),)
  service = None
  if dummy_mode:
    service = DummyEmailService()
  else:
    raise Exception('non-dummy mode not implemented yet')

  demo_pb2_grpc.add_EmailServiceServicer_to_server(service, server)
  health_pb2_grpc.add_HealthServicer_to_server(service, server)

  port = os.environ.get('PORT', "8080")
  logger.info("listening on port: "+port)
  server.add_insecure_port('[::]:'+port)
  server.start()
  try:
    while True:
      time.sleep(3600)
  except KeyboardInterrupt:
    server.stop(0)

def initStackdriverProfiling():
  project_id = None
  try:
    project_id = os.environ["GCP_PROJECT_ID"]
  except KeyError:
    # Environment variable not set
    pass

  for retry in range(1,4):
    try:
      if project_id:
        googlecloudprofiler.start(service='email_server', service_version='1.0.0', verbose=0, project_id=project_id)
      else:
        googlecloudprofiler.start(service='email_server', service_version='1.0.0', verbose=0)
      logger.info("Successfully started Stackdriver Profiler.")
      return
    except (BaseException) as exc:
      logger.info("Unable to start Stackdriver Profiler Python agent. " + str(exc))
      if (retry < 4):
        logger.info("Sleeping %d to retry initializing Stackdriver Profiler"%(retry*10))
        time.sleep (1)
      else:
        logger.warning("Could not initialize Stackdriver Profiler after retrying, giving up")
  return


if __name__ == '__main__':
  logger.info('starting the email service in dummy mode.')

  # Profiler disabled - using Datadog APM instead
  logger.info("Profiler disabled - using Datadog APM.")

  # Tracing is handled by ddtrace.patch_all() automatically
  logger.info("Datadog APM tracing enabled via ddtrace.")
  
  start(dummy_mode = True)
