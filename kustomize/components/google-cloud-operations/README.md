# Integrate v-commerce with Observability Tools

By default, observability instrumentation is **turned off** for v-commerce deployments. This includes Monitoring (Stats), Tracing, and Profiler.

If you want to enable observability instrumentation, the easiest way is to enable the included kustomize module, which enables traces, metrics, and adds a deployment of the [Open Telemetry Collector](https://opentelemetry.io/docs/collector/) to gather the traces and metrics and forward them to your observability backend.

From the `kustomize/` folder at the root level of this repository, execute this command:

```bash
kustomize edit add component components/google-cloud-operations
```

This will update the `kustomize/kustomization.yaml` file which could be similar to:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - base
components:
  - components/google-cloud-operations
```

You can locally render these manifests by running `kubectl kustomize .` as well as deploying them by running `kubectl apply -k .`.

## Configuration

You will need to configure the OpenTelemetry Collector to export traces and metrics to your observability backend. Modify the [otel-collector.yaml](otel-collector.yaml) file to configure the appropriate exporters.

**Note**
Currently only trace is supported. Support for metrics, and more is coming soon.

## Changes

When enabling this kustomize module, most services will be patched with a configuration similar to the following:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: productcatalogservice
spec:
  template:
    spec:
      containers:
        - name: server
          env:
            - name: COLLECTOR_SERVICE_ADDR
              value: 'opentelemetrycollector:4317'
            - name: ENABLE_STATS
              value: '1'
            - name: ENABLE_TRACING
              value: '1'
```

This patch sets environment variables to enable export of stats and tracing, as well as a variable to tell the service how to reach the new collector deployment.

## OpenTelemetry Collector

Currently, this component adds a single collector service which collects traces and metrics from individual services and forwards them to your configured backend.

![Collector Architecture Diagram](collector-model.png)

If you wish to experiment with different backends, you can modify the appropriate lines in [otel-collector.yaml](otel-collector.yaml) to export traces or metrics to a different backend. See the [OpenTelemetry docs](https://opentelemetry.io/docs/collector/configuration/) for more details.

## Workload Identity

If you are running this sample on a managed Kubernetes service with workload identity enabled, you may need to configure the appropriate service account bindings to allow the OpenTelemetry Collector to export data to your observability services. Consult your cloud provider's documentation for setting up workload identity.
