# Development Guide

This doc explains how to build and run the v-commerce source code locally using the `skaffold` command-line tool.

## Prerequisites

- [Docker for Desktop](https://www.docker.com/products/docker-desktop)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [skaffold **2.0.2+**](https://skaffold.dev/docs/install/) (latest version recommended), a tool that builds and deploys Docker images in bulk.
- Clone the repository.
  ```sh
  git clone <your-repo-url>
  cd v-commerce/
  ```
- [Minikube](https://minikube.sigs.k8s.io/docs/start/) (optional)
- [Kind](https://kind.sigs.k8s.io/) (optional)

## Local Cluster Deployment

1. Launch a local Kubernetes cluster with one of the following tools:

   - To launch **Minikube** (tested with Ubuntu Linux). Please, ensure that the
     local Kubernetes cluster has at least:

     - 4 CPUs
     - 4.0 GiB memory
     - 32 GB disk space

     ```shell
     minikube start --cpus=4 --memory 4096 --disk-size 32g
     ```

   - To launch **Docker for Desktop** (tested with Mac/Windows). Go to Preferences:

     - choose "Enable Kubernetes",
     - set CPUs to at least 3, and Memory to at least 6.0 GiB
     - on the "Disk" tab, set at least 32 GB disk space

   - To launch a **Kind** cluster:

     ```shell
     kind create cluster
     ```

2. Run `kubectl get nodes` to verify you're connected to the respective control plane.

3. Run `skaffold run` (first time will be slow, it can take ~20 minutes).
   This will build and deploy the application. If you need to rebuild the images
   automatically as you refactor the code, run `skaffold dev` command.

4. Run `kubectl get pods` to verify the Pods are ready and running.

5. Run `kubectl port-forward deployment/frontend 8080:8080` to forward a port to the frontend service.

6. Navigate to `localhost:8080` to access the web frontend.

## Adding a new microservice

In general, the set of core microservices for v-commerce is fairly complete and unlikely to change in the future, but it can be useful to add an additional optional microservice that can be deployed to complement the core services.

See the [Adding a new microservice](adding-new-microservice.md) guide for instructions on how to add a new microservice.

## Cleanup

If you've deployed the application with `skaffold run` command, you can run
`skaffold delete` to clean up the deployed resources.
