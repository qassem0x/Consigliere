CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto"; 

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,       
    file_path VARCHAR(512) NOT NULL,      
    file_size_bytes BIGINT,
    row_count INT,
    columns JSONB,                        
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,            
    engine VARCHAR(20) NOT NULL,          -- "postgres", "mysql", .. etc
    connection_string TEXT NOT NULL,      -- Warning: Encrypt this in your app before saving
    schema TEXT,                          
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dossiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,           -- Nullable
    connection_id UUID REFERENCES connections(id) ON DELETE CASCADE, -- Nullable
    briefing TEXT,
    key_entities JSONB,
    recommended_actions JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT one_source_only CHECK (
        (file_id IS NOT NULL AND connection_id IS NULL) OR 
        (file_id IS NULL AND connection_id IS NOT NULL)
    )
);

CREATE TABLE chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,            -- Nullable
    connection_id UUID REFERENCES connections(id) ON DELETE CASCADE, -- Nullable
    
    dossier_id UUID REFERENCES dossiers(id) ON DELETE SET NULL,
    title VARCHAR(255),                
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraint: A chat must have EITHER a file OR a connection
    CONSTRAINT chat_source_check CHECK (
        (file_id IS NOT NULL AND connection_id IS NULL) OR 
        (file_id IS NULL AND connection_id IS NOT NULL)
    )
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,            
    content TEXT NOT NULL,                
    artifacts JSONB,
    related_code JSONB,                   
    steps JSONB,                          
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes (Performance)
CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_connections_user_id ON connections(user_id);
CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_messages_chat_id ON messages(chat_id);