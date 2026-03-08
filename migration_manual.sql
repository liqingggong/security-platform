CREATE TABLE IF NOT EXISTS subfinder_assets (
    id SERIAL PRIMARY KEY,
    type assettype NOT NULL,
    value VARCHAR(1024) NOT NULL,
    url VARCHAR(2048),
    domain VARCHAR(255),
    root_domain VARCHAR(255),
    discovered_urls JSON,
    data JSON,
    tags JSON,
    discovered_at TIMESTAMP WITHOUT TIME ZONE,
    last_seen TIMESTAMP WITHOUT TIME ZONE,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    task_id INTEGER REFERENCES tasks(id),
    UNIQUE (tenant_id, task_id, type, value)
);

CREATE INDEX IF NOT EXISTS ix_subfinder_assets_domain ON subfinder_assets(domain);
CREATE INDEX IF NOT EXISTS ix_subfinder_assets_id ON subfinder_assets(id);
CREATE INDEX IF NOT EXISTS ix_subfinder_assets_root_domain ON subfinder_assets(root_domain);
CREATE INDEX IF NOT EXISTS ix_subfinder_assets_task_id ON subfinder_assets(task_id);
CREATE INDEX IF NOT EXISTS ix_subfinder_assets_tenant_id ON subfinder_assets(tenant_id);
CREATE INDEX IF NOT EXISTS ix_subfinder_assets_type ON subfinder_assets(type);
CREATE INDEX IF NOT EXISTS ix_subfinder_assets_url ON subfinder_assets(url);
CREATE INDEX IF NOT EXISTS ix_subfinder_assets_value ON subfinder_assets(value);

ALTER TABLE assets ADD COLUMN IF NOT EXISTS discovered_by JSON;
ALTER TABLE assets ADD COLUMN IF NOT EXISTS source_urls JSON;

INSERT INTO alembic_version (version_num) 
VALUES ('6016f0144e3c') 
ON CONFLICT (version_num) DO NOTHING;
