# v-commerce Quickstart

This tutorial shows you how to deploy **v-commerce** to a Kubernetes cluster.

You'll be able to run v-commerce on:

- a local **[minikube](https://minikube.sigs.k8s.io/docs/)** cluster
- a **[Kind](https://kind.sigs.k8s.io/)** cluster
- any managed Kubernetes service

Let's get started!

## Kubernetes cluster setup

Set up a Kubernetes cluster using the instructions below for either **minikube** or **Kind**.

### Minikube instructions

Minikube creates a local Kubernetes cluster.

1. Install minikube following the [official instructions](https://minikube.sigs.k8s.io/docs/start/).

2. Start minikube with sufficient resources:

   ```sh
   minikube start --cpus=4 --memory=4096 --disk-size=32g
   ```

3. Verify the cluster is running:

   ```sh
   kubectl get nodes
   ```

_It may take a few minutes for minikube to finish starting._

Once minikube has started, you're ready to move on to the next step.

### Kind instructions

Kind creates a local Kubernetes cluster using Docker.

1. Install Kind following the [official instructions](https://kind.sigs.k8s.io/docs/user/quick-start/#installation).

2. Create a cluster:

   ```sh
   kind create cluster
   ```

3. Verify the cluster is running:

   ```sh
   kubectl get nodes
   ```

## Run on Kubernetes

Now you can run v-commerce on your Kubernetes cluster!

1. Clone the repository:

   ```sh
   git clone <your-repo-url>
   cd v-commerce/
   ```

2. Deploy using skaffold:

   ```sh
   skaffold run
   ```

   _It may take a few minutes for the deploy to complete._

3. Once the app is running, verify all pods are ready:

   ```sh
   kubectl get pods
   ```

4. Access the frontend using port-forwarding:

   ```sh
   kubectl port-forward deployment/frontend 8080:8080
   ```

5. Open your browser and navigate to `http://localhost:8080`

## Stop the app

To stop running the app:

1. Press `Ctrl+C` to stop the port-forward.

2. Run `skaffold delete` to clean up deployed resources.

## Conclusion

Congratulations! You've successfully deployed v-commerce.

##### What's next?

Try other deployment options for v-commerce:

- **Istio/Service Mesh**: See the instructions in `./kustomize/components/service-mesh-istio/README.md`.
- **Kustomize Components**: Explore various components in `./kustomize/components/` for additional features.
