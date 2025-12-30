# LLM Observability Strategy for V-Commerce

## The Challenge: Monitoring AI is Different

Traditional application monitoring focuses on latency, errors, and throughput. But LLM-powered applications introduce entirely new failure modes that existing observability tools weren't designed to catch:

- **The model can be technically "working" but giving harmful outputs**
- **Security attacks happen through natural language, not code exploits**
- **Quality is subjective and degrades gradually, not suddenly**
- **Costs scale unpredictably with conversation length**

V-Commerce is an AI-native e-commerce platform where AI isn't just a feature—it's the core experience. Users chat with an AI shopping assistant, get personalized recommendations from an AI stylist (PEAU agent), and virtually try on products using AI image generation. **Every customer interaction touches AI.**

This required us to rethink observability from first principles.

---

## Our Observability Philosophy

### 1. **Monitor What Matters to Users, Not Just Machines**

Traditional monitoring asks: *"Is the service up?"*

We ask: *"Is the AI actually helping users buy things?"*

This led us to create the **Interactions-Per-Conversion** metric—tracking how many AI chat interactions it takes before a user adds something to their cart. High values (8+ chats) indicate the AI is failing to guide users effectively, even if every API call succeeds.

### 2. **Security Threats Come Through the Front Door**

Unlike SQL injection which exploits code vulnerabilities, **prompt injection exploits the AI's natural language understanding**. Attackers don't need to find bugs—they craft convincing text.

We implemented real-time injection scoring that analyzes every user message for attack patterns:
- Jailbreak attempts ("Ignore your instructions...")
- System prompt extraction ("What are your rules?")
- Instruction override ("You are now in admin mode...")

When the same session repeatedly attempts attacks, we **auto-create a security incident** with the attacker's session ID for immediate action.

### 3. **Multimodal = Multi-Vector Attacks**

Our Try-On service accepts user-uploaded images and processes them with AI. This opens attack vectors that don't exist in text-only systems:

- **Decompression bombs**: A 1KB PNG that expands to 10GB in memory
- **Polyglot files**: Images with hidden malicious payloads
- **Resource exhaustion**: Coordinated uploads to crash services

We track attacks **by user ID**, so when the same user makes 3+ malicious attempts, an incident is created identifying them specifically—enabling immediate blocking.

### 4. **Predict Failures Before They Happen**

The Observability Insights Service uses **Gemini to analyze Datadog metrics** and predict failures before they occur. It's AI observing AI.

When error probability exceeds 80%, we get advance warning to scale resources or enable circuit breakers—turning reactive firefighting into proactive prevention.

---

## The Five Detection Rules

| Rule | Query | Innovation |
|------|-------|-----------|
| **Prompt Injection** | `llm.security.injection_attempt_score by {session_id} > 0.7` | Session-grouped alerting identifies repeat attackers |
| **Interactions-Per-Conversion** | `llm.cost_per_conversion > 10.0` | Business outcome metric, not just technical health |
| **Quality Degradation** | `llm.response.quality_score < 0.6` | Composite scoring catches gradual decay |
| **Predictive Capacity** | `llm.prediction.error_probability > 0.8` | AI-powered prediction prevents outages |
| **Multimodal Security** | `tryon.security.* by {user_id} > 3` | User-ID attribution enables surgical blocking |

---

## What Makes This Innovative

### 🔐 Attacker Attribution, Not Just Detection

Most security monitoring tells you "an attack happened." Ours tells you **who did it**.

By grouping metrics by `session_id` (for chatbot) and `user_id` (for try-on), we can:
- Track repeat offenders across time
- Auto-create incidents with attacker identity
- Enable immediate, targeted blocking
- Build forensic trails for investigation

### 📊 Business Metrics as Observability Signals

We treat "interactions per conversion" as a first-class metric alongside latency and error rate. When users need 10+ AI interactions to add something to cart, that's a failure—even if every API returns 200 OK.

This connects engineering observability to business outcomes.

### 🤖 AI Observing AI

The Observability Insights Service uses Gemini to:
- Analyze metric patterns across services
- Predict failures 2 hours in advance
- Generate root cause analysis automatically
- Recommend specific remediation actions

This creates a feedback loop where AI both serves customers and monitors itself.

### 🖼️ Multimodal Security as First-Class Concern

Image-based attacks are a blind spot in most observability strategies. We instrumented the Try-On service with:
- Pillow's decompression bomb limits
- Invalid image detection
- Per-user attack counting
- Automatic incident creation

---

## Incident Auto-Generation

Two monitors auto-create incidents with full context:

| Monitor | Incident Handle | Attacker Tracking |
|---------|-----------------|-------------------|
| Prompt Injection | `@incident-prompt-injection` | `{{session_id.name}}` |
| Multimodal Attack | `@incident-multimodal` | `{{user_id.name}}` |

Both incidents include:
- Attack timeline and details
- Attacker identification
- Impact assessment
- Immediate action checklist

---

## Metrics Reference

| Metric | Service | Description |
|--------|---------|-------------|
| `llm.security.injection_attempt_score` | chatbotservice | Prompt injection detection score (0-1) |
| `llm.cost_per_conversion` | chatbotservice | LLM interactions per cart add |
| `llm.response.quality_score` | chatbotservice | Response quality score (0-1) |
| `llm.prediction.error_probability` | observability-insights | AI-predicted failure probability (0-1) |
| `tryon.security.decompression_bomb` | tryonservice | Decompression bomb attack count |
| `tryon.security.invalid_image` | tryonservice | Invalid/malicious image count |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     V-Commerce Platform                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │   Chatbot   │    │    PEAU     │    │   Try-On    │         │
│   │   Service   │    │    Agent    │    │   Service   │         │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│          │                  │                   │                 │
│          │ LLM Metrics      │ LLM Metrics       │ Security       │
│          │ - injection_score│ - quality_score   │ Metrics        │
│          │ - quality_score  │ - token_usage     │ - decompression│
│          │ - cost_per_conv. │                   │ - invalid_image│
│          │                  │                   │                 │
│          ▼                  ▼                   ▼                 │
│   ┌─────────────────────────────────────────────────────────────┐│
│   │                    Datadog Agent                             ││
│   │              (DogStatsD + APM Traces)                       ││
│   └─────────────────────────────────────────────────────────────┘│
│                              │                                    │
└──────────────────────────────┼────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Datadog                                  │
├─────────────────────────────────────────────────────────────────┤
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│   │  Monitors   │    │  Dashboard  │    │  Incidents  │         │
│   │  (5 Rules)  │───▶│   (LLM Obs) │    │  (Auto-Gen) │         │
│   └──────┬──────┘    └─────────────┘    └──────▲──────┘         │
│          │                                      │                 │
│          └──────────────────────────────────────┘                │
│                    Alert → Incident                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaway

**LLM observability isn't just traditional APM with more metrics—it requires rethinking what "healthy" means when your application's behavior is probabilistic, your security threats are linguistic, and your users' success depends on AI judgment.**

This implementation demonstrates how to build observability that:
- Catches attacks by who, not just what
- Measures business outcomes, not just technical health
- Predicts failures before they impact users
- Treats multimodal AI as a first-class security concern
