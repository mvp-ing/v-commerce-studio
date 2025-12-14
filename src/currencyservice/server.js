// Datadog APM - must be initialized before any other imports
const tracer = require('dd-trace').init({
  service: process.env.DD_SERVICE || 'currencyservice',
  env: process.env.DD_ENV || 'production',
  logInjection: true,
  runtimeMetrics: true,
  profiling: true,
});

// Initialize custom metrics
const { dogstatsd } = require('dd-trace');
const StatsD = require('hot-shots');

// Create StatsD client for custom metrics (agentless mode uses Datadog API)
const statsd = new StatsD({
  host: process.env.DD_AGENT_HOST || 'localhost',
  port: process.env.DD_DOGSTATSD_PORT || 8125,
  prefix: 'currency.',
  globalTags: {
    env: process.env.DD_ENV || 'production',
    service: 'currencyservice',
  },
  errorHandler: (error) => {
    console.error('StatsD error:', error);
  },
});

const pino = require('pino');
const logger = pino({
  name: 'currencyservice-server',
  messageKey: 'message',
  formatters: {
    level(logLevelString, logLevelNum) {
      return { severity: logLevelString };
    },
  },
  // Add trace correlation for Datadog
  mixin() {
    const span = tracer.scope().active();
    if (span) {
      const traceId = span.context().toTraceId();
      const spanId = span.context().toSpanId();
      return {
        dd: {
          trace_id: traceId,
          span_id: spanId,
          service: 'currencyservice',
          env: process.env.DD_ENV || 'production',
        },
      };
    }
    return {};
  },
});

if (process.env.DISABLE_PROFILER) {
  logger.info('Profiler disabled.');
} else {
  logger.info('Profiler enabled.');
  require('@google-cloud/profiler').start({
    serviceContext: {
      service: 'currencyservice',
      version: '1.0.0',
    },
  });
}

// Register GRPC OTel Instrumentation for trace propagation
// regardless of whether tracing is emitted.
const { GrpcInstrumentation } = require('@opentelemetry/instrumentation-grpc');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');

registerInstrumentations({
  instrumentations: [new GrpcInstrumentation()],
});

if (process.env.ENABLE_TRACING == '1') {
  logger.info('Tracing enabled.');

  const { resourceFromAttributes } = require('@opentelemetry/resources');

  const { ATTR_SERVICE_NAME } = require('@opentelemetry/semantic-conventions');

  const opentelemetry = require('@opentelemetry/sdk-node');

  const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-grpc');

  const collectorUrl = process.env.COLLECTOR_SERVICE_ADDR;
  const traceExporter = new OTLPTraceExporter({ url: collectorUrl });
  const sdk = new opentelemetry.NodeSDK({
    resource: resourceFromAttributes({
      [ATTR_SERVICE_NAME]: process.env.OTEL_SERVICE_NAME || 'currencyservice',
    }),
    traceExporter: traceExporter,
  });

  sdk.start();
} else {
  logger.info('Tracing disabled.');
}

const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const MAIN_PROTO_PATH = path.join(__dirname, './proto/demo.proto');
const HEALTH_PROTO_PATH = path.join(
  __dirname,
  './proto/grpc/health/v1/health.proto'
);

const PORT = process.env.PORT;

const shopProto = _loadProto(MAIN_PROTO_PATH).hipstershop;
const healthProto = _loadProto(HEALTH_PROTO_PATH).grpc.health.v1;

// Track currency data last update time
let currencyDataLastUpdate = Date.now();

/**
 * Helper function that loads a protobuf file.
 */
function _loadProto(path) {
  const packageDefinition = protoLoader.loadSync(path, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
  return grpc.loadPackageDefinition(packageDefinition);
}

/**
 * Helper function that gets currency data from a stored JSON file
 * Uses public data from European Central Bank
 */
function _getCurrencyData(callback) {
  const data = require('./data/currency_conversion.json');
  // Track last update of currency data (in production, this would be from actual data fetch)
  currencyDataLastUpdate = Date.now();
  statsd.gauge('rate.last_update', currencyDataLastUpdate / 1000);
  callback(data);
}

/**
 * Helper function that handles decimal/fractional carrying
 */
function _carry(amount) {
  const fractionSize = Math.pow(10, 9);
  amount.nanos += (amount.units % 1) * fractionSize;
  amount.units =
    Math.floor(amount.units) + Math.floor(amount.nanos / fractionSize);
  amount.nanos = amount.nanos % fractionSize;
  return amount;
}

/**
 * Lists the supported currencies
 */
function getSupportedCurrencies(call, callback) {
  const span = tracer.startSpan('getSupportedCurrencies', {
    childOf: tracer.scope().active(),
    tags: {
      'resource.name': 'CurrencyService.GetSupportedCurrencies',
    },
  });

  logger.info('Getting supported currencies...');
  statsd.increment('request.count', 1, { operation: 'getSupportedCurrencies' });

  _getCurrencyData((data) => {
    const currencies = Object.keys(data);
    span.setTag('currencies.count', currencies.length);
    span.finish();
    callback(null, { currency_codes: currencies });
  });
}

/**
 * Converts between currencies
 */
function convert(call, callback) {
  const startTime = Date.now();
  const span = tracer.startSpan('convert', {
    childOf: tracer.scope().active(),
    tags: {
      'resource.name': 'CurrencyService.Convert',
    },
  });

  statsd.increment('request.count', 1, { operation: 'convert' });

  try {
    _getCurrencyData((data) => {
      const request = call.request;

      span.setTag('from_currency', request.from.currency_code);
      span.setTag('to_currency', request.to_code);
      span.setTag('amount.units', request.from.units);

      // Convert: from_currency --> EUR
      const from = request.from;
      const euros = _carry({
        units: from.units / data[from.currency_code],
        nanos: from.nanos / data[from.currency_code],
      });

      euros.nanos = Math.round(euros.nanos);

      // Convert: EUR --> to_currency
      const result = _carry({
        units: euros.units * data[request.to_code],
        nanos: euros.nanos * data[request.to_code],
      });

      result.units = Math.floor(result.units);
      result.nanos = Math.floor(result.nanos);
      result.currency_code = request.to_code;

      // Track conversion latency
      const latency = Date.now() - startTime;
      statsd.histogram('conversion.latency', latency, {
        from: request.from.currency_code,
        to: request.to_code,
      });
      statsd.increment('conversion.count', 1, {
        from: request.from.currency_code,
        to: request.to_code,
        success: 'true',
      });

      span.setTag('result.units', result.units);
      span.setTag('conversion.latency_ms', latency);
      span.finish();

      logger.info(`conversion request successful`);
      callback(null, result);
    });
  } catch (err) {
    const latency = Date.now() - startTime;
    statsd.histogram('conversion.latency', latency, { error: 'true' });
    statsd.increment('conversion.count', 1, { success: 'false' });
    statsd.increment('error.count', 1, { operation: 'convert' });

    span.setTag('error', true);
    span.setTag('error.message', err.message);
    span.finish();

    logger.error(`conversion request failed: ${err}`);
    callback(err.message);
  }
}

/**
 * Endpoint for health checks
 */
function check(call, callback) {
  callback(null, { status: 'SERVING' });
}

/**
 * Starts an RPC server that receives requests for the
 * CurrencyConverter service at the sample server port
 */
function main() {
  logger.info(`Starting gRPC server on port ${PORT}...`);
  logger.info('Datadog APM tracing enabled for currencyservice');

  const server = new grpc.Server();
  server.addService(shopProto.CurrencyService.service, {
    getSupportedCurrencies,
    convert,
  });
  server.addService(healthProto.Health.service, { check });

  server.bindAsync(
    `[::]:${PORT}`,
    grpc.ServerCredentials.createInsecure(),
    function () {
      logger.info(`CurrencyService gRPC server started on port ${PORT}`);
      server.start();

      // Emit initial metrics
      statsd.gauge('service.status', 1);
      statsd.gauge('rate.last_update', currencyDataLastUpdate / 1000);
    }
  );
}

main();
