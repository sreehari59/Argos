# 🚀 Agnes Deployment Guide

**Complete deployment instructions for production and demo environments**

---

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS 11+, or Windows 10+ with WSL2
- **Python**: 3.9 or higher
- **Node.js**: 16.x or higher
- **Memory**: 2GB RAM minimum, 4GB recommended
- **Storage**: 500MB free space

### Required Accounts
- **OpenRouter API**: Free tier account (https://openrouter.ai)
- **Domain** (optional): For production deployment
- **SSL Certificate** (optional): For HTTPS

---

## 🏃 Quick Start (Development)

### 1. Clone Repository
```bash
git clone <repository-url>
cd q-hack
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python3 -m venv ../venv
source ../venv/bin/activate  # On Windows: ..\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cat > ../.env << EOF
OPENROUTER_API_KEY=your_api_key_here
EOF

# Run data processing pipeline (one-time setup)
python ingredients.py
python enrichment.py
python roles.py
python graph.py
python recommendations.py
python llm_compliance.py
python quality_scoring.py

# Start API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Access Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 🐳 Docker Deployment

### Build Images

**Backend Dockerfile**
```dockerfile
# backend/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run data processing on build
RUN python ingredients.py && \
    python enrichment.py && \
    python roles.py && \
    python graph.py && \
    python recommendations.py && \
    python llm_compliance.py && \
    python quality_scoring.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile**
```dockerfile
# frontend/Dockerfile
FROM node:16-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf**
```nginx
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**docker-compose.yml**
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    container_name: agnes-backend
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    volumes:
      - ./db_new.sqlite:/app/db_new.sqlite
      - ./enriched_products.json:/app/enriched_products.json
    restart: unless-stopped

  frontend:
    build: ./frontend
    container_name: agnes-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  db_data:
```

### Deploy with Docker Compose
```bash
# Set environment variables
export OPENROUTER_API_KEY=your_key_here

# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## ☁️ Cloud Deployment

### AWS Deployment (EC2 + RDS)

**1. Launch EC2 Instance**
```bash
# Instance type: t3.medium (2 vCPU, 4GB RAM)
# AMI: Ubuntu 22.04 LTS
# Security group: Allow ports 22, 80, 443, 8000

# SSH into instance
ssh -i key.pem ubuntu@<instance-ip>

# Install dependencies
sudo apt update
sudo apt install -y python3.9 python3-pip nodejs npm nginx

# Clone repository
git clone <repo-url>
cd q-hack
```

**2. Setup Backend Service**
```bash
# Create systemd service
sudo tee /etc/systemd/system/agnes-backend.service << EOF
[Unit]
Description=Agnes Backend API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/q-hack/backend
Environment="PATH=/home/ubuntu/q-hack/venv/bin"
Environment="OPENROUTER_API_KEY=your_key_here"
ExecStart=/home/ubuntu/q-hack/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable agnes-backend
sudo systemctl start agnes-backend
```

**3. Setup Frontend with Nginx**
```bash
# Build frontend
cd frontend
npm run build

# Configure Nginx
sudo tee /etc/nginx/sites-available/agnes << EOF
server {
    listen 80;
    server_name your-domain.com;
    root /home/ubuntu/q-hack/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/agnes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**4. Setup SSL with Let's Encrypt**
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Heroku Deployment

**1. Prepare Application**
```bash
# Create Procfile
echo "web: uvicorn backend.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Create runtime.txt
echo "python-3.9.18" > runtime.txt
```

**2. Deploy**
```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login and create app
heroku login
heroku create agnes-supply-chain

# Set environment variables
heroku config:set OPENROUTER_API_KEY=your_key_here

# Deploy
git push heroku main

# Open app
heroku open
```

### Vercel Deployment (Frontend Only)

**1. Configure vercel.json**
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "devCommand": "npm run dev",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-backend-url.com/api/:path*"
    }
  ]
}
```

**2. Deploy**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel --prod
```

---

## 🔧 Production Configuration

### Environment Variables

**Backend (.env)**
```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-...

# Optional
DATABASE_URL=sqlite:///db_new.sqlite
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.com
MAX_WORKERS=4
CACHE_TTL=3600
```

**Frontend (.env.production)**
```bash
VITE_API_BASE_URL=https://api.your-domain.com
VITE_ENABLE_ANALYTICS=true
```

### Performance Tuning

**Backend (main.py)**
```python
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()

# Enable compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Production server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        workers=4,  # CPU cores
        log_level="info",
        access_log=True
    )
```

**Nginx Caching**
```nginx
# Cache static assets
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Cache API responses
location /api/graph/stats {
    proxy_pass http://backend:8000;
    proxy_cache my_cache;
    proxy_cache_valid 200 1h;
}
```

### Database Optimization

**SQLite Production Settings**
```python
import sqlite3

conn = sqlite3.connect('db_new.sqlite')
conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging
conn.execute('PRAGMA synchronous=NORMAL')  # Faster writes
conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
conn.execute('PRAGMA temp_store=MEMORY')  # In-memory temp tables
```

**Add Indexes**
```sql
-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_substitution_score 
ON Substitution_Candidate(final_score DESC);

CREATE INDEX IF NOT EXISTS idx_ingredient_family 
ON Ingredient_Family(family_name);

CREATE INDEX IF NOT EXISTS idx_bom_component 
ON BOM_Component(BOMId, RawMaterialId);

CREATE INDEX IF NOT EXISTS idx_supplier_product 
ON Supplier_Product(SupplierId, ProductId);
```

---

## 📊 Monitoring & Logging

### Application Monitoring

**Backend Logging**
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    'agnes.log',
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

logger = logging.getLogger('agnes')
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

**Health Check Endpoint**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": check_database(),
        "api_key": check_api_key()
    }
```

### Error Tracking

**Sentry Integration**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1
)
```

### Performance Monitoring

**Prometheus Metrics**
```python
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

---

## 🔒 Security Hardening

### API Security

**Rate Limiting**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/recommendations")
@limiter.limit("10/minute")
async def get_recommendations(request: Request):
    return recommendations
```

**Authentication**
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials):
    token = credentials.credentials
    # Verify JWT token
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    await verify_token(credentials)
    return {"data": "protected"}
```

**CORS Configuration**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Infrastructure Security

**Firewall Rules**
```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**SSL/TLS Configuration**
```nginx
# Strong SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
add_header Strict-Transport-Security "max-age=31536000" always;
```

---

## 🧪 Testing Before Deployment

### Pre-Deployment Checklist

- [ ] All tests passing (`pytest backend/`)
- [ ] Frontend builds successfully (`npm run build`)
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] API endpoints responding correctly
- [ ] CORS configured for production domain
- [ ] SSL certificate installed
- [ ] Monitoring/logging configured
- [ ] Backup strategy in place
- [ ] Load testing completed

### Load Testing

**Using Apache Bench**
```bash
# Test API endpoint
ab -n 1000 -c 10 http://localhost:8000/api/recommendations/top?limit=10

# Results should show:
# - Requests per second: >100
# - Mean response time: <100ms
# - Failed requests: 0
```

**Using Locust**
```python
# locustfile.py
from locust import HttpUser, task, between

class AgnesUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_recommendations(self):
        self.client.get("/api/recommendations/top?limit=10")
    
    @task
    def get_companies(self):
        self.client.get("/api/companies")
```

```bash
locust -f locustfile.py --host=http://localhost:8000
```

---

## 📦 Backup & Recovery

### Database Backup

**Automated Backup Script**
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/agnes"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup database
sqlite3 db_new.sqlite ".backup $BACKUP_DIR/db_$DATE.sqlite"

# Compress
gzip $BACKUP_DIR/db_$DATE.sqlite

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sqlite.gz" -mtime +30 -delete

echo "Backup completed: db_$DATE.sqlite.gz"
```

**Cron Job**
```bash
# Run daily at 2 AM
0 2 * * * /home/ubuntu/q-hack/backup.sh >> /var/log/agnes-backup.log 2>&1
```

### Recovery Procedure

```bash
# Stop services
sudo systemctl stop agnes-backend
sudo systemctl stop nginx

# Restore database
gunzip -c /backups/agnes/db_20260408_020000.sqlite.gz > db_new.sqlite

# Restart services
sudo systemctl start agnes-backend
sudo systemctl start nginx

# Verify
curl http://localhost:8000/health
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

**.github/workflows/deploy.yml**
```yaml
name: Deploy Agnes

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Run tests
        run: |
          pip install -r backend/requirements.txt
          pytest backend/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        env:
          SSH_KEY: ${{ secrets.SSH_KEY }}
          HOST: ${{ secrets.HOST }}
        run: |
          echo "$SSH_KEY" > key.pem
          chmod 600 key.pem
          ssh -i key.pem ubuntu@$HOST 'cd q-hack && git pull && sudo systemctl restart agnes-backend'
```

---

## 📞 Support & Troubleshooting

### Common Issues

**Issue: API not responding**
```bash
# Check service status
sudo systemctl status agnes-backend

# Check logs
sudo journalctl -u agnes-backend -f

# Restart service
sudo systemctl restart agnes-backend
```

**Issue: Database locked**
```bash
# Check for locks
lsof db_new.sqlite

# Kill blocking process
kill -9 <PID>
```

**Issue: High memory usage**
```bash
# Monitor resources
htop

# Reduce workers
# Edit /etc/systemd/system/agnes-backend.service
# Change workers from 4 to 2
```

### Performance Optimization

**If API is slow:**
1. Add database indexes (see Database Optimization)
2. Enable caching (Redis/Memcached)
3. Increase worker count
4. Use CDN for static assets

**If frontend is slow:**
1. Enable code splitting
2. Lazy load components
3. Optimize images
4. Enable Gzip compression

---

## 📈 Scaling Strategy

### Horizontal Scaling

**Load Balancer (Nginx)**
```nginx
upstream agnes_backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}

server {
    location /api {
        proxy_pass http://agnes_backend;
    }
}
```

### Database Scaling

**Migrate to PostgreSQL**
```python
# Update DATABASE_URL
DATABASE_URL = "postgresql://user:pass@localhost/agnes"

# Use SQLAlchemy for connection pooling
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)
```

---

**Deployment complete! Agnes is production-ready.** 🚀
