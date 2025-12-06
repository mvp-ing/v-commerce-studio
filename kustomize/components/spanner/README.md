# Integrate v-commerce with Spanner

By default the `cartservice` stores its data in an in-cluster Redis database.
Using a fully managed database service outside your cluster (such as Spanner) could bring more resiliency and more security.

## Provision a Spanner Database

To provision a Spanner instance and database, follow your cloud provider's documentation.

Example database schema:

```sql
CREATE TABLE CartItems (
    userId STRING(1024),
    productId STRING(1024),
    quantity INT64
) PRIMARY KEY (userId, productId);

CREATE INDEX CartItemsByUserId ON CartItems(userId);
```

## Grant the `cartservice` Access to the Spanner Database

If using workload identity, ensure your Kubernetes service account has the appropriate permissions to access the Spanner database.

## Deploy v-commerce connected to a Spanner Database

To automate the deployment of v-commerce integrated with Spanner you can leverage the following variation with [Kustomize](../..).

From the `kustomize/` folder at the root level of this repository, execute these commands:

```bash
kustomize edit add component components/spanner
```

_Note: this Kustomize component will also remove the `redis-cart` `Deployment` and `Service` not used anymore._

This will update the `kustomize/kustomization.yaml` file which could be similar to:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - base
components:
  - components/spanner
```

Update current Kustomize manifest to target this Spanner database.

```bash
PROJECT_ID=<your-project-id>
SPANNER_INSTANCE_NAME=<your-instance>
SPANNER_DATABASE_NAME=carts

sed -i "s/SPANNER_PROJECT/${PROJECT_ID}/g" components/spanner/kustomization.yaml
sed -i "s/SPANNER_INSTANCE/${SPANNER_INSTANCE_NAME}/g" components/spanner/kustomization.yaml
sed -i "s/SPANNER_DATABASE/${SPANNER_DATABASE_NAME}/g" components/spanner/kustomization.yaml
```

You can locally render these manifests by running `kubectl kustomize .` as well as deploying them by running `kubectl apply -k .`.

## Note on Spanner Connection Environment Variables

The following environment variables will be used by the `cartservice`, if present:

- `SPANNER_INSTANCE`: defaults to `onlineboutique`, unless specified.
- `SPANNER_DATABASE`: defaults to `carts`, unless specified.
- `SPANNER_CONNECTION_STRING`: defaults to `projects/${SPANNER_PROJECT}/instances/${SPANNER_INSTANCE}/databases/${SPANNER_DATABASE}`. If this variable is defined explicitly, all other environment variables will be ignored.

## Resources

- [Spanner Documentation](https://spanner.google/)
