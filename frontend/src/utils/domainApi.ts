import apiClient from './api'

export interface Domain {
  id: number
  name: string
  root_domain?: string
  scan_status: 'pending' | 'scanning' | 'completed' | 'failed'
  ip_count: number
  endpoint_count: number
  sources: string[]
  discovered_at: string
}

export interface AggregatedIP {
  id: number
  ip: string
  port: number
  protocol?: string
  sources: string[]
  products: Record<string, string>
  banners?: Record<string, string>
  endpoint_count: number
  first_seen: string
}

export interface DomainDetail {
  id: number
  name: string
  root_domain?: string
  scan_status: string
  discovered_by: string
  discovered_at: string
  ip_count: number
  endpoint_count: number
  source_count: number
  sources: string[]
  ips: AggregatedIP[]
  created_at: string
  updated_at: string
}

export interface DomainEndpoint {
  id: number
  path: string
  method: string
  status_code?: number
  content_type?: string
  content_length?: number
  title?: string
  technologies: string[]
  discovered_by?: string
  discovered_at: string
}

export interface ListDomainsParams {
  task_id?: number
  root_domain?: string
  scan_status?: string
  skip?: number
  limit?: number
}

export interface ListDomainsResponse {
  items: Domain[]
  total: number
}

export interface ListEndpointsResponse {
  items: DomainEndpoint[]
  total: number
}

export const domainsAPI = {
  list: (params?: ListDomainsParams) =>
    apiClient.get<ListDomainsResponse>('/domains/', { params }),

  getUnique: (params?: { skip?: number; limit?: number }) =>
    apiClient.get<DomainDetail[]>('/domains/unique', { params }),

  get: (id: number) =>
    apiClient.get<DomainDetail>(`/domains/${id}`),

  getIPs: (domainId: number) =>
    apiClient.get<AggregatedIP[]>(`/domains/${domainId}/ips`),

  getEndpoints: (ipId: number, params?: { skip?: number; limit?: number }) =>
    apiClient.get<ListEndpointsResponse>(`/domains/ips/${ipId}/endpoints`, { params }),
}
