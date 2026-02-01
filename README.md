# AI Customer Service

<!-- GitHub Actions Status Badges -->
[![ConvoHub CI/CD](https://github.com/JCTekDev/ai-customer-service/actions/workflows/convohub-cicd.yaml/badge.svg)](https://github.com/JCTekDev/ai-customer-service/actions/workflows/convohub-cicd.yaml)
[![Counter Agent CI/CD](https://github.com/JCTekDev/ai-customer-service/actions/workflows/counter-agent-cicd.yaml/badge.svg)](https://github.com/JCTekDev/ai-customer-service/actions/workflows/counter-agent-cicd.yaml)
[![Info Agent CI/CD](https://github.com/JCTekDev/ai-customer-service/actions/workflows/info-agent-cicd.yaml/badge.svg)](https://github.com/JCTekDev/ai-customer-service/actions/workflows/info-agent-cicd.yaml)
[![Marketing Agent CI/CD](https://github.com/JCTekDev/ai-customer-service/actions/workflows/marketing-agent-cicd.yaml/badge.svg)](https://github.com/JCTekDev/ai-customer-service/actions/workflows/marketing-agent-cicd.yaml)
[![WAHA Integrator CI/CD](https://github.com/JCTekDev/ai-customer-service/actions/workflows/waha-integrator-cicd.yaml/badge.svg)](https://github.com/JCTekDev/ai-customer-service/actions/workflows/waha-integrator-cicd.yaml)

AI Agents Legion to provide Customer Services
\n+## Services Overview
Short explanations of each service in this monorepo:

- **ConvoHub** (`services/convohub/`): LangGraph-based orchestration hub. A supervisor LLM routes user inputs to specialized tool agents (FAQ info agent, calendar scheduler). Exposes a WAHA-compatible webhook adapter.
- **Counter Agent** (`services/counter-agent/`): Lightweight FAQ / counter queries responder using LangChain prompt + simple AI service layer.
- **Info Agent** (`services/info-agent/`): Standalone FAQ microservice with conversation state and AI response logic (also embedded as a tool variant inside ConvoHub).
- **Finance Advisors** (`services/finance-advisors/`): Multi-agent / graph application providing financial advisory interactions; uses a LangGraph style runner with domain-specific agents.
- **Marketing Agent** (`services/marketing-agent/`): Rasa-based conversational marketing assistant (NLU, stories, rules, custom actions) for campaign or lead engagement.
- **WAHA Integrator** (`services/waha-integrator/`): Receives WhatsApp (WAHA) webhook events and forwards messages to internal AI services (historical integration path prior to embedding adapter inside ConvoHub).

Each service ships its own Dockerfile, environment sample (`.env.example`), and CI/CD workflow for independent build & deploy.




