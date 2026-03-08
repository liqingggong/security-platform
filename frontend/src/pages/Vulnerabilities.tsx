import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Input, Select, Button, Space, Tag, message, Card, Tooltip } from 'antd'
import { ReloadOutlined, SearchOutlined, FilterOutlined, BugOutlined, EyeOutlined, ExclamationCircleOutlined, WarningOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { vulnerabilitiesAPI, tasksAPI } from '../utils/api'
import dayjs from 'dayjs'
import { TablePageSkeleton } from '../components/PageSkeleton'

const { Search } = Input

const Vulnerabilities = () => {
  const [vulnerabilities, setVulnerabilities] = useState<any[]>([])
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({
    task_id: undefined as number | undefined,
    severity: undefined as string | undefined,
    status: undefined as string | undefined,
    search: '',
  })
  const navigate = useNavigate()

  useEffect(() => {
    loadTasks()
    loadVulnerabilities()
  }, [])

  useEffect(() => {
    loadVulnerabilities()
  }, [filters])

  const loadTasks = async () => {
    try {
      const data = await tasksAPI.list()
      setTasks(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载任务列表失败')
    }
  }

  const loadVulnerabilities = async () => {
    setLoading(true)
    try {
      const params: any = {}
      if (filters.task_id) params.task_id = filters.task_id
      if (filters.severity) params.severity = filters.severity
      if (filters.status) params.status = filters.status
      if (filters.search) params.search = filters.search
      const data = await vulnerabilitiesAPI.list(params)
      setVulnerabilities(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载漏洞列表失败')
    } finally {
      setLoading(false)
    }
  }

  const getSeverityBadge = (severity: string) => {
    const severityMap: Record<string, { color: string; bgColor: string; icon: React.ReactNode; label: string }> = {
      critical: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', icon: <ExclamationCircleOutlined />, label: '严重' },
      high: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', icon: <WarningOutlined />, label: '高危' },
      medium: { color: '#F97316', bgColor: 'rgba(249, 115, 22, 0.15)', icon: <WarningOutlined />, label: '中危' },
      low: { color: '#0EA5E9', bgColor: 'rgba(14, 165, 233, 0.15)', icon: <InfoCircleOutlined />, label: '低危' },
      info: { color: '#64748B', bgColor: 'rgba(100, 116, 139, 0.15)', icon: <InfoCircleOutlined />, label: '信息' },
    }
    const config = severityMap[severity] || { color: '#64748B', bgColor: 'rgba(100, 116, 139, 0.15)', icon: null, label: severity }
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
        {config.label}
      </div>
    )
  }

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; bgColor: string; text: string }> = {
      open: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', text: '未处理' },
      in_progress: { color: '#0EA5E9', bgColor: 'rgba(14, 165, 233, 0.15)', text: '处理中' },
      resolved: { color: '#22C55E', bgColor: 'rgba(34, 197, 94, 0.15)', text: '已解决' },
      false_positive: { color: '#64748B', bgColor: 'rgba(100, 116, 139, 0.15)', text: '误报' },
    }
    const config = statusMap[status] || { color: '#64748B', bgColor: 'rgba(100, 116, 139, 0.15)', text: status }
    return (
      <Tag
        style={{
          background: config.bgColor,
          color: config.color,
          border: 'none',
          borderRadius: 6,
          fontWeight: 600,
          padding: '4px 12px',
        }}
      >
        {config.text}
      </Tag>
    )
  }

  // 统计各等级漏洞数量
  const severityCounts = vulnerabilities.reduce((acc, vuln) => {
    acc[vuln.severity] = (acc[vuln.severity] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const columns = [
    {
      title: '漏洞标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title: string) => (
        <span style={{ fontWeight: 500, color: '#F8FAFC' }}>{title}</span>
      ),
    },
    {
      title: '资产地址',
      dataIndex: 'asset_url',
      key: 'asset_url',
      render: (url: string, record: any) => {
        const display = url || (record.asset_ip && record.asset_port
          ? `${record.asset_ip}:${record.asset_port}`
          : record.asset_ip || record.asset_domain || '-')
        return (
          <Tag
            style={{
              background: 'rgba(51, 65, 85, 0.8)',
              color: '#CBD5E1',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              borderRadius: 6,
              fontSize: 12,
              fontFamily: 'monospace',
            }}
          >
            {display}
          </Tag>
        )
      },
      ellipsis: true,
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => getSeverityBadge(severity),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: 'CVE ID',
      dataIndex: 'cve_id',
      key: 'cve_id',
      width: 140,
      render: (cve: string) =>
        cve ? (
          <Tag
            style={{
              background: 'rgba(234, 179, 8, 0.15)',
              color: '#EAB308',
              border: 'none',
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            {cve}
          </Tag>
        ) : (
          <span style={{ color: '#64748B' }}>-</span>
        ),
    },
    {
      title: '发现时间',
      dataIndex: 'discovered_at',
      key: 'discovered_at',
      width: 160,
      render: (time: string) => (
        <span style={{ color: '#94A3B8', fontSize: 13 }}>
          {dayjs(time).format('YYYY-MM-DD HH:mm')}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 90,
      align: 'center' as const,
      render: (_: any, record: any) => (
        <Tooltip title="查看详情">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/vulnerabilities/${record.id}`)}
            style={{ color: '#0EA5E9' }}
          />
        </Tooltip>
      ),
    },
  ]

  // 显示骨架屏避免白屏
  if (loading && vulnerabilities.length === 0) {
    return <TablePageSkeleton />
  }

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">漏洞管理</h1>
        <p className="page-subtitle">查看和处理扫描发现的安全漏洞</p>
      </div>

      {/* Stats Cards */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        {[
          { severity: 'critical', label: '严重', color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)' },
          { severity: 'high', label: '高危', color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)' },
          { severity: 'medium', label: '中危', color: '#F97316', bgColor: 'rgba(249, 115, 22, 0.15)' },
          { severity: 'low', label: '低危', color: '#0EA5E9', bgColor: 'rgba(14, 165, 233, 0.15)' },
        ].map((item) => (
          <Card
            key={item.severity}
            style={{
              flex: 1,
              minWidth: 140,
              borderRadius: 12,
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              cursor: 'pointer',
            }}
            bodyStyle={{ padding: 16 }}
            onClick={() => setFilters({ ...filters, severity: item.severity })}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 10,
                  background: item.bgColor,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: item.color,
                }}
              >
                <BugOutlined />
              </div>
              <div>
                <div style={{ fontSize: 24, fontWeight: 700, color: item.color }}>
                  {severityCounts[item.severity] || 0}
                </div>
                <div style={{ fontSize: 12, color: '#64748B' }}>{item.label}漏洞</div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Filter Bar */}
      <div
        className="glass-card"
        style={{ padding: 24, marginBottom: 24 }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 16,
          }}
        >
          <Space size={12} wrap>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <FilterOutlined style={{ color: '#64748B' }} />
              <span style={{ color: '#94A3B8', fontWeight: 500 }}>筛选条件:</span>
            </div>
            <Select
              placeholder="选择任务"
              allowClear
              style={{ width: 260 }}
              value={filters.task_id}
              onChange={(value) => setFilters({ ...filters, task_id: value })}
              showSearch
              optionFilterProp="children"
            >
              {tasks.map((task) => (
                <Select.Option key={task.id} value={task.id}>
                  {task.name}
                </Select.Option>
              ))}
            </Select>
            <Select
              placeholder="严重程度"
              allowClear
              style={{ width: 130 }}
              value={filters.severity}
              onChange={(value) => setFilters({ ...filters, severity: value })}
            >
              <Select.Option value="critical">严重</Select.Option>
              <Select.Option value="high">高危</Select.Option>
              <Select.Option value="medium">中危</Select.Option>
              <Select.Option value="low">低危</Select.Option>
              <Select.Option value="info">信息</Select.Option>
            </Select>
            <Select
              placeholder="处理状态"
              allowClear
              style={{ width: 130 }}
              value={filters.status}
              onChange={(value) => setFilters({ ...filters, status: value })}
            >
              <Select.Option value="open">未处理</Select.Option>
              <Select.Option value="in_progress">处理中</Select.Option>
              <Select.Option value="resolved">已解决</Select.Option>
              <Select.Option value="false_positive">误报</Select.Option>
            </Select>
            <Search
              placeholder="搜索漏洞标题"
              style={{ width: 240 }}
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              onSearch={loadVulnerabilities}
              allowClear
              prefix={<SearchOutlined style={{ color: '#64748B' }} />}
            />
          </Space>

          <Button
            icon={<ReloadOutlined />}
            onClick={loadVulnerabilities}
            style={{
              borderRadius: 8,
              background: 'rgba(51, 65, 85, 0.5)',
              borderColor: 'rgba(148, 163, 184, 0.2)',
              color: '#CBD5E1',
            }}
          >
            刷新
          </Button>
        </div>
      </div>

      {/* Table */}
      <div
        style={{
          background: 'rgba(30, 41, 59, 0.6)',
          borderRadius: 16,
          overflow: 'hidden',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
          border: '1px solid rgba(148, 163, 184, 0.1)',
        }}
      >
        <Table
          columns={columns}
          dataSource={vulnerabilities}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 20,
            showTotal: (total) => (
              <span style={{ color: '#64748B' }}>
                共 <strong style={{ color: '#0EA5E9' }}>{total}</strong> 条记录
              </span>
            ),
          }}
          scroll={{ x: 1000 }}
        />
      </div>
    </div>
  )
}

export default Vulnerabilities
