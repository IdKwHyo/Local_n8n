# Local_n8n
Here's a comprehensive **README.md** for your Internal Automation Platform repository:

```markdown
# Internal Automation Platform (LLM-Powered)


Enterprise-grade automation platform with local LLM integration, vector search, and visual workflow builder. Fully self-contained with no external dependencies.

## Key Features

- **Secure & Air-Gapped** - No internet access required
- **Local AI Processing** - LLaMA2/Mistral via Ollama
- **Semantic Search** - FAISS/Qdrant-like vector search via PostgreSQL
- **Visual Workflows** - Node-RED based flow builder
- **RBAC Security** - JWT authentication with role-based access

## Tech Stack

| Component           | Technology                  |
|---------------------|-----------------------------|
| Workflow Engine     | Node-RED                    |
| Backend Service     | FastAPI (Python)            |
| Vector Database     | PostgreSQL + pgvector       |
| LLM Inference       | Ollama (LLaMA2/Mistral)     |
| Embedding Model     | BAAI/bge-small-en-v1.5      |
| Containerization    | Docker Compose              |

## Quick Start

### Prerequisites
- Docker 20.10+
- NVIDIA GPU (recommended)
- 16GB RAM minimum

```bash
# Clone repository
git clone https://github.com/your-org/internal-automation.git
cd internal-automation

# Start services
docker-compose up -d

# Initialize LLM model
docker exec ollama ollama pull llama2
```

### Access Interfaces
- **Node-RED**: http://localhost:1880
- **API Docs**: http://localhost:8000/docs
- **Adminer (DB UI)**: http://localhost:8080

## Example Workflows

1. **Invoice Processing**
   ```
   PDF Upload → Text Extraction → Vector Store → LLM Summary → Database
   ```

2. **Knowledge Search**  
   ```
   User Query → Vector Search → LLM Synthesis → Format Response
   ```

## API Usage

```python
import requests

# Create embedding
requests.post("http://localhost:8000/embed", json={
    "content": "Invoice #123 for $500",
    "workflow_id": 1
})

# Semantic search
requests.post("http://localhost:8000/query", json={
    "text": "find financial documents",
    "k": 3
})
```

## Directory Structure

```
.
├── node-red/               # Flow configurations
│   ├── flows.json          # Main workflow definition
│   └── settings.js         # Node-RED settings
├── python-service/         # FastAPI backend
│   ├── app.py              # Core API endpoints
│   └── requirements.txt    # Python dependencies
├── postgres/
│   └── init.sql            # Database schema setup
├── docker-compose.yaml     # Full stack definition
└── README.md               # This document
```

## Security Notes

1. Change default credentials:
   ```bash
   # PostgreSQL
   echo "POSTGRES_PASSWORD=your_secure_password" >> .env

   # Node-RED
   echo "NODE_RED_CREDENTIAL_SECRET=$(openssl rand -hex 32)" >> .env
   ```

2. Enable HTTPS:
   ```yaml
   # In docker-compose.yaml
   services:
     node-red:
       ports:
         - "443:1880"
       volumes:
         - ./certs:/etc/nginx/certs
   ```

## Support

For issues, please:
1. Check running containers:
   ```bash
   docker-compose ps
   ```
2. View logs:
   ```bash
   docker-compose logs -f python-service
   ```
3. Open an issue with:
   - Relevant logs
   - Steps to reproduce
   - Expected vs actual behavior

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.
```

This README includes:

1. Visual system diagram (replace URL with your actual diagram)
2. Self-contained installation instructions
3. API usage examples
4. Security best practices
5. Troubleshooting guide
6. Clean directory structure overview
7. License information

Would you like me to add any specific sections such as:
- Detailed contributor guidelines
- Roadmap with planned features
- Performance tuning recommendations
- Screenshots of the Node-RED interface?
