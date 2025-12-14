const pino = require('pino');

// Get tracer for log correlation (may not be initialized yet during startup)
let tracer;
try {
  tracer = require('dd-trace');
} catch (e) {
  tracer = null;
}

module.exports = pino({
  name: 'paymentservice-server',
  messageKey: 'message',
  formatters: {
    level(logLevelString, logLevelNum) {
      return { severity: logLevelString };
    },
  },
  // Add trace correlation for Datadog
  mixin() {
    if (tracer) {
      const span = tracer.scope().active();
      if (span) {
        const traceId = span.context().toTraceId();
        const spanId = span.context().toSpanId();
        return {
          dd: {
            trace_id: traceId,
            span_id: spanId,
            service: 'paymentservice',
            env: process.env.DD_ENV || 'production',
          },
        };
      }
    }
    return {};
  },
});
