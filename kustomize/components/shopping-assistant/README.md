# Shopping Assistant with RAG & Database

This demo adds a new service to v-commerce called `shoppingassistantservice` which, alongside a database-backed products catalog, adds a RAG-featured AI assistant to the frontend experience, helping users suggest products matching their home decor.

## Setup Instructions

**Note:** This demo requires a PostgreSQL-compatible database and access to an LLM API.

1. Set some environment variables.

   ```sh
   export PROJECT_ID=<project_id>
   export PGPASSWORD=<pgpassword>
   export LLM_API_KEY=<your-llm-api-key>
   ```

   **Note**: The PostgreSQL password can be set to anything you want, but make sure to note it down.

1. Create a Kubernetes cluster using your preferred method.

   ```sh
   # Example with kind
   kind create cluster --name v-commerce
   ```

1. Change your Kubernetes context to your cluster.

   ```sh
   kubectl config use-context kind-v-commerce
   ```

1. Set up a PostgreSQL-compatible database (AlloyDB, Cloud SQL, Amazon RDS, or self-hosted PostgreSQL).

1. Create the required database schema:

   ```sql
   CREATE DATABASE products;
   
   \c products
   
   -- Create the products table with vector support
   CREATE EXTENSION IF NOT EXISTS vector;
   
   CREATE TABLE products (
       id TEXT PRIMARY KEY,
       name TEXT,
       description TEXT,
       picture TEXT,
       price_usd_units INT,
       price_usd_nanos INT,
       categories TEXT[],
       embedding vector(768)
   );
   ```

1. Populate the products table with your product data and embeddings.

1. Clone the repository locally.

   ```sh
   git clone <your-repo-url>
   cd v-commerce/
   ```

1. Replace the API key placeholder in the shoppingassistant service.

   ```sh
   export LLM_API_KEY=<your-llm-api-key>
   sed -i "s/GOOGLE_API_KEY_VAL/${LLM_API_KEY}/g" kustomize/components/shopping-assistant/shoppingassistantservice.yaml
   ```

1. Edit the root Kustomize file to enable the `alloydb` and `shopping-assistant` components.

   ```sh
   nano kustomize/kustomization.yaml
   ```

   ```yaml
   apiVersion: kustomize.config.k8s.io/v1beta1
   kind: Kustomization
   resources:
     - base
   components:
     - components/alloydb
     - components/shopping-assistant
   ```

1. Update the database connection settings in the alloydb component:

   ```sh
   # Update with your database connection details
   sed -i "s/ALLOYDB_PRIMARY_IP_VAL/<your-db-host>/g" kustomize/components/alloydb/kustomization.yaml
   sed -i "s/ALLOYDB_DATABASE_NAME_VAL/products/g" kustomize/components/alloydb/kustomization.yaml
   ```

1. Deploy to the Kubernetes cluster.

   ```sh
   kubectl apply -k kustomize/
   ```

1. Wait for all the pods to be up and running. You can then access the frontend.

   ```sh
   kubectl get pods
   kubectl port-forward deployment/frontend 8080:8080
   ```

1. Navigate to `http://localhost:8080` to access v-commerce with the shopping assistant feature.
