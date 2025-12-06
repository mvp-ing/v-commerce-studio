# Update the container registry of the v-commerce apps

By default, v-commerce's services' container images are pulled from a public container registry. One best practice is to have these container images in your own private container registry. The Kustomize variation in this folder can help with using your own private container registry.

## Change the default container registry via Kustomize

To automate the deployment of v-commerce integrated with your own container registry, you can leverage the following variation with [Kustomize](../..).

From the `kustomize/` folder at the root level of this repository, execute this command:

```bash
REGISTRY=my-registry # Example: my-registry.example.com/v-commerce
sed -i "s|CONTAINER_IMAGES_REGISTRY|${REGISTRY}|g" components/container-images-registry/kustomization.yaml
kustomize edit add component components/container-images-registry
```

_Note: this Kustomize component will update the container registry in the `image:` field in all `Deployments`._

This will update the `kustomize/kustomization.yaml` file which could be similar to:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - base
components:
  - components/container-images-registry
```

You can (optionally) locally render these manifests by running `kubectl kustomize .`.
You can deploy them by running `kubectl apply -k .`.
