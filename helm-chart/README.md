# Helm chart for v-commerce

If you'd like to deploy v-commerce via its Helm chart, you could leverage the following instructions.

**Warning:** v-commerce's Helm chart is currently experimental. If you have feedback or run into issues, please create a GitHub Issue.

Deploy the default setup of v-commerce:

```sh
helm upgrade vcommerce ./helm-chart \
    --install
```

Deploy advanced scenario of v-commerce:

```sh
helm upgrade vcommerce ./helm-chart \
    --install \
    --create-namespace \
    --set images.repository=<your-registry>/v-commerce \
    --set frontend.externalService=false \
    --set redis.create=false \
    --set cartservice.database.type=spanner \
    --set cartservice.database.connectionString=<your-connection-string> \
    --set serviceAccounts.create=true \
    --set authorizationPolicies.create=true \
    --set networkPolicies.create=true \
    --set sidecars.create=true \
    --set frontend.virtualService.create=true \
    -n vcommerce
```

For the full list of configurations, see [values.yaml](./values.yaml).

You could also find advanced scenarios with these blogs below:

- [Helm chart usage for advanced and secured scenarios with Service Mesh and GitOps](https://medium.com/google-cloud/246119e46d53)
- [gRPC health probes with Kubernetes 1.24+](https://medium.com/google-cloud/b5bd26253a4c)
