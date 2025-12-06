# Service mesh with Istio

You can use [Istio](https://istio.io) to enable service mesh features such as traffic management, observability, and security. Istio can be provisioned using the open source `istioctl` tool or via managed service mesh offerings. You can then label individual namespaces for sidecar injection and configure an Istio gateway to replace the frontend-external load balancer.

# Setup

The following CLI tools need to be installed and in the PATH:

- `kubectl`
- `kustomize`
- `istioctl`

1. Set up some default environment variables.

   ```sh
   CLUSTER_NAME="v-commerce"
   ```

# Provision a Kubernetes Cluster

1. Create a Kubernetes cluster using your preferred method (minikube, kind, or a managed Kubernetes service).

   ```sh
   # Example with kind
   kind create cluster --name $CLUSTER_NAME
   ```

1. Change your kubectl context for the newly created cluster.

   ```sh
   kubectl config use-context kind-$CLUSTER_NAME
   ```

# Provision and Configure Istio Service Mesh

## Install Istio using istioctl

1. Install the open source version of Istio by following the [getting started guide](https://istio.io/latest/docs/setup/getting-started/).

   ```sh
   # Install istio 1.17 or above
   istioctl install --set profile=minimal -y

   # Enable sidecar injection for Kubernetes namespace(s) where v-commerce is deployed
   kubectl label namespace default istio-injection=enabled
   ```

# Deploy v-commerce with the Istio component

Once the service mesh and namespace injection are configured, you can then deploy the Istio manifests using Kustomize.

1. Enable the service-mesh-istio component.

   ```sh
   cd kustomize/
   kustomize edit add component components/service-mesh-istio
   ```

   This will update the `kustomize/kustomization.yaml` file which could be similar to:

   ```yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization
   resources:
     - base
   components:
     - components/service-mesh-istio
   ```

   _Note: `service-mesh-istio` component includes the same delete patch as the `non-public-frontend` component. Trying to use both those components in your kustomization.yaml file will result in an error._

1. Deploy the manifests.

   ```sh
   kubectl apply -k .
   ```

# Verify that the deployment succeeded

1. Check that the pods and the gateway are in a healthy and ready state.

   ```sh
   kubectl get pods,gateways,services
   ```

1. Find the external IP address of your Istio gateway.

   ```sh
   INGRESS_HOST="$(kubectl get gateway istio-gateway \
       -o jsonpath='{.status.addresses[*].value}')"
   ```

1. Navigate to the frontend in a web browser.

   ```
   http://$INGRESS_HOST
   ```

# Additional service mesh demos

- [Canary deployment](https://istio.io/latest/docs/tasks/traffic-management/traffic-shifting/)
- [Security (mTLS, JWT, Authorization)](https://istio.io/latest/docs/tasks/security/)

# Related resources

- [Istio Gateway documentation](https://istio.io/latest/docs/tasks/traffic-management/ingress/gateway-api/)
- [Uninstall Istio via istioctl](https://istio.io/latest/docs/setup/install/istioctl/#uninstall-istio)
