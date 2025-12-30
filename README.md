# v-commerce

A cloud-native microservices demo application showcasing modern e-commerce patterns with AI-powered features, built for Kubernetes and cloud-native environments. **Fully instrumented with Datadog for comprehensive observability, LLM monitoring, and production-ready monitoring capabilities.**

## 🎯 Purpose

v-commerce is designed to demonstrate:

- **Microservices architecture patterns** - Distributed system design with multiple services
- **Kubernetes deployments and orchestration** - Production-ready containerized applications
- **Cloud-native application development** - Best practices for modern distributed systems
- **Datadog Observability** - **Full-stack observability with APM, LLM monitoring, custom metrics, dashboards, and automated incident management**
- **AI/LLM integration** - Multiple AI-powered services using Gemini models with specialized Datadog LLM observability

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
- **OpenTelemetry Collector** - Telemetry aggregation and export to Datadog
- **Datadog Agent** - Infrastructure and application monitoring (agentless mode supported)
- **Datadog Observability Stack** - Complete observability pipeline with traces, metrics, logs, and LLM-specific monitoring

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) or [Minikube](https://minikube.sigs.k8s.io/) or [Kind](https://kind.sigs.k8s.io/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Skaffold 2.0.2+](https://skaffold.dev/docs/install/)
- **Datadog Account** (optional but recommended) - For full observability features. Get your [DD_API_KEY](https://app.datadoghq.com/organization-settings/api-keys) and configure `DD_SITE`.

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

### Enable Datadog Observability (Recommended)

To enable full observability with Datadog:

1. **Get your Datadog credentials:**

   - Sign up at [datadoghq.com](https://www.datadoghq.com/) (free trial available)
   - Get your API key from [Organization Settings](https://app.datadoghq.com/organization-settings/api-keys)
   - Note your Datadog site (e.g., `datadoghq.com`, `us3.datadoghq.com`, `us5.datadoghq.com`)

2. **Configure environment variables:**

   ```bash
   cp docs/env.datadog.example .env.datadog
   # Edit .env.datadog and add:
   # DD_API_KEY=your_api_key_here
   # DD_SITE=datadoghq.com
   ```

3. **Deploy with Datadog integration:**

   - The application is pre-instrumented with Datadog tracing
   - Services automatically send telemetry to Datadog when credentials are configured
   - View traces, metrics, and logs in your Datadog dashboard

4. **Generate traffic and view observability:**
   ```bash
   source .env.datadog
   python3 scripts/traffic-generator.py --base-url http://localhost:8080
   ```
   Then check your Datadog dashboard for real-time traces, metrics, and LLM observability data.

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

## 🔍 Datadog Observability

**v-commerce is fully instrumented with Datadog** for production-grade observability, making it an ideal platform for learning and demonstrating modern observability practices.

### Why Datadog?

v-commerce leverages Datadog's comprehensive observability platform to provide:

- **Unified Observability** - Traces, metrics, logs, and LLM data in one platform
- **Zero-Instrumentation Overhead** - Automatic instrumentation with minimal code changes
- **LLM-Specific Monitoring** - Specialized tracking for AI/LLM services
- **Production-Ready** - Enterprise-grade monitoring suitable for real-world deployments

### Core Observability Features

#### 📊 Distributed Tracing

- **End-to-end request tracing** across all microservices (Go, Python, Node.js)
- **Service dependency mapping** - Visualize how services interact
- **Performance insights** - Identify bottlenecks and slow requests
- **Error tracking** - Automatic error detection and alerting

#### 🤖 LLM Observability

v-commerce includes **specialized Datadog LLM observability** for AI-powered services:

- **Token usage tracking** - Monitor input/output tokens per request
- **Cost monitoring** - Track LLM API costs per service and operation
- **Latency metrics** - Measure LLM response times
- **Quality metrics** - Track response quality and user satisfaction
- **Model performance** - Compare different LLM models and configurations

#### 📈 Custom Metrics & Dashboards

- **Business metrics** - Orders, cart additions, checkout conversions
- **Technical metrics** - Request rates, error rates, latency percentiles
- **Pre-configured dashboards** - Ready-to-use Datadog dashboards for:
  - Service health overview
  - LLM performance and costs
  - AI insights and recommendations
  - Infrastructure metrics

#### 🚨 Automated Detection Rules

Four specialized detection rules automatically identify issues:

1. **Prompt Injection Detection** - Identifies adversarial prompts attempting to manipulate AI services
2. **Interactions-Per-Conversion Anomaly** - Alerts when too many AI chat interactions are needed per cart conversion
3. **Response Quality Degradation** - Monitors for declining response quality over time
4. **Predictive Capacity Alert** - Warns of sustained high load that may impact capacity

#### 🎯 SLOs & Incident Management

- **Service Level Objectives** - Define and track SLOs for critical services
- **Automated incident management** - Datadog automatically creates incidents from alerts
- **Runbooks integration** - Link operational runbooks to incidents
- **On-call management** - Integrate with PagerDuty, Slack, and other tools

### Instrumentation Details

#### Service Instrumentation

**Python Services** (Chatbot, Shopping Assistant, PEAU Agent, Cart, Email, Ad, Recommendation, Try-On, Video Generation, MCP Service):

- Instrumented with `ddtrace` library
- Automatic tracing of Flask/gRPC requests
- Custom LLM spans for Gemini API calls
- Custom metrics for token usage and costs

**Go Services** (Frontend, Product Catalog, Checkout, Shipping):

- Instrumented with OpenTelemetry (OTLP)
- Automatic gRPC and HTTP tracing
- Metrics exported to Datadog via OTLP collector

**Node.js Services** (Payment, Currency):

- Instrumented with `dd-trace-js`
- Automatic HTTP/gRPC tracing
- Custom business metrics

### Setup Instructions

#### 1. Get Datadog Credentials

1. Sign up for a [Datadog account](https://www.datadoghq.com/) (free 14-day trial)
2. Navigate to [Organization Settings > API Keys](https://app.datadoghq.com/organization-settings/api-keys)
3. Create a new API key or use an existing one
4. Note your Datadog site (check the URL: `app.datadoghq.com` = `datadoghq.com`, `us3.datadoghq.com` = `us3.datadoghq.com`, etc.)

#### 2. Configure Environment Variables

```bash
cp docs/env.datadog.example .env.datadog
```

Edit `.env.datadog`:

```bash
export DD_API_KEY=your_api_key_here
export DD_SITE=datadoghq.com  # or us3.datadoghq.com, us5.datadoghq.com, etc.
```

#### 3. Deploy with Datadog

The application is pre-configured to send telemetry to Datadog when credentials are available. Services automatically detect Datadog environment variables and start sending traces, metrics, and logs.

**For Kubernetes deployments:**

- Services use environment variables from secrets
- OpenTelemetry Collector aggregates and forwards telemetry to Datadog
- Datadog Agent (optional) provides infrastructure metrics

**Agentless Mode:**

- v-commerce supports Datadog's agentless mode
- Services send telemetry directly to Datadog APIs
- No Datadog Agent required in your cluster

#### 4. View Observability Data

1. **Access Datadog Dashboard:**

   - Go to [app.datadoghq.com](https://app.datadoghq.com/)
   - Navigate to **APM > Services** to see all instrumented services
   - Check **Dashboards** for pre-configured v-commerce dashboards

2. **Generate Traffic:**

   ```bash
   source .env.datadog
   python3 scripts/traffic-generator.py --base-url http://localhost:8080
   ```

3. **Explore Observability:**
   - **Traces**: APM > Traces - See end-to-end request flows
   - **Services**: APM > Services - Service health and performance
   - **LLM Observability**: Navigate to LLM-specific views for AI service metrics
   - **Dashboards**: Custom dashboards showing business and technical metrics
   - **Monitors**: Detection rules and alerts

### Datadog Configuration Files

v-commerce includes pre-configured Datadog resources:

- **`datadog-exports/dashboards/`** - Pre-built Datadog dashboards
- **`datadog-exports/detection-rules.json`** - LLM detection rule configurations
- **`datadog-exports/incident-rules.json`** - Incident management rules
- **`datadog-exports/created-slos.json`** - Service level objectives

Import these into your Datadog account using the provided scripts:

```bash
python3 scripts/create-datadog-dashboard.py
python3 scripts/create-datadog-monitors.py
python3 scripts/create-datadog-slos.py
```

### Advanced Features

- **Custom Metrics** - Services emit custom business metrics (orders, cart size, etc.)
- **Log Correlation** - Logs automatically correlated with traces
- **Error Tracking** - Automatic error detection and grouping
- **Profiling** - Continuous profiling for performance optimization (optional)
- **Synthetic Monitoring** - End-to-end testing from Datadog (optional)

### Learn More

- See the [detailed implementation plan](.cursor/plans/datadog_llm_observability_hackathon_e7fcc76b.plan.md) for technical details
- [Datadog APM Documentation](https://docs.datadoghq.com/tracing/)
- [Datadog LLM Observability](https://docs.datadoghq.com/llm_observability/)
- [Datadog Kubernetes Integration](https://docs.datadoghq.com/agent/kubernetes/)

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
│   ├── traffic-generator.py        # Generate traffic to trigger Datadog detection rules
│   ├── create-datadog-dashboard.py  # Deploy Datadog dashboards
│   ├── create-datadog-monitors.py   # Deploy Datadog monitors and detection rules
│   └── create-datadog-slos.py       # Deploy Datadog SLOs
├── docs/                  # Documentation
├── protos/                # Protocol buffer definitions
└── datadog-exports/       # Datadog configuration exports (dashboards, SLOs, detection rules)
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

### Observability (Powered by Datadog)

- **Datadog APM** - Full distributed tracing across all services
- **Datadog LLM Observability** - Specialized monitoring for AI/LLM services with token tracking, cost monitoring, and quality metrics
- **Datadog Metrics** - Custom business and technical metrics with pre-configured dashboards
- **Datadog Logs** - Centralized log aggregation with trace correlation
- **Datadog Detection Rules** - Automated detection of prompt injection, cost anomalies, and quality issues
- **Datadog SLOs & Incident Management** - Service level objectives and automated incident response
- **OpenTelemetry** - Telemetry collection and export to Datadog
- **ddtrace** - Python/Node.js automatic instrumentation
- **OTLP** - Go service tracing via OpenTelemetry Protocol

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
- **[Datadog Documentation](https://docs.datadoghq.com/)** - Comprehensive observability platform
- **[Datadog APM](https://docs.datadoghq.com/tracing/)** - Distributed tracing guide
- **[Datadog LLM Observability](https://docs.datadoghq.com/llm_observability/)** - AI/LLM monitoring
- **[Datadog Kubernetes Integration](https://docs.datadoghq.com/agent/kubernetes/)** - K8s monitoring setup
- [Google Cloud Run](https://cloud.google.com/run)

---

**Note**: v-commerce is designed to be cloud-agnostic and can run on any Kubernetes cluster, including local development environments like `kind`, `minikube`, or Docker Desktop.
