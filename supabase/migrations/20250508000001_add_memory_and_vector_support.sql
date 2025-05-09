-- Migration: Add memory persistence and vector embeddings support
-- Author: Claude-DevOps
-- Date: 2025-05-08

-- Enable pgvector extension for vector embeddings (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create user_memories table for persistent memory storage
CREATE TABLE IF NOT EXISTS public.user_memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    memory_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT user_memories_user_id_key UNIQUE (user_id)
);

-- Add RLS policies for user_memories
ALTER TABLE public.user_memories ENABLE ROW LEVEL SECURITY;

-- Allow users to read only their own memories
CREATE POLICY "Users can read their own memories"
    ON public.user_memories
    FOR SELECT
    USING (auth.uid()::text = user_id);

-- Allow users to insert/update only their own memories
CREATE POLICY "Users can insert their own memories"
    ON public.user_memories
    FOR INSERT
    WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Users can update their own memories"
    ON public.user_memories
    FOR UPDATE
    USING (auth.uid()::text = user_id);

-- Add vector storage to project_photos table if it doesn't exist already
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' AND table_name = 'project_photos' 
                   AND column_name = 'embed') THEN
        -- Add vector embedding column
        ALTER TABLE public.project_photos ADD COLUMN IF NOT EXISTS embed vector(1536);
        
        -- Add vision labels array
        ALTER TABLE public.project_photos ADD COLUMN IF NOT EXISTS vision_labels TEXT[];
        
        -- Add confidence score
        ALTER TABLE public.project_photos ADD COLUMN IF NOT EXISTS confidence FLOAT;
    END IF;
END $$;

-- Create index for vector similarity search if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'project_photos_embed_idx') THEN
        -- Create ivfflat index for vector similarity search
        CREATE INDEX IF NOT EXISTS project_photos_embed_idx ON public.project_photos USING ivfflat (embed vector_cosine_ops) WITH (lists = 100);
    END IF;
END $$;

-- Create function for vector similarity search
CREATE OR REPLACE FUNCTION find_similar_photos(
    p_project_id TEXT,
    p_embedding VECTOR,
    p_limit INTEGER DEFAULT 5
) RETURNS TABLE (storage_path TEXT, distance FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pp.storage_path, 
        pp.embed <=> p_embedding AS distance
    FROM 
        project_photos pp
    WHERE 
        pp.project_id = p_project_id 
        AND pp.embed IS NOT NULL
    ORDER BY 
        distance ASC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;