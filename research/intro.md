# 🛡️ AI Guardian v3.0.0: Analytics Lab

This digital research book provides the **Scientific Proof** behind the **AI Guardian v3.0.0** security engine. 

---

### 🏗️ Technical Pipeline: High-Fidelity Overview
AI Guardian employs a high-performance, asynchronous orchestrator that processes every notification through 10 distinct architectural layers.

```mermaid
graph LR
    %% Style Definitions
    classDef ingest fill:#e3f2fd,stroke:#1565c0,color:#0d47a1
    classDef intel fill:#fff3e0,stroke:#e65100,color:#bf360c
    classDef logic fill:#f3e5f5,stroke:#7b1fa2,color:#4a148c
    classDef storage fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20

    %% Pipeline Flow
    Input["📱 Notification In"]:::ingest --> API["🚀 FastAPI Orchestrator"]:::ingest
    
    subgraph "Stage 1: Signal Discovery"
        API --> URL["🔍 URL Scraper"]:::intel
        API --> Intent["💬 Intent NLP"]:::intel
        API --> Bench["📊 Heuristic Baseline"]:::intel
    end

    URL & Intent & Bench --> TI["🧠 Threat Intel & RAG"]:::intel
    
    subgraph "Stage 2: Deep Reasoning"
        TI --> Gate{AI Gating Router}:::logic
        Gate -- "Flash" --> Groq["⚡ Groq: Llama-3"]:::logic
        Gate -- "Complex" --> Gemini["🪐 Google Gemini"]:::logic
    end

    Groq & Gemini --> ABE["🛡️ Adaptive Behavioral Engine"]:::logic
    
    subgraph "Stage 3: Persistence & Resilience"
        ABE --> Redis["📡 Redis Event Bus"]:::storage
        Redis --> PG["📊 Analytics (Postgres)"]:::storage
        Redis --> Alerts["🔔 Alert Manager"]:::storage
        Redis --> Heal["♻️ Self-Healing Engine"]:::storage
    end

    Alerts --> Verdict["✅ Secure Scan Verdict"]:::ingest
```

---

While the main dashboard provides real-time protection, this lab focuses on the **empirical evidence** gathered during our **510-scenario** Grand Scale comparative benchmark.

## Core Research Objectives
- **Validate Accuracy**: Does AI Guardian consistently beat industry standards (GSB/Truecaller)?
- **Assess Recall**: How effectively do we catch specific scam categories (Banking, Crypto, Indian SMS)?
- **Analyze Performance**: What is the latency cost of our 10-layer "Deep Reasoning" pipeline?

---

### 📊 Research Data Visualization

#### 1. Overall Performance Delta
![Overall Performance](overall_performance.png)

#### 2. Detection Accuracy by Category
![Category Accuracy](category_accuracy.png)

#### 3. Pipeline Latency Distribution
![Latency Distribution](latency_distribution.png)

---

### 🔍 Technical Analysis: Why AI Guardian Wins

The **+80% Accuracy** and **+85% Recall** gaps shown above are driven by three fundamental innovations:

1. **Zero-Day Resilience (RAG Layer)**
   * **Problem**: Industry tools (GSB/Truecaller) rely on "Reports." If a scam link was created 10 minutes ago, it won't be in their database.
   * **Solution**: AI Guardian uses **Semantic RAG**. Even if a URL is new, if the *Message Intent* matches a known scam pattern in our database, we flag it instantly.

2. **Semantic Intent vs. Keyword Matching**
   * **Problem**: Scammers bypass filters by misspelling words (e.g., "B@nk" instead of "Bank").
   * **Solution**: Our **NLP Signal Discovery** understands the "Vibe" and "Pressure" of the message regardless of typos. We detect the *act* of phishing, not just the keywords.

3. **Behavioral Reasoning (The LLM Gate)**
   * **Problem**: Traditional heuristics are static.
   * **Solution**: Our **Gated LLM** (Groq/Gemini) performs "Chain of Thought" reasoning. It asks: *"Why would a bank send a link from a .biz domain at 2 AM with a 5-minute deadline?"* This logic is impossible for traditional industry baselines to replicate.

---

### Navigation
Use the sidebar to explore the **Analytics Lab** notebook for the full Python source of these visualizations.

*Developed for the Idea Spark Hackathon 2026*
