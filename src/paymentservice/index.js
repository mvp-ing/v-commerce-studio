'use strict';

// Datadog APM - must be initialized before any other imports
const tracer = require('dd-trace').init({
  service: process.env.DD_SERVICE || 'paymentservice',
  env: process.env.DD_ENV || 'production',
  logInjection: true,
  runtimeMetrics: true,
  profiling: true,
});

// Initialize custom metrics
const StatsD = require('hot-shots');

// Create StatsD client for custom metrics
const statsd = new StatsD({
  host: process.env.DD_AGENT_HOST || 'localhost',
  port: process.env.DD_DOGSTATSD_PORT || 8125,
  prefix: 'payment.',
  globalTags: {
    env: process.env.DD_ENV || 'production',
    service: 'paymentservice',
  },
  errorHandler: (error) => {
    console.error('StatsD error:', error);
  },
});

// Export statsd for use in other modules
module.exports.statsd = statsd;
module.exports.tracer = tracer;

const logger = require('./logger');

if (process.env.DISABLE_PROFILER) {
  logger.info('Profiler disabled.');
} else {
  logger.info('Profiler enabled.');
  require('@google-cloud/profiler').start({
    serviceContext: {
      service: 'paymentservice',
      version: '1.0.0',
    },
  });
}

if (process.env.ENABLE_TRACING == '1') {
  logger.info('Tracing enabled.');

  const { resourceFromAttributes } = require('@opentelemetry/resources');

  const { ATTR_SERVICE_NAME } = require('@opentelemetry/semantic-conventions');

  const {
    GrpcInstrumentation,
  } = require('@opentelemetry/instrumentation-grpc');
  const {
    registerInstrumentations,
  } = require('@opentelemetry/instrumentation');
  const opentelemetry = require('@opentelemetry/sdk-node');

  const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-grpc');

  const collectorUrl = process.env.COLLECTOR_SERVICE_ADDR;
  const traceExporter = new OTLPTraceExporter({ url: collectorUrl });

  const sdk = new opentelemetry.NodeSDK({
    resource: resourceFromAttributes({
      [ATTR_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME || 'paymentservice',
    }),
    traceExporter: traceExporter,
  });

  registerInstrumentations({
    instrumentations: [new GrpcInstrumentation()],
  });

  sdk.start();
} else {
  logger.info('Tracing disabled.');
}

const path = require('path');
const HipsterShopServer = require('./server');

const PORT = process.env['PORT'];
const PROTO_PATH = path.join(__dirname, '/proto/');

const server = new HipsterShopServer(PROTO_PATH, PORT);

logger.info('Datadog APM tracing enabled for paymentservice');

// Emit initial service status metric
statsd.gauge('service.status', 1);

server.listen();
