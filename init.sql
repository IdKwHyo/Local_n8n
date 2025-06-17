-- Enable vector extension (required for embedding operations)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create workflows table with additional metadata
CREATE TABLE workflows (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by TEXT DEFAULT 'system',
    is_active BOOLEAN DEFAULT TRUE
);

-- Create documents table with proper constraints and indexing
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    raw_content TEXT,  -- For storing original/unprocessed content
    embedding vector(384) NOT NULL,  -- Matches bge-small-en-v1.5 embedding size
    workflow_id INTEGER REFERENCES workflows(id) ON DELETE SET NULL,
    metadata JSONB,  -- For storing additional document metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT content_not_empty CHECK (content <> '')
);

-- Create optimized index for vector search
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- For faster workflow-based queries
CREATE INDEX idx_documents_workflow_id ON documents(workflow_id);

-- For metadata searches
CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata);

-- Create function to update timestamp on row update
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for automatic timestamp updates
CREATE TRIGGER update_workflows_modtime
BEFORE UPDATE ON workflows
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_documents_modtime
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Create search function for easier querying
CREATE OR REPLACE FUNCTION semantic_search(
    query_embedding vector(384),
    workflow_id_param INTEGER DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.5,
    max_results INTEGER DEFAULT 5
)
RETURNS TABLE(
    id INTEGER,
    content TEXT,
    similarity FLOAT,
    workflow_id INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.content,
        1 - (d.embedding <=> query_embedding) AS similarity,
        d.workflow_id
    FROM 
        documents d
    WHERE 
        (workflow_id_param IS NULL OR d.workflow_id = workflow_id_param)
        AND (1 - (d.embedding <=> query_embedding)) > similarity_threshold
    ORDER BY 
        similarity DESC
    LIMIT 
        max_results;
END;
$$ LANGUAGE plpgsql;