import { useState, useEffect } from 'react'
import { Table, Card, Tag, Space, Button, Input, Select, Modal, List, Descriptions } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { domainsAPI, Domain, AggregatedIP } from '../utils/domainApi'
import { GlobalOutlined, ReloadOutlined, SearchOutlined, EyeOutlined } from '@ant-design/icons'
import { TablePageSkeleton } from '../components/PageSkeleton'

const Domains = () => {
  const [domains, setDomains] = useState<Domain[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [filters, setFilters] = useState({
    task_id: undefined as number | undefined,
    root_domain: '',
    scan_status: undefined as string | undefined,
  })
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedDomain, setSelectedDomain] = useState<Domain | null>(null)
  const [domainIPs, setDomainIPs] = useState<AggregatedIP[]>([])
  const [ipsLoading, setIPsLoading] = useState(false)

  const loadDomains = async (skip = 0, limit = 50) => {
    setLoading(true)
    try {
      const res = await domainsAPI.list({
        ...filters,
        skip,
        limit,
      })
      setDomains(res.data.items)
      setTotal(res.data.total)
    } catch (error) {
      console.error('Failed to load domains:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDomains()
  }, [filters])

  const showDomainDetail = async (domain: Domain) => {
    setSelectedDomain(domain)
    setDetailModalVisible(true)
    setIPsLoading(true)
    try {
      const res = await domainsAPI.getIPs(domain.id)
      setDomainIPs(res.data)
    } catch (error) {
      console.error('Failed to load domain IPs:', error)
    } finally {
      setIPsLoading(false)
    }
  }

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { color: string; bgColor: string; text: string }> = {
      pending: { color: '#94A3B8', bgColor: 'rgba(148, 163, 184, 0.15)', text: '等待中' },
      scanning: { color: '#0EA5E9', bgColor: 'rgba(14, 165, 233, 0.15)', text: '扫描中' },
      completed: { color: '#22C55E', bgColor: 'rgba(34, 197, 94, 0.15)', text: '已完成' },
      failed: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', text: '失败' },
    }
    const config = statusMap[status] || { color: '#94A3B8', bgColor: 'rgba(148, 163, 184, 0.15)', text: status }
    return (
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          padding: '4px 10px',
          borderRadius: 6,
          background: config.bgColor,
          color: config.color,
          fontSize: 12,
          fontWeight: 600,
        }}
      >
        <div
          style={{
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: config.color,
          }}
        />
        {config.text}
      </div>
    )
  }

  const columns: ColumnsType<Domain> = [
    {
      title: '域名',
      dataIndex: 'name',
      render: (name: string, record: Domain) => (
        <Space direction="vertical" size={0}>
          <span style={{ fontWeight: 600, color: '#F8FAFC' }}>{name}</span>
          {record.root_domain && (
            <Tag
              style={{
                background: 'rgba(51, 65, 85, 0.8)',
                color: '#94A3B8',
                border: 'none',
                fontSize: 12,
                padding: '0 8px',
                borderRadius: 4,
              }}
            >
              {record.root_domain}
            </Tag>
          )}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'scan_status',
      width: 100,
      render: (status: string) => getStatusBadge(status),
    },
    {
      title: '来源',
      dataIndex: 'sources',
      width: 150,
      render: (sources: string[]) => (
        <Space size={4}>
          {sources?.map((s) => (
            <Tag
              key={s}
              style={{
                background: 'rgba(14, 165, 233, 0.15)',
                color: '#0EA5E9',
                border: 'none',
                fontSize: 12,
                padding: '0 8px',
                borderRadius: 6,
              }}
            >
              {s}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'IP数',
      dataIndex: 'ip_count',
      width: 80,
      render: (count: number) => (
        <span style={{ color: '#F8FAFC', fontWeight: 600 }}>{count}</span>
      ),
    },
    {
      title: '端点数',
      dataIndex: 'endpoint_count',
      width: 80,
      render: (count: number) => (
        <span style={{ color: '#F8FAFC', fontWeight: 600 }}>{count}</span>
      ),
    },
    {
      title: '发现时间',
      dataIndex: 'discovered_at',
      width: 180,
      render: (date: string) => (
        <span style={{ color: '#94A3B8' }}>{new Date(date).toLocaleString()}</span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record: Domain) => (
        <Button
          type="text"
          icon={<EyeOutlined />}
          onClick={() => showDomainDetail(record)}
          style={{ color: '#0EA5E9' }}
        >
          详情
        </Button>
      ),
    },
  ]

  // 显示骨架屏避免白屏
  if (loading && domains.length === 0) {
    return <TablePageSkeleton />
  }

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">域名资产</h1>
        <p className="page-subtitle">查看和管理扫描发现的域名资产</p>
      </div>

      {/* Card with Table */}
      <Card
        style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(148, 163, 184, 0.1)',
          borderRadius: 16,
        }}
        headStyle={{
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
        }}
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(129, 140, 248, 0.2) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#818CF8',
              }}
            >
              <GlobalOutlined />
            </div>
            <span style={{ color: '#F8FAFC', fontWeight: 600 }}>域名列表</span>
          </div>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Input.Search
            placeholder="根域名"
            value={filters.root_domain}
            onChange={(e) => setFilters({ ...filters, root_domain: e.target.value })}
            onSearch={() => loadDomains()}
            style={{ width: 200 }}
            prefix={<SearchOutlined style={{ color: '#64748B' }} />}
          />
          <Select
            placeholder="状态"
            allowClear
            value={filters.scan_status}
            onChange={(value) => setFilters({ ...filters, scan_status: value })}
            style={{ width: 120 }}
            options={[
              { value: 'pending', label: '等待中' },
              { value: 'scanning', label: '扫描中' },
              { value: 'completed', label: '已完成' },
              { value: 'failed', label: '失败' },
            ]}
          />
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            onClick={() => loadDomains()}
            style={{
              background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
              border: 'none',
              borderRadius: 8,
            }}
          >
            查询
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={domains}
          rowKey="id"
          loading={loading}
          pagination={{
            total,
            pageSize: 50,
            showSizeChanger: true,
            showTotal: (total) => (
              <span style={{ color: '#64748B' }}>
                共 <strong style={{ color: '#0EA5E9' }}>{total}</strong> 条
              </span>
            ),
          }}
          onChange={(pagination) => {
            loadDomains(
              (pagination.current! - 1) * pagination.pageSize!,
              pagination.pageSize!
            )
          }}
        />
      </Card>

      {/* Detail Modal */}
      <Modal
        title={
          <div style={{ color: '#F8FAFC' }}>
            域名详情: {selectedDomain?.name}
          </div>
        }
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={800}
      >
        {selectedDomain && (
          <>
            <Descriptions
              size="small"
              column={2}
              style={{ marginBottom: 24 }}
              labelStyle={{ color: '#64748B' }}
              contentStyle={{ color: '#CBD5E1' }}
            >
              <Descriptions.Item label="根域名">
                {selectedDomain.root_domain || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {getStatusBadge(selectedDomain.scan_status)}
              </Descriptions.Item>
              <Descriptions.Item label="IP数">
                <span style={{ color: '#0EA5E9', fontWeight: 600 }}>{selectedDomain.ip_count}</span>
              </Descriptions.Item>
              <Descriptions.Item label="端点数">
                <span style={{ color: '#0EA5E9', fontWeight: 600 }}>{selectedDomain.endpoint_count}</span>
              </Descriptions.Item>
              <Descriptions.Item label="来源">
                {selectedDomain.sources?.map((s) => (
                  <Tag
                    key={s}
                    style={{
                      background: 'rgba(14, 165, 233, 0.15)',
                      color: '#0EA5E9',
                      border: 'none',
                      fontSize: 12,
                      padding: '0 8px',
                    }}
                  >
                    {s}
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>

            <h4 style={{ color: '#F8FAFC', marginBottom: 16 }}>IP 列表</h4>
            <List
              loading={ipsLoading}
              dataSource={domainIPs}
              style={{
                background: 'rgba(51, 65, 85, 0.3)',
                borderRadius: 8,
                padding: '0 16px',
              }}
              renderItem={(ip) => (
                <List.Item style={{ borderBottomColor: 'rgba(148, 163, 184, 0.1)' }}>
                  <List.Item.Meta
                    title={
                      <Space>
                        <span style={{ color: '#F8FAFC', fontFamily: 'monospace' }}>
                          {ip.ip}:{ip.port}
                        </span>
                        {ip.protocol && (
                          <Tag
                            style={{
                              background: 'rgba(34, 197, 94, 0.15)',
                              color: '#22C55E',
                              border: 'none',
                              fontSize: 12,
                            }}
                          >
                            {ip.protocol}
                          </Tag>
                        )}
                        {ip.sources?.map((s) => (
                          <Tag
                            key={s}
                            style={{
                              background: 'rgba(14, 165, 233, 0.15)',
                              color: '#0EA5E9',
                              border: 'none',
                              fontSize: 12,
                            }}
                          >
                            {s}
                          </Tag>
                        ))}
                      </Space>
                    }
                    description={
                      <Space direction="vertical" size={0}>
                        {Object.entries(ip.products || {}).map(([source, product]) => (
                          <span key={source} style={{ color: '#94A3B8' }}>
                            {source}: {product}
                          </span>
                        ))}
                        {ip.endpoint_count > 0 && (
                          <span style={{ color: '#64748B' }}>端点数: {ip.endpoint_count}</span>
                        )}
                      </Space>
                    }
                  />
                </List.Item>
              )}
            />
          </>
        )}
      </Modal>
    </div>
  )
}

export default Domains
