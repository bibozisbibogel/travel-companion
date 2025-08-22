# Infrastructure and Deployment

## Infrastructure as Code
- **Tool:** Docker Compose 2.20+ with Terraform 1.6+ for cloud deployment
- **Location:** `infrastructure/` directory with separate dev/prod configurations
- **Approach:** Container-first with docker-compose for local development, Terraform for AWS ECS deployment

## Deployment Strategy
- **Strategy:** Blue-Green deployment with health checks and automated rollback
- **CI/CD Platform:** GitHub Actions with multi-stage pipeline
- **Pipeline Configuration:** `.github/workflows/` directory with separate build/test/deploy stages

## Environments
- **Development:** Local Docker containers with hot reload
- **Staging:** AWS ECS with production-like data but lower resources  
- **Production:** AWS ECS with multi-AZ deployment and auto-scaling

## Environment Promotion Flow
```
Development (Local) → Staging (AWS) → Production (AWS)
                ↓           ↓              ↓
              Feature    Integration    Release
              Testing      Testing       Testing
```

## Rollback Strategy
- **Primary Method:** Blue-Green deployment switch with health check validation
- **Trigger Conditions:** Failed health checks, error rate >5%, response time >30s
- **Recovery Time Objective:** <5 minutes for service restoration
