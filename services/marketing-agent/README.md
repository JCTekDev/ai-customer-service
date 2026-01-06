# Rasa Customer Support Agent

A flexible Rasa-based microservice tailored for ACME marketing agency. It handles preliminary client qualification, provides high-level service information, and drives prospects toward scheduling a strategy meeting.

## Features
- Spanish-language conversational agent
- Service qualification flows for: Social Media, Google Ads, Diseño Web, Diseño Gráfico, Publicidad Exterior
- Appointment scheduling stub with timezone awareness (Bogotá timezone)
- Price handling deflection toward meeting
- Fallback and out-of-scope redirection

## Structure
```
services/marketing-agent/
  actions/
    actions.py
  data/
    nlu.yml
    stories.yml
    rules.yml
  domain.yml
  config.yml
  endpoints.yml
  requirements.txt
  Dockerfile
```

## Quick Start (Local)
```bash
cd services/marketing-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
rasa train
# Run servers
rasa run --enable-api --port 8002 &
rasa run actions --port 5055 --debug &
```

Test conversation:
```bash
curl -X POST localhost:8002/webhooks/rest/webhook \
  -H 'Content-Type: application/json' \
  -d '{"sender":"test","message":"Hola"}'
```

## Docker
```bash
docker build -t marketing-agent:latest .
docker run -p 8002:8002 -p 5055:5055 marketing-agent:latest
```

## Customization
- Update training data in `data/` for new intents or flows.
- Extend `actions/actions.py` for calendar integration or CRM logging.
- Add entities and slot mappings in `domain.yml` for richer context.

## Deployment (Kubernetes Sketch)
Example manifest (adapt for your kustomize overlays):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: marketing-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: marketing-agent
  template:
    metadata:
      labels:
        app: marketing-agent
    spec:
      containers:
        - name: rasa
          image: ghcr.io/JCTekDev/marketing-agent:latest
          ports:
            - containerPort: 8002
            - containerPort: 5055
          env:
            - name: TZ
              value: America/Bogota
          readinessProbe:
            httpGet:
              path: /model
              port: 8002
            initialDelaySeconds: 10
            periodSeconds: 15
---
apiVersion: v1
kind: Service
metadata:
  name: marketing-agent
spec:
  selector:
    app: marketing-agent
  ports:
    - name: http
      port: 8002
      targetPort: 8002
    - name: actions
      port: 5055
      targetPort: 5055
```

## Next Steps
- Integrate real calendar API for availability
- Add entity extraction for precise date/time parsing
- Implement conversation tests in `tests/`
- Add CI pipeline for model training & image build

## License
Internal usage for J / ai-customer-service platform.
