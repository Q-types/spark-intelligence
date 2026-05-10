#!/usr/bin/env python3
"""
DevOps & Infrastructure Benchmark
Tests: Dockerfile Optimization, CI/CD Pipeline, Kubernetes Manifests, Monitoring, IaC

Run: python benchmarks/solutions/devops_benchmark.py
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


# =============================================================================
# Problem 1: Dockerfile Optimization (Easy)
# =============================================================================

ORIGINAL_DOCKERFILE = """FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN python -m pytest
RUN pip install gunicorn
CMD ["gunicorn", "app:app"]"""


OPTIMIZED_DOCKERFILE = """# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run tests in build stage
RUN pip install pytest && python -m pytest && pip uninstall -y pytest

# Production stage
FROM python:3.11-slim AS production

WORKDIR /app

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy only necessary files from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app .

# Install production server
RUN pip install --no-cache-dir gunicorn

# Set ownership and switch to non-root user
RUN chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app:app"]
"""


class DockerfileAnalyzer:
    """Analyzes Dockerfile for optimization criteria."""

    def analyze(self, dockerfile: str) -> Dict[str, Any]:
        """Analyze dockerfile and return metrics."""
        lines = dockerfile.strip().split('\n')

        return {
            "multi_stage": self._has_multi_stage(dockerfile),
            "slim_base": self._uses_slim_base(dockerfile),
            "layer_caching": self._has_layer_caching(dockerfile),
            "non_root_user": self._has_non_root_user(dockerfile),
            "health_check": self._has_health_check(dockerfile),
            "no_cache": self._uses_no_cache(dockerfile),
            "test_separation": self._has_test_separation(dockerfile),
            "line_count": len(lines)
        }

    def _has_multi_stage(self, dockerfile: str) -> bool:
        """Check for multi-stage build."""
        return dockerfile.count('FROM ') >= 2 and ' AS ' in dockerfile

    def _uses_slim_base(self, dockerfile: str) -> bool:
        """Check for slim or alpine base image."""
        return 'slim' in dockerfile.lower() or 'alpine' in dockerfile.lower()

    def _has_layer_caching(self, dockerfile: str) -> bool:
        """Check if requirements.txt is copied before code."""
        req_pos = dockerfile.find('requirements.txt')
        copy_all_pos = dockerfile.find('COPY . .')

        # If requirements is copied separately before COPY . .
        if 'COPY requirements.txt' in dockerfile:
            return True
        return False

    def _has_non_root_user(self, dockerfile: str) -> bool:
        """Check for USER instruction (non-root)."""
        return 'USER ' in dockerfile and 'USER root' not in dockerfile.lower()

    def _has_health_check(self, dockerfile: str) -> bool:
        """Check for HEALTHCHECK instruction."""
        return 'HEALTHCHECK' in dockerfile

    def _uses_no_cache(self, dockerfile: str) -> bool:
        """Check for --no-cache-dir in pip install."""
        return '--no-cache-dir' in dockerfile or '--no-cache' in dockerfile

    def _has_test_separation(self, dockerfile: str) -> bool:
        """Check if tests are run in build stage only."""
        # Tests should not be in production stage
        if 'AS production' in dockerfile or 'as production' in dockerfile:
            prod_start = dockerfile.lower().find('as production')
            prod_section = dockerfile[prod_start:]
            return 'pytest' not in prod_section.lower()
        return False


# =============================================================================
# Problem 2: CI/CD Pipeline Design (Medium)
# =============================================================================

GITHUB_ACTIONS_WORKFLOW = """name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
      fail-fast: false

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linting
        run: |
          pip install ruff
          ruff check .

      - name: Run tests with coverage
        run: |
          pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  security:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'

      - name: Run Bandit SAST
        run: |
          pip install bandit
          bandit -r app/ -f json -o bandit-report.json || true

      - name: Run dependency audit
        run: |
          pip install pip-audit
          pip-audit

  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    permissions:
      contents: read
      packages: write

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha
            type=ref,event=branch

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    runs-on: ubuntu-latest
    needs: build
    environment: staging

    steps:
      - name: Deploy to staging
        run: |
          echo "Deploying to staging..."
          # kubectl set image deployment/app app=${{ needs.build.outputs.image-tag }}

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    environment:
      name: production
      url: https://app.example.com

    steps:
      - name: Deploy to production
        run: |
          echo "Deploying to production..."
          # kubectl set image deployment/app app=${{ needs.build.outputs.image-tag }}

      - name: Verify deployment
        run: |
          echo "Verifying deployment health..."

      - name: Rollback on failure
        if: failure()
        run: |
          echo "Rolling back deployment..."
          # kubectl rollout undo deployment/app
"""


class CICDAnalyzer:
    """Analyzes CI/CD pipeline configuration."""

    def analyze(self, workflow: str) -> Dict[str, Any]:
        """Analyze workflow and return metrics."""
        return {
            "has_test_job": 'jobs:' in workflow and 'test:' in workflow,
            "has_matrix": 'matrix:' in workflow and 'python-version' in workflow,
            "has_security_scan": 'trivy' in workflow.lower() or 'bandit' in workflow.lower(),
            "has_sast": 'bandit' in workflow.lower() or 'semgrep' in workflow.lower(),
            "has_docker_build": 'docker/build-push-action' in workflow,
            "has_staging": 'staging' in workflow.lower(),
            "has_production": 'production' in workflow.lower(),
            "has_manual_approval": 'environment:' in workflow,
            "has_rollback": 'rollback' in workflow.lower(),
            "has_caching": 'cache' in workflow.lower(),
            "python_versions": self._extract_python_versions(workflow)
        }

    def _extract_python_versions(self, workflow: str) -> List[str]:
        """Extract Python versions from matrix."""
        match = re.search(r"python-version:\s*\[(.*?)\]", workflow)
        if match:
            versions = match.group(1)
            return [v.strip().strip("'\"") for v in versions.split(',')]
        return []


# =============================================================================
# Problem 3: Kubernetes Deployment Manifest (Medium)
# =============================================================================

K8S_MANIFESTS = """---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  APP_ENV: "production"
  LOG_LEVEL: "info"
  DATABASE_HOST: "postgres-service"

---
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: production
type: Opaque
stringData:
  DATABASE_PASSWORD: "${DATABASE_PASSWORD}"
  API_KEY: "${API_KEY}"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
  labels:
    app: web-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web-app
  template:
    metadata:
      labels:
        app: web-app
    spec:
      containers:
        - name: web-app
          image: ghcr.io/myorg/web-app:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: app-config
            - secretRef:
                name: app-secrets
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000

---
apiVersion: v1
kind: Service
metadata:
  name: web-app-service
  namespace: production
spec:
  selector:
    app: web-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-app-ingress
  namespace: production
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - app.example.com
      secretName: app-tls
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-app-service
                port:
                  number: 80

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-app-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
"""


class K8sAnalyzer:
    """Analyzes Kubernetes manifests."""

    def analyze(self, manifests: str) -> Dict[str, Any]:
        """Analyze manifests and return metrics."""
        return {
            "has_deployment": 'kind: Deployment' in manifests,
            "has_replicas": 'replicas:' in manifests,
            "has_resource_requests": 'requests:' in manifests and 'cpu:' in manifests,
            "has_resource_limits": 'limits:' in manifests,
            "has_liveness_probe": 'livenessProbe:' in manifests,
            "has_readiness_probe": 'readinessProbe:' in manifests,
            "has_hpa": 'HorizontalPodAutoscaler' in manifests,
            "has_configmap": 'kind: ConfigMap' in manifests,
            "has_secret": 'kind: Secret' in manifests,
            "has_service": 'kind: Service' in manifests,
            "has_ingress": 'kind: Ingress' in manifests,
            "has_security_context": 'securityContext:' in manifests,
            "has_non_root": 'runAsNonRoot: true' in manifests,
            "resource_count": manifests.count('kind:')
        }


# =============================================================================
# Problem 4: Monitoring and Alerting Setup (Hard)
# =============================================================================

PROMETHEUS_CONFIG = """global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - "/etc/prometheus/rules/*.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'web-app'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['web-app:8000']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
"""

ALERT_RULES = """groups:
  - name: web-app-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) /
          sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over last 5 minutes"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
          > 0.5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "95th percentile latency is {{ $value }}s"

      - alert: PodRestarts
        expr: |
          increase(kube_pod_container_status_restarts_total[1h]) > 3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod restarting frequently"
          description: "Pod {{ $labels.pod }} has restarted {{ $value }} times in the last hour"

      - alert: HighMemoryUsage
        expr: |
          container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Container {{ $labels.container }} is using {{ $value | humanizePercentage }} of memory limit"

      - alert: ServiceDown
        expr: up{job="web-app"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "{{ $labels.job }} is not responding"
"""

GRAFANA_DASHBOARD = """{
  "dashboard": {
    "title": "Web Application Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (method, status)",
            "legendFormat": "{{method}} - {{status}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~'5..'}[5m])) / sum(rate(http_requests_total[5m])) * 100"
          }
        ],
        "thresholds": "1,5",
        "colors": ["green", "yellow", "red"]
      },
      {
        "title": "Latency Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "sum(rate(http_request_duration_seconds_bucket[5m])) by (le)"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "container_memory_usage_bytes{container='web-app'}"
          }
        ]
      },
      {
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(container_cpu_usage_seconds_total{container='web-app'}[5m])"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}"""

SLO_DEFINITION = """# Service Level Objectives

## Availability SLO
- Target: 99.9% uptime
- Measurement: sum(up{job="web-app"}) / count(up{job="web-app"})
- Error Budget: 43.2 minutes per month

## Latency SLO
- Target: 95th percentile < 500ms
- Measurement: histogram_quantile(0.95, http_request_duration_seconds_bucket)
- Error Budget: 5% of requests can exceed target

## Error Rate SLO
- Target: < 1% error rate
- Measurement: sum(http_requests_total{status=~"5.."}) / sum(http_requests_total)
- Error Budget: 1% of requests can fail

## Throughput SLI
- Measurement: sum(rate(http_requests_total[5m]))
- Baseline: 1000 req/s
"""


class MonitoringAnalyzer:
    """Analyzes monitoring configuration."""

    def analyze(self, prometheus_config: str, alert_rules: str,
                grafana_dashboard: str, slo_definition: str) -> Dict[str, Any]:
        """Analyze monitoring setup."""
        return {
            # Prometheus
            "has_scrape_config": 'scrape_configs:' in prometheus_config,
            "has_alertmanager": 'alertmanagers:' in prometheus_config,
            "has_rule_files": 'rule_files:' in prometheus_config,

            # Alerts
            "has_error_rate_alert": 'HighErrorRate' in alert_rules,
            "has_latency_alert": 'HighLatency' in alert_rules,
            "has_pod_restart_alert": 'PodRestarts' in alert_rules or 'restarts' in alert_rules.lower(),
            "has_severity_labels": 'severity:' in alert_rules,
            "alert_count": alert_rules.count('- alert:'),

            # Dashboard
            "has_request_metrics": 'http_requests_total' in grafana_dashboard,
            "has_latency_metrics": 'duration' in grafana_dashboard.lower(),
            "has_resource_metrics": 'memory' in grafana_dashboard.lower() or 'cpu' in grafana_dashboard.lower(),
            "panel_count": grafana_dashboard.count('"title"'),

            # SLO
            "has_availability_slo": 'availability' in slo_definition.lower(),
            "has_latency_slo": 'latency' in slo_definition.lower(),
            "has_error_budget": 'error budget' in slo_definition.lower()
        }


# =============================================================================
# Problem 5: Infrastructure as Code (Hard)
# =============================================================================

TERRAFORM_CONFIG = """# main.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "terraform-state-bucket"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  cidr_block         = var.vpc_cidr
  availability_zones = var.availability_zones
  environment        = var.environment
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  cluster_name   = "${var.app_name}-cluster"
  vpc_id         = module.vpc.vpc_id
  subnet_ids     = module.vpc.private_subnet_ids
  container_port = var.container_port
  desired_count  = var.ecs_desired_count

  depends_on = [module.vpc]
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  identifier        = "${var.app_name}-db"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = var.db_instance_class
  allocated_storage = var.db_storage
  multi_az          = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  depends_on = [module.vpc]
}

# ElastiCache Module
module "elasticache" {
  source = "./modules/elasticache"

  cluster_id      = "${var.app_name}-cache"
  engine          = "redis"
  node_type       = var.cache_node_type
  num_cache_nodes = var.cache_nodes

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids

  depends_on = [module.vpc]
}

# ALB Module
module "alb" {
  source = "./modules/alb"

  name       = "${var.app_name}-alb"
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnet_ids

  target_group_arn = module.ecs.target_group_arn

  depends_on = [module.vpc, module.ecs]
}

# S3 for static assets
resource "aws_s3_bucket" "static_assets" {
  bucket = "${var.app_name}-static-assets"

  tags = {
    Name        = "${var.app_name}-static"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "static_assets" {
  bucket = aws_s3_bucket.static_assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/ecs/${var.app_name}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}
"""

TERRAFORM_VPC_MODULE = """# modules/vpc/main.tf
variable "cidr_block" {
  type = string
}

variable "availability_zones" {
  type = list(string)
}

variable "environment" {
  type = string
}

locals {
  public_subnets  = [for i, az in var.availability_zones : cidrsubnet(var.cidr_block, 4, i)]
  private_subnets = [for i, az in var.availability_zones : cidrsubnet(var.cidr_block, 4, i + 4)]
}

resource "aws_vpc" "main" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.environment}-vpc"
    Environment = var.environment
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.environment}-igw"
  }
}

resource "aws_subnet" "public" {
  count = length(var.availability_zones)

  vpc_id                  = aws_vpc.main.id
  cidr_block              = local.public_subnets[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.environment}-public-${count.index + 1}"
    Type = "public"
  }
}

resource "aws_subnet" "private" {
  count = length(var.availability_zones)

  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_subnets[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.environment}-private-${count.index + 1}"
    Type = "private"
  }
}

resource "aws_nat_gateway" "main" {
  count = length(var.availability_zones)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = {
    Name = "${var.environment}-nat-${count.index + 1}"
  }
}

resource "aws_eip" "nat" {
  count = length(var.availability_zones)

  domain = "vpc"

  tags = {
    Name = "${var.environment}-eip-${count.index + 1}"
  }
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}
"""


class TerraformAnalyzer:
    """Analyzes Terraform configuration."""

    def analyze(self, main_config: str, vpc_module: str) -> Dict[str, Any]:
        """Analyze Terraform config."""
        full_config = main_config + vpc_module

        return {
            "has_vpc": 'aws_vpc' in full_config or 'module "vpc"' in full_config,
            "has_public_subnets": 'public' in full_config and 'subnet' in full_config.lower(),
            "has_private_subnets": 'private' in full_config and 'subnet' in full_config.lower(),
            "has_ecs": 'ecs' in full_config.lower(),
            "has_alb": 'alb' in full_config.lower() or 'load_balancer' in full_config.lower(),
            "has_rds": 'rds' in full_config.lower() or 'aws_db' in full_config,
            "has_multi_az": 'multi_az' in full_config.lower() and 'true' in full_config,
            "has_elasticache": 'elasticache' in full_config.lower(),
            "has_s3": 'aws_s3_bucket' in full_config,
            "has_cloudwatch": 'cloudwatch' in full_config.lower(),
            "uses_modules": 'module "' in full_config,
            "has_backend": 'backend "' in full_config,
            "has_security_groups": 'security_group' in full_config.lower() or 'private_subnet' in full_config,
            "module_count": full_config.count('module "'),
            "resource_count": full_config.count('resource "')
        }


# =============================================================================
# Benchmark Runner
# =============================================================================

def run_tests() -> dict:
    """Run all benchmark tests and return results."""
    results = {
        "problems": [],
        "summary": {}
    }

    total_score = 0
    max_score = 0
    all_tests = []

    # Problem 1: Dockerfile Optimization (Easy - 100 points)
    print("\n" + "="*60)
    print("Problem 1: Dockerfile Optimization")
    print("="*60)

    problem1_tests = []
    problem1_passed = 0

    analyzer = DockerfileAnalyzer()
    metrics = analyzer.analyze(OPTIMIZED_DOCKERFILE)

    tests = [
        ("multi_stage_build", metrics["multi_stage"], "Uses multi-stage build"),
        ("slim_base_image", metrics["slim_base"], "Uses slim/alpine base"),
        ("layer_caching", metrics["layer_caching"], "Dependencies cached separately"),
        ("non_root_user", metrics["non_root_user"], "Runs as non-root user"),
        ("health_check", metrics["health_check"], "Has HEALTHCHECK instruction"),
        ("no_cache_pip", metrics["no_cache"], "Uses --no-cache-dir"),
        ("test_separation", metrics["test_separation"], "Tests not in production")
    ]

    for name, passed, description in tests:
        problem1_tests.append({
            "name": name,
            "passed": passed,
            "details": description
        })
        if passed:
            problem1_passed += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {description}")

    problem1_score = (problem1_passed / len(tests)) * 100
    results["problems"].append({
        "id": "ops_001",
        "title": "Dockerfile Optimization",
        "difficulty": "Easy",
        "pass_rate": problem1_passed / len(tests),
        "score": problem1_score,
        "tests": problem1_tests
    })
    total_score += problem1_score
    max_score += 100
    all_tests.extend(problem1_tests)

    # Problem 2: CI/CD Pipeline (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 2: CI/CD Pipeline Design")
    print("="*60)

    problem2_tests = []
    problem2_passed = 0

    analyzer = CICDAnalyzer()
    metrics = analyzer.analyze(GITHUB_ACTIONS_WORKFLOW)

    tests = [
        ("test_job", metrics["has_test_job"], "Has test job"),
        ("matrix_testing", metrics["has_matrix"] and len(metrics["python_versions"]) >= 3,
         f"Matrix testing: {metrics['python_versions']}"),
        ("security_scanning", metrics["has_security_scan"], "Has security scanning (Trivy)"),
        ("sast_scanning", metrics["has_sast"], "Has SAST scanning (Bandit)"),
        ("docker_build", metrics["has_docker_build"], "Builds Docker image"),
        ("staging_deploy", metrics["has_staging"], "Deploys to staging"),
        ("production_deploy", metrics["has_production"], "Deploys to production"),
        ("manual_approval", metrics["has_manual_approval"], "Has manual approval"),
        ("rollback", metrics["has_rollback"], "Has rollback capability"),
        ("caching", metrics["has_caching"], "Uses caching")
    ]

    for name, passed, description in tests:
        problem2_tests.append({
            "name": name,
            "passed": passed,
            "details": description
        })
        if passed:
            problem2_passed += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {description}")

    problem2_score = (problem2_passed / len(tests)) * 150
    results["problems"].append({
        "id": "ops_002",
        "title": "CI/CD Pipeline Design",
        "difficulty": "Medium",
        "pass_rate": problem2_passed / len(tests),
        "score": problem2_score,
        "tests": problem2_tests
    })
    total_score += problem2_score
    max_score += 150
    all_tests.extend(problem2_tests)

    # Problem 3: Kubernetes Manifests (Medium - 150 points)
    print("\n" + "="*60)
    print("Problem 3: Kubernetes Deployment Manifest")
    print("="*60)

    problem3_tests = []
    problem3_passed = 0

    analyzer = K8sAnalyzer()
    metrics = analyzer.analyze(K8S_MANIFESTS)

    tests = [
        ("deployment", metrics["has_deployment"], "Has Deployment"),
        ("replicas", metrics["has_replicas"], "Has replicas configured"),
        ("resource_requests", metrics["has_resource_requests"], "Has resource requests"),
        ("resource_limits", metrics["has_resource_limits"], "Has resource limits"),
        ("liveness_probe", metrics["has_liveness_probe"], "Has liveness probe"),
        ("readiness_probe", metrics["has_readiness_probe"], "Has readiness probe"),
        ("hpa", metrics["has_hpa"], "Has HorizontalPodAutoscaler"),
        ("configmap", metrics["has_configmap"], "Has ConfigMap"),
        ("secret", metrics["has_secret"], "Has Secret"),
        ("service", metrics["has_service"], "Has Service"),
        ("ingress", metrics["has_ingress"], "Has Ingress"),
        ("security_context", metrics["has_non_root"], "Runs as non-root")
    ]

    for name, passed, description in tests:
        problem3_tests.append({
            "name": name,
            "passed": passed,
            "details": description
        })
        if passed:
            problem3_passed += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {description}")

    problem3_score = (problem3_passed / len(tests)) * 150
    results["problems"].append({
        "id": "ops_003",
        "title": "Kubernetes Deployment Manifest",
        "difficulty": "Medium",
        "pass_rate": problem3_passed / len(tests),
        "score": problem3_score,
        "tests": problem3_tests
    })
    total_score += problem3_score
    max_score += 150
    all_tests.extend(problem3_tests)

    # Problem 4: Monitoring Setup (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 4: Monitoring and Alerting Setup")
    print("="*60)

    problem4_tests = []
    problem4_passed = 0

    analyzer = MonitoringAnalyzer()
    metrics = analyzer.analyze(PROMETHEUS_CONFIG, ALERT_RULES, GRAFANA_DASHBOARD, SLO_DEFINITION)

    tests = [
        ("scrape_config", metrics["has_scrape_config"], "Has Prometheus scrape config"),
        ("alertmanager", metrics["has_alertmanager"], "Has Alertmanager integration"),
        ("error_rate_alert", metrics["has_error_rate_alert"], "Has error rate alert"),
        ("latency_alert", metrics["has_latency_alert"], "Has latency alert"),
        ("pod_restart_alert", metrics["has_pod_restart_alert"], "Has pod restart alert"),
        ("severity_labels", metrics["has_severity_labels"], "Has severity labels"),
        ("request_metrics", metrics["has_request_metrics"], "Dashboard has request metrics"),
        ("latency_metrics", metrics["has_latency_metrics"], "Dashboard has latency metrics"),
        ("resource_metrics", metrics["has_resource_metrics"], "Dashboard has resource metrics"),
        ("availability_slo", metrics["has_availability_slo"], "Has availability SLO"),
        ("latency_slo", metrics["has_latency_slo"], "Has latency SLO"),
        ("error_budget", metrics["has_error_budget"], "Has error budget defined")
    ]

    for name, passed, description in tests:
        problem4_tests.append({
            "name": name,
            "passed": passed,
            "details": description
        })
        if passed:
            problem4_passed += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {description}")

    problem4_score = (problem4_passed / len(tests)) * 200
    results["problems"].append({
        "id": "ops_004",
        "title": "Monitoring and Alerting Setup",
        "difficulty": "Hard",
        "pass_rate": problem4_passed / len(tests),
        "score": problem4_score,
        "tests": problem4_tests
    })
    total_score += problem4_score
    max_score += 200
    all_tests.extend(problem4_tests)

    # Problem 5: Infrastructure as Code (Hard - 200 points)
    print("\n" + "="*60)
    print("Problem 5: Infrastructure as Code")
    print("="*60)

    problem5_tests = []
    problem5_passed = 0

    analyzer = TerraformAnalyzer()
    metrics = analyzer.analyze(TERRAFORM_CONFIG, TERRAFORM_VPC_MODULE)

    tests = [
        ("vpc", metrics["has_vpc"], "Has VPC"),
        ("public_subnets", metrics["has_public_subnets"], "Has public subnets"),
        ("private_subnets", metrics["has_private_subnets"], "Has private subnets"),
        ("ecs", metrics["has_ecs"], "Has ECS Fargate"),
        ("alb", metrics["has_alb"], "Has Application Load Balancer"),
        ("rds", metrics["has_rds"], "Has RDS PostgreSQL"),
        ("multi_az", metrics["has_multi_az"], "Has Multi-AZ setup"),
        ("elasticache", metrics["has_elasticache"], "Has ElastiCache Redis"),
        ("s3", metrics["has_s3"], "Has S3 bucket"),
        ("cloudwatch", metrics["has_cloudwatch"], "Has CloudWatch logs"),
        ("uses_modules", metrics["uses_modules"], f"Uses modules ({metrics['module_count']} modules)"),
        ("backend", metrics["has_backend"], "Has remote backend")
    ]

    for name, passed, description in tests:
        problem5_tests.append({
            "name": name,
            "passed": passed,
            "details": description
        })
        if passed:
            problem5_passed += 1
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {description}")

    problem5_score = (problem5_passed / len(tests)) * 200
    results["problems"].append({
        "id": "ops_005",
        "title": "Infrastructure as Code",
        "difficulty": "Hard",
        "pass_rate": problem5_passed / len(tests),
        "score": problem5_score,
        "tests": problem5_tests
    })
    total_score += problem5_score
    max_score += 200
    all_tests.extend(problem5_tests)

    # Summary
    passed_tests = sum(1 for t in all_tests if t["passed"])
    total_tests = len(all_tests)

    results["summary"] = {
        "total_score": total_score,
        "max_score": max_score,
        "overall_percentage": (total_score / max_score) * 100 if max_score > 0 else 0,
        "tests_passed": passed_tests,
        "tests_total": total_tests,
        "pass_rate": passed_tests / total_tests if total_tests > 0 else 0
    }

    return results


def main():
    print("="*60)
    print("DEVOPS & INFRASTRUCTURE BENCHMARK")
    print("="*60)

    results = run_tests()

    # Print summary table
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"\n| Problem | Difficulty | Pass Rate | Score |")
    print(f"|---------|------------|-----------|-------|")
    for p in results["problems"]:
        print(f"| {p['id']} | {p['difficulty']} | {p['pass_rate']*100:.1f}% | {p['score']:.1f} |")

    print(f"\n**Overall Score: {results['summary']['overall_percentage']:.1f}% ({results['summary']['total_score']:.1f}/{results['summary']['max_score']:.1f})**")
    print(f"**Tests: {results['summary']['tests_passed']}/{results['summary']['tests_total']} passed**")

    # Save results
    output_path = "/tmp/devops_benchmark_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    main()
