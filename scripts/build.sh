#!/bin/bash
set -e

echo "Building counter-agent microservices..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration
REGISTRY=${REGISTRY:-"ghcr.io/JCTekDev"}
TAG=${TAG:-"latest"}

echo "Registry: $REGISTRY"
echo "Tag: $TAG"

# Build counter-agent AI Agent
echo "Building counter-agent AI Agent..."
docker build -t "$REGISTRY/counter-agent:$TAG" "$PROJECT_ROOT/services/counter-agent"

# Build WAHA Integrator
echo "Building WAHA Integrator..."
docker build -t "$REGISTRY/waha-integrator:$TAG" "$PROJECT_ROOT/services/waha-integrator"

echo "Build completed successfully!"

# Optional: Push to registry if PUSH=true
if [ "$PUSH" = "true" ]; then
    echo "Pushing images to registry..."
    docker push "$REGISTRY/counter-agent:$TAG"
    docker push "$REGISTRY/waha-integrator:$TAG"
    echo "Images pushed successfully!"
fi

echo ""
echo "Built images:"
echo "  - $REGISTRY/counter-agent:$TAG"
echo "  - $REGISTRY/waha-integrator:$TAG"
echo ""
echo "Usage examples:"
echo "  # Build only:"
echo "  ./scripts/build.sh"
echo ""
echo "  # Build and push:"
echo "  PUSH=true ./scripts/build.sh"
echo ""
echo "  # Custom registry and tag:"
echo "  REGISTRY=your-registry.com TAG=v1.0.0 ./scripts/build.sh"