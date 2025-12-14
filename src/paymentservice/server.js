const path = require('path');
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const charge = require('./charge');
const logger = require('./logger');

// Get tracer and statsd from index.js
let tracer, statsd;
try {
  const main = require('./index');
  tracer = main.tracer;
  statsd = main.statsd;
} catch (e) {
  // Fallback if index.js hasn't initialized yet
  tracer = require('dd-trace');
  const StatsD = require('hot-shots');
  statsd = new StatsD({
    host: process.env.DD_AGENT_HOST || 'localhost',
    port: process.env.DD_DOGSTATSD_PORT || 8125,
    prefix: 'payment.',
    globalTags: {
      env: process.env.DD_ENV || 'production',
      service: 'paymentservice',
    },
  });
}

class HipsterShopServer {
  constructor(protoRoot, port = HipsterShopServer.PORT) {
    this.port = port;

    this.packages = {
      hipsterShop: this.loadProto(path.join(protoRoot, 'demo.proto')),
      health: this.loadProto(
        path.join(protoRoot, 'grpc/health/v1/health.proto')
      ),
    };

    this.server = new grpc.Server();
    this.loadAllProtos(protoRoot);
  }

  /**
   * Handler for PaymentService.Charge.
   * @param {*} call  { ChargeRequest }
   * @param {*} callback  fn(err, ChargeResponse)
   */
  static ChargeServiceHandler(call, callback) {
    const startTime = Date.now();
    const fraudCheckStart = Date.now();

    // Create a span for the charge operation
    const span = tracer.startSpan('PaymentService.Charge', {
      childOf: tracer.scope().active(),
      tags: {
        'resource.name': 'PaymentService.Charge',
        'span.kind': 'server',
      },
    });

    try {
      logger.info(
        `PaymentService#Charge invoked with request ${JSON.stringify(
          call.request
        )}`
      );

      // Track request
      statsd.increment('request.count', 1, { operation: 'charge' });

      // Extract amount info for metrics
      const amount = call.request.amount;
      span.setTag(
        'payment.currency',
        amount ? amount.currency_code : 'unknown'
      );
      span.setTag('payment.units', amount ? amount.units : 0);

      // Simulate fraud check (in real implementation, this would be an actual check)
      const fraudCheckDuration = Date.now() - fraudCheckStart;
      statsd.histogram('fraud_check.duration', fraudCheckDuration);
      span.setTag('fraud_check.duration_ms', fraudCheckDuration);

      // Process the charge
      const response = charge(call.request);

      // Track successful transaction
      const totalDuration = Date.now() - startTime;
      statsd.increment('transaction.count', 1, {
        status: 'success',
        currency: amount ? amount.currency_code : 'unknown',
      });
      statsd.histogram('transaction.duration', totalDuration, {
        status: 'success',
      });

      // Track transaction amount if available
      if (amount && amount.units) {
        statsd.histogram('transaction.amount', amount.units, {
          currency: amount.currency_code,
        });
      }

      span.setTag('payment.transaction_id', response.transaction_id);
      span.setTag('payment.success', true);
      span.setTag('payment.duration_ms', totalDuration);
      span.finish();

      callback(null, response);
    } catch (err) {
      const totalDuration = Date.now() - startTime;

      // Track failed transaction
      statsd.increment('transaction.count', 1, {
        status: 'error',
        error_type: err.constructor.name,
      });
      statsd.increment('error.count', 1, {
        operation: 'charge',
        error_type: err.constructor.name,
      });
      statsd.histogram('transaction.duration', totalDuration, {
        status: 'error',
      });

      span.setTag('error', true);
      span.setTag('error.type', err.constructor.name);
      span.setTag('error.message', err.message);
      span.setTag('payment.success', false);
      span.finish();

      console.warn(err);
      callback(err);
    }
  }

  static CheckHandler(call, callback) {
    callback(null, { status: 'SERVING' });
  }

  listen() {
    const server = this.server;
    const port = this.port;
    server.bindAsync(
      `[::]:${port}`,
      grpc.ServerCredentials.createInsecure(),
      function () {
        logger.info(`PaymentService gRPC server started on port ${port}`);
        server.start();
      }
    );
  }

  loadProto(path) {
    const packageDefinition = protoLoader.loadSync(path, {
      keepCase: true,
      longs: String,
      enums: String,
      defaults: true,
      oneofs: true,
    });
    return grpc.loadPackageDefinition(packageDefinition);
  }

  loadAllProtos(protoRoot) {
    const hipsterShopPackage = this.packages.hipsterShop.hipstershop;
    const healthPackage = this.packages.health.grpc.health.v1;

    this.server.addService(hipsterShopPackage.PaymentService.service, {
      charge: HipsterShopServer.ChargeServiceHandler.bind(this),
    });

    this.server.addService(healthPackage.Health.service, {
      check: HipsterShopServer.CheckHandler.bind(this),
    });
  }
}

HipsterShopServer.PORT = process.env.PORT;

module.exports = HipsterShopServer;
