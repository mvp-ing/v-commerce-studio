## Deploy v-commerce

v-commerce can be deployed to any Kubernetes cluster. See the [Development Guide](development-guide.md) for instructions on deploying to a local cluster using Minikube, Kind, or Docker Desktop.

For production deployments, you can use the Kubernetes manifests in the `/release` directory or deploy using Helm charts from the `/helm-chart` directory.

### Deployment Options

1. **Local Development**: Use Minikube, Kind, or Docker Desktop with Skaffold
2. **Helm Chart**: Deploy using the Helm chart in `/helm-chart`
3. **Kustomize**: Use Kustomize to customize deployments with various components
4. **Raw Manifests**: Apply the manifests in `/release/kubernetes-manifests.yaml` directly
