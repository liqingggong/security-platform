// 用户相关类型
export interface User {
  id: number
  email: string
  full_name?: string
  is_active: boolean
  role: 'admin' | 'user'
  tenant_id: number
  created_at: string
  last_login?: string
}

export interface UserLogin {
  email: string
  password: string
}

export interface UserCreate {
  email: string
  password: string
  full_name?: string
}

export interface Token {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RefreshToken {
  refresh_token: string
}

// 任务相关类型
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface Task {
  id: number
  name: string
  description?: string
  status: TaskStatus
  progress: number
  input_data: TaskInput
  output_data?: TaskOutput
  scan_plan_id?: number
  tenant_id: number
  created_at: string
  started_at?: string
  completed_at?: string
  error?: string
}

export interface TaskInput {
  root_domains?: string[]
  ips?: string[]
  fofa_query?: string
  hunter_query?: string
  enable?: Record<string, boolean>
  options?: Record<string, any>
  plan_tool_configs?: Record<string, any>
}

export interface TaskOutput {
  results?: Record<string, any>
  summary?: {
    total_assets_discovered?: number
    total_vulnerabilities_found?: number
    fofa_records?: number
    hunter_records?: number
    subfinder_subdomains?: number
    subfinder_records?: number
    nmap_ips?: number
    httpx_alive?: number
    nuclei_findings?: number
  }
  errors?: string[]
  child_task_ids?: {
    first: string[]
    second: string[]
    post: string[]
  }
}

export interface TaskUpdate {
  name?: string
  description?: string
  root_domains?: string[]
  ips?: string[]
  fofa_query?: string
  hunter_query?: string
  enable?: Record<string, boolean>
  options?: Record<string, any>
  scan_plan_id?: number
}

export interface TaskCreate {
  name: string
  description?: string
  root_domains?: string[]
  ips?: string[]
  fofa_query?: string
  hunter_query?: string
  enable?: Record<string, boolean>
  options?: Record<string, any>
  scan_plan_id?: number
}

export interface TaskLog {
  id: number
  task_id: number
  phase: string
  level: 'info' | 'warning' | 'error'
  message: string
  created_at: string
}

// 资产相关类型
export type AssetType = 'domain' | 'subdomain' | 'ip' | 'url' | 'endpoint'

export interface Asset {
  id: number
  type: AssetType
  value: string
  domain?: string
  url?: string
  ip_address?: string
  port?: number
  protocol?: string
  product?: string
  tags?: string[]
  sources?: string[]
  data?: Record<string, any>
  task_id?: number
  tenant_id: number
  last_seen: string
  created_at: string
}

export interface AssetListResponse {
  items: Asset[]
  total: number
}

export interface AssetStats {
  by_type: Record<AssetType, number>
  total: number
}

// 漏洞相关类型
export type VulnerabilitySeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type VulnerabilityStatus = 'open' | 'in_progress' | 'resolved' | 'false_positive'

export interface Vulnerability {
  id: number
  title: string
  description?: string
  severity: VulnerabilitySeverity
  status: VulnerabilityStatus
  cve_id?: string
  cwe_id?: string
  cvss_score?: number
  asset_id?: number
  task_id?: number
  asset_url?: string
  asset_ip?: string
  asset_domain?: string
  asset_port?: number
  references?: string[]
  raw_data?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface VulnerabilityUpdate {
  status?: VulnerabilityStatus
}

export interface VulnerabilityStats {
  by_severity: Record<VulnerabilitySeverity, number>
  by_status: Record<VulnerabilityStatus, number>
  total: number
}

// 凭据相关类型
export type CredentialProvider = 'fofa' | 'hunter'

export interface ApiCredential {
  id: number
  provider: CredentialProvider
  api_key: string
  api_email?: string
  is_active: boolean
  tenant_id: number
  created_at: string
  updated_at: string
}

export interface CredentialUpdate {
  api_key: string
  api_email?: string
  is_active: boolean
}

// 扫描方案相关类型
export interface ScanPlanTool {
  tool_name: string
  enabled: boolean
  config?: Record<string, any>
}

export interface ScanPlan {
  id: number
  name: string
  description?: string
  options?: Record<string, any>
  tools?: ScanPlanTool[]
  tenant_id: number
  created_at: string
  updated_at: string
}

export interface ScanPlanCreate {
  name: string
  description?: string
  options?: Record<string, any>
  tools: ScanPlanTool[]
}

export interface ScanPlanUpdate {
  description?: string
  options?: Record<string, any>
  tools?: ScanPlanTool[]
}

// 指纹规则相关类型
export interface FingerprintRule {
  id: number
  name: string
  description?: string
  enabled: boolean
  target: 'url' | 'title' | 'header' | 'body'
  pattern: string
  metadata?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface FingerprintRuleCreate {
  name: string
  description?: string
  enabled?: boolean
  target: string
  pattern: string
  metadata?: Record<string, any>
}

export interface FingerprintRuleUpdate {
  description?: string
  enabled?: boolean
  target?: string
  pattern?: string
  metadata?: Record<string, any>
}

// 工具相关类型
export type ToolType = 'asset_search' | 'subdomain_enum' | 'port_scan' | 'http_probe' | 'vuln_scan' | 'other'

export interface Tool {
  id: number
  name: string
  display_name?: string
  tool_type: ToolType
  file_path?: string
  command_template?: string
  config?: Record<string, any>
  enabled: boolean
  version?: string
  author?: string
  description?: string
  tenant_id: number
  created_at: string
  updated_at: string
}

export interface ToolUpdate {
  display_name?: string
  description?: string
  version?: string
  author?: string
  command_template?: string
  config?: Record<string, any>
  enabled?: boolean
}

// API 错误类型
export interface ApiError {
  detail?: string
  message?: string
}

// 分页相关类型
export interface PaginationParams {
  skip?: number
  limit?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}
