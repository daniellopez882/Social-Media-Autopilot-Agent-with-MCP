# 🛸 SocialPilot: The Autonomous Media Engine
> **Agentic social media orchestration at scale. Built for the era of AI-native brands.**

SocialPilot is an enterprise-grade autonomous system that handles the entire lifecycle of social media marketing—from trend discovery to platform-native content generation, safety validation, and automated scheduling. 

![SocialPilot Dashboard](socialpilot_dashboard_mockup_1772870940932.png)

---

## ⚡ The Future of Distribution
Traditional social media management is manual, reactive, and fragmented. **SocialPilot** replaces the legacy workflow with a stateful, agentic engine that thinks like a CMO and executes like a Digital Native.

- **Proactive Intelligence**: Detects emerging cultural signals *before* they peak.
- **Brand Guardrails**: Autonomous ethics monitoring prevents PR crises in real-time.
- **Human-in-the-loop**: A seamless approval architecture for critical content decisions.
- **Compound Growth**: Cross-platform orchestration (X, LinkedIn, Meta) that learns from every interaction.

---

## 🏗️ Technical Architecture
SocialPilot leverages a **Stateful Graph** orchestration layer to coordinate a "Crew" of specialist agents across specific cognitive domains.

### 🧠 The Specialists
| Agent | Cognitive Domain | Intelligence Layer |
| :--- | :--- | :--- |
| **Orchestrator** | Master Routing & Supervisor | Claude 3.5 Sonnet |
| **TrendAnalyzer** | Pattern Recognition & Trend Spotting | GPT-4o |
| **ContentGenerator** | Creative Writing & Visual Arts | Claude 3.5 Sonnet |
| **SafetyOfficer** | Ethics, Risk & Compliance | GPT-4 |
| **Accountant** | Growth Narrative & ROI Extraction | GPT-4o |

---

## 🚀 Ignition Sequence

### 1. Synchronize Environment
```bash
cp .env.example .env
# Enable MOCK_MODE=true for rapid iteration without API costs.
```

### 2. Launch Control Center

**Backend Runtime (FastAPI)**:
```bash
py -m uvicorn app.main:app --reload
```

**Intelligence Dashboard (Glassmorphism UI)**:
```bash
py run_dashboard.py
```

---

## 📡 The Protocol (API)

### `POST /client/profile`
Synchronize a brand's DNA including tonality, audience psychographics, and safety constraints.

### `POST /run`
Trigger an autonomous cycle. Current mission types supported:
- `campaign`: Full E2E flow (Trend Detection → Content Creation → Safety Check → Scheduling).
- `engagement`: Autonomous DM and comment response loop with sentiment classification.
- `analytics`: Performance narrative generation and "Stop/Start" recommendations.

### `POST /approve/{id}`
The human bypass. Immediate authorization of high-priority content flagged for review.

---

## 🛠️ Stack
- **Orchestration**: `langgraph`
- **Agent Framework**: `crewai`
- **API Engine**: `fastapi`
- **Frontend**: Autonomous Glassmorphism Command Center
- **Intelligence**: OpenAI GPT-4o + Anthropic Claude 3.5

---

**Architected by**: Ismail Sajid — Agentic AI Engineer  
*"Autonomy without compromise."*
