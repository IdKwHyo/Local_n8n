from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2cffi as psycopg2
from psycopg2.extras import RealDictCursor
import ollama
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
from fastapi.middleware.cors import CORSMiddleware

# Initialize
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to be more restrictive in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = SentenceTransformer('BAAI/bge-small-en-v1.5')
logging.basicConfig(level=logging.INFO)

# Database connection
def get_db():
    return psycopg2.connect(
        "postgres://postgres:postgres@postgres:5432/automation",
        cursor_factory=RealDictCursor
    )

# Models
class Document(BaseModel):
    content: str
    workflow_id: int = None

class Query(BaseModel):
    text: str
    workflow_id: int = None
    k: int = 3  

class LLMRequest(BaseModel):  # New model for LLM endpoint
    model: str = "llama2"
    prompt: str
    temperature: float = 0.7
    max_tokens: int = 1000

# Routes
@app.get("/")
def read_root():
    return {"message": "API is running"}

@app.post("/embed")
async def create_embedding(doc: Document):
    try:
        embedding = model.encode(doc.content)
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO documents (content, embedding, workflow_id) VALUES (%s, %s, %s) RETURNING id",
                    (doc.content, np.array(embedding).tobytes(), doc.workflow_id)
                )
                doc_id = cur.fetchone()['id']
                conn.commit()
        return {"id": doc_id}
    except Exception as e:
        logging.error(f"Embedding error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def semantic_search(query: Query):
    try:
        query_embedding = model.encode(query.text)
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, content, 
                    1 - (embedding <=> %s) as similarity
                    FROM documents
                    WHERE workflow_id = %s OR %s IS NULL
                    ORDER BY similarity DESC
                    LIMIT %s
                """, (np.array(query_embedding).tobytes(), query.workflow_id, query.workflow_id, query.k))
                results = cur.fetchall()
        return {"results": results}
    except Exception as e:
        logging.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/health")
async def health_check():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/llama")
async def query_llama(request: LLMRequest):  
    try:
        response = ollama.generate(
            model=request.model,
            prompt=request.prompt,
            options={
                'temperature': request.temperature,
                'num_predict': request.max_tokens
            }
        )
        return {"response": response['response']}
    except Exception as e:
        logging.error(f"LLaMA error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))