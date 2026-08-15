# Infrastructure Configuration

This directory contains container definitions and setup documentation for deploying the Multimodal Autonomous Customer Support Agent application.

## Structure

- `docker-compose.yml` (located in the project root) orchestrates the local services.
- `backend/Dockerfile` defines the container runtime for the FastAPI service.
- `frontend/Dockerfile` defines the Next.js production build using standalone output tracing.
- `/infra` serves as a placeholder for database initialization scripts, Nginx configurations, or Kubernetes manifests.
