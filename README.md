# v-commerce

A cloud-native microservices demo application showcasing modern e-commerce patterns with AI-powered features, built for Kubernetes and cloud-native environments.

## 🎯 Purpose

v-commerce is designed to demonstrate:

- **Microservices architecture patterns** - Distributed system design with multiple services
- **Kubernetes deployments and orchestration** - Production-ready containerized applications
- **Cloud-native application development** - Best practices for modern distributed systems
- **Observability and monitoring** - Comprehensive telemetry with Datadog integration
- **AI/LLM integration** - Multiple AI-powered services using Gemini models

The application is accessible and useful to all Kubernetes users, from beginners to experienced practitioners.

## 🏗️ Architecture

v-commerce is built as a collection of microservices, each responsible for a specific domain:

- **Frontend** (Go) - Web UI and API gateway
- **Backend Services** - Multiple gRPC services handling business logic
- **AI Services** - LLM-powered features for enhanced user experience
- **Infrastructure** - Kubernetes-native deployment with Helm and Kustomize

### Core Services

| Service             | Language | Description                                         |
| ------------------- | -------- | --------------------------------------------------- |
| **Frontend**        | Go       | Web frontend serving the user interface             |
| **Product Catalog** | Go       | Manages product inventory and search                |
| **Cart**            | Python   | Shopping cart management with Redis/AlloyDB/Spanner |
| **Checkout**        | Go       | Orchestrates the checkout process                   |
| **Shipping**        | Go       | Handles shipping quotes and order shipments         |
| **Payment**         | Node.js  | Processes payment transactions                      |
| **Currency**        | Node.js  | Currency conversion service                         |
| **Email**           | Python   | Sends order confirmation emails                     |
| **Ad**              | Python   | Contextual advertisement service                    |
| **Recommendation**  | Python   | Product recommendation engine                       |

### AI-Powered Services

| Service                | Language | Description                                                |
| ---------------------- | -------- | ---------------------------------------------------------- |
| **Chatbot**            | Python   | AI-powered customer support chatbot with RAG               |
| **Shopping Assistant** | Python   | Multimodal LLM service for interior design recommendations |
| **PEAU Agent**         | Python   | AI agent for product exploration and assistance            |
| **Try-On**             | Python   | Virtual try-on service for products                        |
| **Video Generation**   | Python   | AI-generated product videos                                |
| **MCP Service**        | Python   | Model Context Protocol service                             |

### Supporting Components

- **Load Generator** - Locust-based traffic simulation tool
- **OpenTelemetry Collector** - Telemetry aggregation and export
- **Datadog Agent** - Infrastructure and application monitoring

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) or [Minikube](https://minikube.sigs.k8s.io/) or [Kind](https://kind.sigs.k8s.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Skaffold 2.0.2+](https://skaffold.dev/docs/install/)

### Local Development

1. **Clone the repository**

   ```bash
   git clone <your-repo-url>
   cd v-commerce/
   ```

2. **Start a local Kubernetes cluster**

   **Option A: Minikube**

   ```bash
   minikube start --cpus=4 --memory 4096 --disk-size 32g
   ```

   **Option B: Docker Desktop**

   - Enable Kubernetes in Preferences
   - Set CPUs to at least 3, Memory to at least 6.0 GiB
   - Set disk space to at least 32 GB

   **Option C: Kind**

   ```bash
   kind create cluster
   ```

3. **Deploy the application**

   ```bash
   skaffold run
   ```

   ⏱️ First deployment takes ~20 minutes (builds all Docker images)

4. **Port forward to access the frontend**

   ```bash
   kubectl port-forward deployment/frontend 8080:8080
   ```

5. **Access the application**
   - Open your browser to `http://localhost:8080`

### Development Mode

For automatic rebuilds during development:

```bash
skaffold dev
```

### Cleanup

Remove all deployed resources:

```bash
skaffold delete
```

## 📦 Deployment Options

v-commerce supports multiple deployment methods:

### 1. Skaffold (Development)

Best for local development and testing. See [Development Guide](docs/development-guide.md).

### 2. Helm Chart

Production-ready Helm chart for Kubernetes deployments:

```bash
helm install v-commerce ./helm-chart
```

See [Helm Chart README](helm-chart/README.md) for details.

### 3. Kustomize

Flexible configuration management with Kustomize components:

```bash
kubectl apply -k kustomize/base
```

See [Kustomize README](kustomize/README.md) for available components.

### 4. Kubernetes Manifests

Direct Kubernetes YAML manifests:

```bash
kubectl apply -f kubernetes-manifests/
```

### 5. Terraform

Infrastructure as Code for GCP deployments:

```bash
cd terraform/
terraform init
terraform apply
```

See [Terraform README](terraform/README.md) for details.

## 🔍 Observability

v-commerce includes comprehensive observability with **Datadog** integration:

### Features

- **Distributed Tracing** - End-to-end request tracing across all services
- **LLM Observability** - Specialized monitoring for AI/LLM services
- **Custom Metrics** - Business and technical metrics
- **Dashboards** - Pre-configured Datadog dashboards
- **Detection Rules** - Automated detection of:
  - Hallucination detection
  - Prompt injection attempts
  - Cost-per-conversion anomalies
  - Response quality degradation
  - Predictive capacity alerts
- **SLOs & Incident Management** - Service level objectives and automated incident response

### Setup

1. Configure Datadog credentials:

   ```bash
   cp docs/env.datadog.example .env.datadog
   # Edit .env.datadog with your DD_API_KEY and DD_SITE
   ```

2. Deploy with Datadog integration (see deployment manifests)

3. Generate traffic to trigger detection rules:
   ```bash
   source .env.datadog
   python3 scripts/traffic-generator.py --base-url http://localhost:8080
   ```

See the [plan document](.cursor/plans/datadog_llm_observability_hackathon_e7fcc76b.plan.md) for detailed observability implementation.

## 📁 Project Structure

```
v-commerce/
├── src/                    # Source code for all microservices
│   ├── frontend/          # Go web frontend
│   ├── chatbotservice/    # AI chatbot service
│   ├── shoppingassistantservice/  # Shopping assistant
│   └── ...                # Other services
├── kubernetes-manifests/  # Kubernetes YAML manifests
├── helm-chart/            # Helm chart for deployment
├── kustomize/             # Kustomize configurations
├── terraform/             # Infrastructure as Code
├── scripts/               # Utility scripts
│   ├── traffic-generator.py
│   ├── create-datadog-dashboard.py
│   └── create-datadog-monitors.py
├── docs/                  # Documentation
├── protos/                # Protocol buffer definitions
└── datadog-exports/       # Datadog configuration exports
```

## 📚 Documentation

- [Development Guide](docs/development-guide.md) - Building and running locally
- [Services README](Services%20README.md) - Detailed service documentation
- [Adding a New Microservice](docs/adding-new-microservice.md) - Extension guide
- [Product Requirements](docs/product-requirements.md) - Project requirements
- [Runbooks](docs/RUNBOOKS.md) - Operational runbooks
- [Incident Management](docs/INCIDENT_MANAGEMENT.md) - Incident response procedures

## 🛠️ Technology Stack

### Languages & Frameworks

- **Go** - Frontend, Product Catalog, Checkout, Shipping services
- **Python** - Cart, Email, Ad, Recommendation, AI services
- **Node.js** - Payment, Currency services

### Infrastructure

- **Kubernetes** - Container orchestration
- **Docker** - Containerization
- **gRPC** - Inter-service communication
- **Protocol Buffers** - Service contracts

### Observability

- **Datadog** - APM, metrics, logs, traces
- **OpenTelemetry** - Telemetry collection
- **ddtrace** - Python/Node.js tracing
- **OTLP** - Go service tracing

### AI/ML

- **Google Gemini** - LLM models for AI services
- **Vector Search** - AlloyDB for product embeddings
- **RAG** - Retrieval Augmented Generation

## 🎮 User Journey

The default user journey demonstrates core e-commerce functionality:

1. **Browse Products** - View the product catalog
2. **Add to Cart** - Select items and add them to the cart
3. **Checkout** - Complete the order with pre-populated form data
4. **Order Confirmation** - Receive order confirmation

## 🤝 Contributing

v-commerce follows specific product requirements to maintain simplicity and accessibility:

1. **Preserve the golden user journey** - Must run on a `kind` Kubernetes cluster
2. **Preserve demo simplicity** - Keep the primary user journey straightforward
3. **Preserve quickstart simplicity** - Don't add unnecessary complexity

See [Product Requirements](docs/product-requirements.md) for details.

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🔗 Related Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Skaffold Documentation](https://skaffold.dev/docs/)
- [Datadog Documentation](https://docs.datadoghq.com/)
- [Google Cloud Run](https://cloud.google.com/run)

---

**Note**: v-commerce is designed to be cloud-agnostic and can run on any Kubernetes cluster, including local development environments like `kind`, `minikube`, or Docker Desktop.
