# Integrate v-commerce with an External Redis Instance

By default the `cartservice` app is serializing the data in an in-cluster Redis database. Using a database outside your cluster could bring more resiliency and more security with a managed Redis service.

![Architecture diagram with External Redis](/docs/img/memorystore.png)

## Provision an External Redis Instance

You can provision an external Redis instance using your preferred cloud provider or self-hosted solution. Important notes:

- Ensure your Kubernetes cluster has network connectivity to the Redis instance.
- For managed Redis services, ensure proper network/VPC configuration.

## Deploy v-commerce connected to an External Redis Instance

To automate the deployment of v-commerce integrated with an external Redis instance, you can leverage the following variation with [Kustomize](../..).

From the `kustomize/` folder at the root level of this repository, execute this command:

```bash
kustomize edit add component components/memorystore
```

_Note: this Kustomize component will also remove the `redis-cart` `Deployment` and `Service` not used anymore._

This will update the `kustomize/kustomization.yaml` file which could be similar to:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - base
components:
  - components/memorystore
```

Update current Kustomize manifest to target your Redis instance.

```bash
REDIS_HOST="<your-redis-host>"
REDIS_PORT="<your-redis-port>"
sed -i "s/REDIS_CONNECTION_STRING/${REDIS_HOST}:${REDIS_PORT}/g" components/memorystore/kustomization.yaml
```

You can locally render these manifests by running `kubectl kustomize .` as well as deploying them by running `kubectl apply -k .`.

## Resources

- [Redis Documentation](https://redis.io/documentation)
