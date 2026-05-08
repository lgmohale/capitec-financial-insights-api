# Kubernetes Deployment Reference

This folder contains a simple Kubernetes deployment reference for the FastAPI API container.

It deploys only the API service. PostgreSQL, Redis, and MinIO/S3 are expected to be external services and are passed into the container through environment variables.

## Files

- `namespace.yaml`: namespace for the API resources
- `configmap.yaml`: non-sensitive API configuration
- `secret.example.yaml`: example secret values with placeholders
- `deployment.yaml`: FastAPI API deployment
- `service.yaml`: internal ClusterIP service

## External Services

The API expects these services to already exist:

- PostgreSQL through `DATABASE_URL`
- Redis through `REDIS_URL`
- MinIO or S3 through the object storage environment variables

Do not commit real secret values. Copy `secret.example.yaml` and replace the placeholder values through your preferred secret-management process.

## Example Apply Order

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.example.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

Kubernetes is not required to run the project locally. Use Docker Compose for local development.
