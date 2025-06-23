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
    return {"message": "Semantic Search & LLM API is running", "version": "1.0.0"}

@app.post("/embed")
async def create_embedding(doc: Document):
    """Create and store document embedding"""
    try:
        logging.info(f"Creating embedding for document with workflow_id: {doc.workflow_id}")
        embedding = model.encode(doc.content)
        
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO documents (content, embedding, workflow_id) VALUES (%s, %s, %s) RETURNING id",
                    (doc.content, np.array(embedding).tobytes(), doc.workflow_id)
                )
                doc_id = cur.fetchone()['id']
                conn.commit()
                
        logging.info(f"Document embedded successfully with ID: {doc_id}")
        return {"id": doc_id, "message": "Document embedded successfully"}
        
    except Exception as e:
        logging.error(f"Embedding error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

@app.post("/query")
async def semantic_search(query: Query):
    """Perform semantic search on documents"""
    try:
        logging.info(f"Performing search for: '{query.text}' with workflow_id: {query.workflow_id}")
        query_embedding = model.encode(query.text)
        
        with get_db() as conn:
            with conn.cursor() as cur:
                # Updated query to handle None workflow_id properly
                if query.workflow_id is None:
                    cur.execute("""
                        SELECT id, content, workflow_id,
                        1 - (embedding <=> %s) as similarity
                        FROM documents
                        ORDER BY similarity DESC
                        LIMIT %s
                    """, (np.array(query_embedding).tobytes(), query.k))
                else:
                    cur.execute("""
                        SELECT id, content, workflow_id,
                        1 - (embedding <=> %s) as similarity
                        FROM documents
                        WHERE workflow_id = %s
                        ORDER BY similarity DESC
                        LIMIT %s
                    """, (np.array(query_embedding).tobytes(), query.workflow_id, query.k))
                
                results = cur.fetchall()
                
        logging.info(f"Found {len(results)} results")
        return {"results": results, "query": query.text, "total_results": len(results)}
        
    except Exception as e:
        logging.error(f"Query error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Check API and database health"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.execute("SELECT COUNT(*) as doc_count FROM documents")
                doc_count = cur.fetchone()['doc_count']
                
        return {
            "status": "healthy", 
            "database": "connected",
            "total_documents": doc_count,
            "model": "BAAI/bge-small-en-v1.5"
        }
    except Exception as e:
        logging.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.post("/llama")
async def query_llama(request: LLMRequest):
    """Query LLM model"""
    try:
        logging.info(f"Querying {request.model} with temperature {request.temperature}")
        response = ollama.generate(
            model=request.model,
            prompt=request.prompt,
            options={
                'temperature': request.temperature,
                'num_predict': request.max_tokens
            }
        )
        
        logging.info(f"LLM response generated successfully")
        return {
            "response": response['response'],
            "model": request.model,
            "prompt_length": len(request.prompt),
            "response_length": len(response['response'])
        }
        
    except Exception as e:
        logging.error(f"LLaMA error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM query failed: {str(e)}")

# Additional helpful endpoints

@app.get("/documents")
async def list_documents(workflow_id: Optional[int] = None, limit: int = 10):
    """List documents in the database"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                if workflow_id is None:
                    cur.execute("""
                        SELECT id, content, workflow_id, 
                               LENGTH(content) as content_length,
                               SUBSTRING(content, 1, 100) as preview
                        FROM documents 
                        ORDER BY id DESC 
                        LIMIT %s
                    """, (limit,))
                else:
                    cur.execute("""
                        SELECT id, content, workflow_id,
                               LENGTH(content) as content_length,
                               SUBSTRING(content, 1, 100) as preview
                        FROM documents 
                        WHERE workflow_id = %s
                        ORDER BY id DESC 
                        LIMIT %s
                    """, (workflow_id, limit))
                
                documents = cur.fetchall()
                
        return {"documents": documents, "count": len(documents)}
        
    except Exception as e:
        logging.error(f"List documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")

@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """Delete a document by ID"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents WHERE id = %s RETURNING id", (doc_id,))
                deleted = cur.fetchone()
                
                if not deleted:
                    raise HTTPException(status_code=404, detail="Document not found")
                    
                conn.commit()
                
        return {"message": f"Document {doc_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Delete document error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_documents,
                        COUNT(DISTINCT workflow_id) as unique_workflows,
                        AVG(LENGTH(content)) as avg_content_length,
                        MIN(id) as oldest_doc_id,
                        MAX(id) as newest_doc_id
                    FROM documents
                """)
                stats = cur.fetchone()
                
                cur.execute("""
                    SELECT workflow_id, COUNT(*) as count
                    FROM documents 
                    WHERE workflow_id IS NOT NULL
                    GROUP BY workflow_id 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                workflow_stats = cur.fetchall()
                
        return {
            "database_stats": stats,
            "top_workflows": workflow_stats
        }
        
    except Exception as e:
        logging.error(f"Stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

# Initialize database table if it doesn't exist
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Check if table exists, create if not
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id SERIAL PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding BYTEA NOT NULL,
                        workflow_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create index for better performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_documents_workflow_id 
                    ON documents(workflow_id)
                """)
                
                conn.commit()
                
        logging.info("Database initialized successfully")
        
    except Exception as e:
        logging.error(f"Database initialization failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
