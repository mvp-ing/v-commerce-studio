# Integrate v-commerce with AlloyDB (PostgreSQL)

By default the `cartservice` stores its data in an in-cluster Redis database.
Using a fully managed database service outside your cluster (such as AlloyDB or PostgreSQL) could bring more resiliency and more security.

Note that for managed database services, you'll need network connectivity from your Kubernetes cluster to the database.

## Provision an AlloyDB/PostgreSQL Database

You can use AlloyDB, Cloud SQL for PostgreSQL, Amazon RDS, or any PostgreSQL-compatible database.

### Environment Variables

Set the following environment variables for setup:

```bash
PROJECT_ID=<project_id>
REGION=<region>
ALLOYDB_DATABASE_NAME=carts
ALLOYDB_TABLE_NAME=cart_items
PGPASSWORD=<password>
```

### Database Schema

Create the required database and table:

```sql
CREATE DATABASE carts;

\c carts

CREATE TABLE cart_items (
    userId text,
    productId text,
    quantity int,
    PRIMARY KEY(userId, productId)
);

CREATE INDEX cartItemsByUserId ON cart_items(userId);
```

## Grant the `cartservice` Access to the Database

Ensure your Kubernetes service account has appropriate access to the database credentials. You can store credentials in Kubernetes secrets.

## Deploy v-commerce connected to an AlloyDB Database

To automate the deployment of v-commerce integrated with AlloyDB you can leverage the following variation with [Kustomize](../..).

From the `kustomize/` folder at the root level of this repository, execute these commands:

```bash
kustomize edit add component components/alloydb
```

_**Note:** this Kustomize component will also remove the `redis-cart` `Deployment` and `Service` not used anymore._

This will update the `kustomize/kustomization.yaml` file which could be similar to:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - base
components:
  - components/alloydb
```

Update current Kustomize manifest to target this AlloyDB database.

```bash
sed -i "s/PROJECT_ID_VAL/${PROJECT_ID}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_PRIMARY_IP_VAL/${ALLOYDB_PRIMARY_IP}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_DATABASE_NAME_VAL/${ALLOYDB_DATABASE_NAME}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_TABLE_NAME_VAL/${ALLOYDB_TABLE_NAME}/g" components/alloydb/kustomization.yaml
```

You can locally render these manifests by running `kubectl kustomize .` as well as deploying them by running `kubectl apply -k .`.

## Cleanup

```bash
# Delete database resources as needed for your provider
```
