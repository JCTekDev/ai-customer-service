#!/bin/bash
set -e

echo "Deploying counter-agent to Kubernetes..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
NAMESPACE=${NAMESPACE:-"ai-customer-service-dev"}
REGISTRY=${REGISTRY:-"ghcr.io/JCTekDev"}
TAG=${TAG:-"latest"}
CONTEXT=${CONTEXT:-""}

# Set kubectl context if specified
if [ -n "$CONTEXT" ]; then
    echo "🎯 Using kubectl context: $CONTEXT"
    kubectl config use-context "$CONTEXT"
fi

echo "Namespace: $NAMESPACE"
echo "Registry: $REGISTRY"
echo "Tag: $TAG"

# Create namespace if it doesn't exist
echo "Creating namespace '$NAMESPACE' if it doesn't exist..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Update image tags in manifests (if using kustomize)
cd "$PROJECT_ROOT/k8s"

# Create temporary kustomization with updated images
cat > kustomization-deploy.yaml << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  - counter-agent/
  - waha-integrator/

images:
  - name: counter-agent
    newName: $REGISTRY/counter-agent
    newTag: $TAG
  - name: waha-integrator
    newName: $REGISTRY/waha-integrator  
    newTag: $TAG

namespace: $NAMESPACE
EOF

# Deploy using kustomize
echo "Applying Kubernetes manifests..."
kubectl apply -k . -f kustomization-deploy.yaml

# Wait for deployments to be ready
echo "Waiting for deployments to be ready..."
kubectl rollout status deployment/counter-agent -n "$NAMESPACE" --timeout=300s
kubectl rollout status deployment/waha-integrator -n "$NAMESPACE" --timeout=300s

# Cleanup
rm -f kustomization-deploy.yaml

echo "Deployment completed successfully!"

# Show service information
echo ""
echo "Service Information:"
kubectl get pods,svc -n "$NAMESPACE"

echo ""
echo "Service URLs (if using port-forward):"
echo "  # counter-agent AI Agent:"
echo "  kubectl port-forward -n $NAMESPACE svc/counter-agent 8000:8000"
echo "  # Then access: http://localhost:8000"
echo ""
echo "  # WAHA Integrator:"  
echo "  kubectl port-forward -n $NAMESPACE svc/waha-integrator 8001:8001"
echo "  # Then access: http://localhost:8001"

echo ""
echo "Usage examples:"
echo "  # Deploy with defaults:"
echo "  ./scripts/deploy.sh"
echo ""
echo "  # Deploy to specific namespace:"
echo "  NAMESPACE=counter-agent-dev ./scripts/deploy.sh"
echo ""
echo "  # Deploy with custom images:"
echo "  REGISTRY=my-registry.com TAG=v1.0.0 ./scripts/deploy.sh"
echo ""
echo "  # Deploy to specific cluster:"
echo "  CONTEXT=my-cluster ./scripts/deploy.sh"