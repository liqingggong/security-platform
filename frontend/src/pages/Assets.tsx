import { Table, Select, Button, Space, message, Input, Modal, InputNumber, Tag, Tooltip } from 'antd'
import { ReloadOutlined, DownloadOutlined, SearchOutlined, EyeOutlined, LinkOutlined, FilterOutlined } from '@ant-design/icons'
import { assetsAPI, tasksAPI } from '../utils/api'
import dayjs from 'dayjs'
import { useState, useEffect, useRef } from 'react'
import { TablePageSkeleton } from '../components/PageSkeleton'

const Assets = () => {
  const [assets, setAssets] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedTaskId, setSelectedTaskId] = useState<number | undefined>(undefined)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [searchText, setSearchText] = useState<string>('')
  const [exportModalVisible, setExportModalVisible] = useState(false)
  const [exportLimit, setExportLimit] = useState(10000)

  // Use ref to track latest values without triggering re-renders
  const latestSearchText = useRef(searchText)
  const latestSelectedTaskId = useRef(selectedTaskId)

  useEffect(() => {
    latestSearchText.current = searchText
  }, [searchText])

  useEffect(() => {
    latestSelectedTaskId.current = selectedTaskId
  }, [selectedTaskId])

  const loadAssets = async (page: number, size: number) => {
    const taskId = latestSelectedTaskId.current
    if (!taskId) {
      setAssets([])
      return
    }

    setLoading(true)
    try {
      const skip = (page - 1) * size
      const limit = size
      const params: any = { task_id: taskId, skip, limit }
      const search = latestSearchText.current
      if (search) {
        params.search = search
      }
      console.log('[Assets Debug] Request:', { page, size, skip, limit, taskId })
      const resp = await assetsAPI.list(params)
      console.log('[Assets Debug] Response:', { items: resp?.items?.length, total: resp?.total })
      const items = Array.isArray(resp?.items) ? resp.items : []
      setAssets(items)
      setTotal(typeof resp?.total === 'number' ? resp.total : items.length)
    } catch (error) {
      console.error('[Assets Debug] Error:', error)
      message.error('加载资产列表失败')
    } finally {
      setLoading(false)
    }
  }

  // Load tasks on mount
  useEffect(() => {
    loadTasks()
  }, [])

  // Load assets when task changes
  useEffect(() => {
    if (!selectedTaskId) {
      setAssets([])
      setTotal(0)
      setCurrentPage(1)
      return
    }
    setCurrentPage(1)
    loadAssets(1, pageSize)
  }, [selectedTaskId])

  // Load assets when search text changes
  useEffect(() => {
    if (!selectedTaskId) return
    const timer = setTimeout(() => {
      setCurrentPage(1)
      loadAssets(1, pageSize)
    }, 500)
    return () => clearTimeout(timer)
  }, [searchText, selectedTaskId])

  const loadTasks = async () => {
    try {
      const data = await tasksAPI.list()
      setTasks(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载任务列表失败')
    }
  }

  const handleSearch = () => {
    setCurrentPage(1)
    loadAssets(1, pageSize)
  }

  const handlePageChange = (page: number, newPageSize?: number) => {
    const size = newPageSize ?? pageSize
    setCurrentPage(page)
    if (newPageSize) {
      setPageSize(newPageSize)
    }
    loadAssets(page, size)
  }

  const handleExport = () => {
    if (!selectedTaskId) {
      message.warning('请先选择任务')
      return
    }
    setExportModalVisible(true)
  }

  const exportAssets = async (format: 'csv' | 'xlsx') => {
    if (!selectedTaskId) {
      message.warning('请先选择任务')
      return
    }

    setLoading(true)
    try {
      const resp = await assetsAPI.list({
        task_id: selectedTaskId,
        skip: 0,
        limit: exportLimit,
        search: searchText || undefined
      })
      const items = Array.isArray(resp?.items) ? resp.items : []
      if (items.length === 0) {
        message.warning('没有可导出的资产')
        setExportModalVisible(false)
        setLoading(false)
        return
      }

      const headers = ['序号', '来源', '域名', 'URL', 'IP', '端口', '协议', '指纹', '发现时间']
      const rows = items.map((item: any, index: number) => {
        const discoveredBy = item?.discovered_by || {}
        const sourceList: string[] = []

        for (const [source] of Object.entries(discoveredBy)) {
          sourceList.push(source.toUpperCase())
        }

        if (sourceList.length === 0) {
          const sources: string[] = Array.isArray(item?.sources) ? item.sources : []
          for (const s of sources) {
            if (s === 'fofa' || s === 'hunter' || s === 'subfinder') {
              sourceList.push(s.toUpperCase())
            }
          }
        }

        return [
          index + 1,
          sourceList.join('+') || '-',
          item.domain || '-',
          item.url || '-',
          item.ip_address || '-',
          item.port || '-',
          item.protocol || '-',
          item.product || '-',
          item.discovered_at ? dayjs(item.discovered_at).format('YYYY-MM-DD HH:mm:ss') : '-',
        ]
      })

      if (format === 'csv') {
        const csvContent = [
          headers.join(','),
          ...rows.map((row: any[]) => row.map((cell: any) => `"${String(cell).replace(/"/g, '""')}"`).join(',')),
        ].join('\n')

        const BOM = '\uFEFF'
        const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
        const link = document.createElement('a')
        const url = URL.createObjectURL(blob)
        link.setAttribute('href', url)
        link.setAttribute('download', `资产列表_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.csv`)
        link.style.visibility = 'hidden'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
      } else if (format === 'xlsx') {
        const XLSX = await import('xlsx')
        const ws = XLSX.utils.aoa_to_sheet([headers, ...rows])
        const wb = XLSX.utils.book_new()
        XLSX.utils.book_append_sheet(wb, ws, 'Assets')
        const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' })
        const blob = new Blob([wbout], { type: 'application/octet-stream' })
        const a = document.createElement('a')
        const url = URL.createObjectURL(blob)
        a.href = url
        a.download = `资产列表_${dayjs().format('YYYY-MM-DD_HH-mm-ss')}.xlsx`
        a.click()
        URL.revokeObjectURL(url)
      }

      message.success(`成功导出 ${items.length} 条资产`)
      setExportModalVisible(false)
      setLoading(false)
    } catch (error) {
      message.error('导出失败')
      setExportModalVisible(false)
      setLoading(false)
    }
  }

  const getSourceTag = (record: any) => {
    const discoveredBy = record?.discovered_by || {}
    const sourceList: string[] = []

    for (const [source] of Object.entries(discoveredBy)) {
      sourceList.push(source.toUpperCase())
    }

    if (sourceList.length === 0) {
      const sources: string[] = Array.isArray(record?.sources) ? record.sources : []
      for (const s of sources) {
        if (s === 'fofa' || s === 'hunter' || s === 'subfinder') {
          sourceList.push(s.toUpperCase())
        }
      }
    }

    if (sourceList.length === 0) return <span style={{ color: '#64748B' }}>-</span>

    const sourceColors: Record<string, string> = {
      FOFA: '#0EA5E9',
      HUNTER: '#818CF8',
      SUBFINDER: '#22C55E',
    }

    return (
      <Space size={4}>
        {sourceList.map((source) => (
          <Tag
            key={source}
            style={{
              background: `${sourceColors[source] || '#64748B'}20`,
              color: sourceColors[source] || '#64748B',
              border: 'none',
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 600,
              padding: '2px 8px',
            }}
          >
            {source}
          </Tag>
        ))}
      </Space>
    )
  }

  if (loading && tasks.length === 0) {
    return <TablePageSkeleton />
  }

  const columns = [
    {
      title: '序号',
      key: 'index',
      width: 70,
      align: 'center' as const,
      render: (_: any, __: any, index: number) => (
        <span style={{ color: '#64748B', fontSize: 13 }}>
          {(currentPage - 1) * pageSize + index + 1}
        </span>
      ),
    },
    {
      title: '来源',
      key: 'source',
      width: 140,
      render: (_: any, record: any) => getSourceTag(record),
    },
    {
      title: '域名',
      dataIndex: 'domain',
      key: 'domain',
      ellipsis: true,
      render: (domain: string) => (
        <span style={{ fontWeight: 500, color: '#F8FAFC' }}>
          {domain || '-'}
        </span>
      ),
    },
    {
      title: 'URL',
      key: 'url',
      ellipsis: true,
      render: (_: any, record: any) => {
        // 优先使用 url 字段，如果没有则尝试从 domain/port/protocol 组合生成
        let url = record?.url
        if (!url && record?.domain && record?.port) {
          const protocol = record?.protocol || 'http'
          url = `${protocol}://${record.domain}:${record.port}`
        }

        return url ? (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: '#0EA5E9',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {url}
            <LinkOutlined style={{ fontSize: 12 }} />
          </a>
        ) : (
          <span style={{ color: '#64748B' }}>-</span>
        )
      },
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (ip: string) => (
        <Tag
          style={{
            background: 'rgba(51, 65, 85, 0.8)',
            color: '#CBD5E1',
            border: '1px solid rgba(148, 163, 184, 0.2)',
            borderRadius: 6,
            fontFamily: 'monospace',
            fontSize: 13,
          }}
        >
          {ip || '-'}
        </Tag>
      ),
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 80,
      align: 'center' as const,
      render: (port: any) => {
        const p = typeof port === 'number' && port !== 0 ? String(port) : '-'
        return (
          <span
            style={{
              fontWeight: 600,
              color: p === '-' ? '#64748B' : '#0EA5E9',
            }}
          >
            {p}
          </span>
        )
      },
    },
    {
      title: '协议',
      dataIndex: 'protocol',
      key: 'protocol',
      width: 90,
      render: (protocol: string) =>
        protocol ? (
          <Tag
            style={{
              background: 'rgba(14, 165, 233, 0.15)',
              color: '#0EA5E9',
              border: 'none',
              borderRadius: 6,
              fontWeight: 600,
              fontSize: 12,
            }}
          >
            {protocol.toUpperCase()}
          </Tag>
        ) : (
          <span style={{ color: '#64748B' }}>-</span>
        ),
    },
    {
      title: '指纹',
      dataIndex: 'product',
      key: 'product',
      ellipsis: true,
      render: (product: string) =>
        product ? (
          <Tooltip title={product}>
            <Tag
              style={{
                background: 'rgba(34, 197, 94, 0.15)',
                color: '#22C55E',
                border: 'none',
                borderRadius: 6,
                fontSize: 12,
              }}
            >
              {product}
            </Tag>
          </Tooltip>
        ) : (
          <span style={{ color: '#64748B' }}>-</span>
        ),
    },
    {
      title: '发现时间',
      dataIndex: 'discovered_at',
      key: 'discovered_at',
      width: 160,
      render: (_: any, record: any) => {
        const t = record?.fofa_discovered_at || record?.hunter_discovered_at || record?.subfinder_discovered_at || record?.discovered_at
        return t ? (
          <span style={{ color: '#94A3B8', fontSize: 13 }}>
            {dayjs(t).format('YYYY-MM-DD HH:mm')}
          </span>
        ) : (
          <span style={{ color: '#64748B' }}>-</span>
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      align: 'center' as const,
      render: () => (
        <Tooltip title="查看详情">
          <Button
            type="text"
            icon={<EyeOutlined />}
            style={{
              color: '#0EA5E9',
              width: 32,
              height: 32,
              borderRadius: 8,
            }}
            onClick={() => {
              message.info('查看资产详情功能开发中')
            }}
          />
        </Tooltip>
      ),
    },
  ]

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">资产管理</h1>
        <p className="page-subtitle">查看和管理所有扫描发现的资产</p>
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
              <span style={{ color: '#94A3B8', fontWeight: 500 }}>任务筛选:</span>
            </div>
            <Select
              placeholder="选择任务"
              allowClear
              style={{ width: 280 }}
              value={selectedTaskId}
              onChange={(value) => setSelectedTaskId(value)}
              showSearch
              optionFilterProp="children"
              size="middle"
            >
              {tasks.map((task) => (
                <Select.Option key={task.id} value={task.id}>
                  {task.name}
                </Select.Option>
              ))}
            </Select>

            <Input
              placeholder="搜索域名、IP、URL"
              style={{ width: 260 }}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onPressEnter={handleSearch}
              allowClear
              prefix={<SearchOutlined style={{ color: '#64748B' }} />}
              size="middle"
            />
          </Space>

          <Space size={12}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => loadAssets(currentPage, pageSize)}
              disabled={!selectedTaskId}
              style={{
                borderRadius: 8,
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#CBD5E1',
              }}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExport}
              disabled={!selectedTaskId}
              style={{
                borderRadius: 8,
                background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                border: 'none',
              }}
            >
              导出数据
            </Button>
          </Space>
        </div>

        {/* Stats Summary */}
        {selectedTaskId && (
          <div
            style={{
              display: 'flex',
              gap: 24,
              marginTop: 20,
              paddingTop: 20,
              borderTop: '1px solid rgba(148, 163, 184, 0.1)',
            }}
          >
            <div>
              <span style={{ color: '#64748B', fontSize: 13 }}>总记录: </span>
              <span style={{ color: '#0EA5E9', fontWeight: 700, fontSize: 18 }}>
                {total.toLocaleString()}
              </span>
            </div>
            <div>
              <span style={{ color: '#64748B', fontSize: 13 }}>当前页: </span>
              <span style={{ color: '#CBD5E1', fontWeight: 600 }}>
                {assets.length} 条
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Data Table */}
      {!selectedTaskId ? (
        <div
          style={{
            textAlign: 'center',
            padding: 80,
            background: 'rgba(30, 41, 59, 0.5)',
            borderRadius: 16,
            border: '1px dashed rgba(148, 163, 184, 0.2)',
          }}
        >
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: 20,
              background: 'linear-gradient(135deg, rgba(51, 65, 85, 0.8) 0%, rgba(71, 85, 105, 0.8) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 24px',
            }}
          >
            <FilterOutlined style={{ fontSize: 32, color: '#64748B' }} />
          </div>
          <h3 style={{ color: '#CBD5E1', marginBottom: 8 }}>请先选择任务</h3>
          <p style={{ color: '#64748B' }}>选择一个扫描任务以查看相关资产数据</p>
        </div>
      ) : (
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
            dataSource={assets}
            rowKey="id"
            loading={loading}
            pagination={{
              current: currentPage,
              pageSize: pageSize,
              total,
              showTotal: (t) => (
                <span style={{ color: '#64748B' }}>
                  共 <strong style={{ color: '#0EA5E9' }}>{t}</strong> 条记录
                </span>
              ),
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              onChange: handlePageChange,
            }}
            scroll={{ x: 1200 }}
            style={{ background: 'transparent' }}
          />
        </div>
      )}

      {/* Export Modal */}
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(56, 189, 248, 0.2) 100%)',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <DownloadOutlined style={{ color: '#0EA5E9' }} />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>导出资产</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>选择导出格式和数量限制</div>
            </div>
          </div>
        }
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={null}
        width={480}
      >
        <Space direction="vertical" style={{ width: '100%', marginTop: 24 }} size={20}>
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8, color: '#CBD5E1' }}>
              导出数量限制
            </div>
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              max={100000}
              step={1000}
              value={exportLimit}
              onChange={(value) => setExportLimit(value || 10000)}
              formatter={(value) => `${value?.toLocaleString()} 条`}
              parser={(value) => parseInt(value?.replace(/[^\d]/g, '') || '10000', 10)}
              size="large"
            />
            <div style={{ color: '#64748B', fontSize: 12, marginTop: 8 }}>
              大数据量导出可能需要较长时间，建议分批导出
            </div>
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <Button
              size="large"
              style={{ flex: 1, borderRadius: 8 }}
              onClick={() => setExportModalVisible(false)}
            >
              取消
            </Button>
            <Button
              size="large"
              style={{ flex: 1, borderRadius: 8 }}
              onClick={() => exportAssets('csv')}
              loading={loading}
            >
              导出 CSV
            </Button>
            <Button
              type="primary"
              size="large"
              style={{
                flex: 1,
                borderRadius: 8,
                background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                border: 'none',
              }}
              onClick={() => exportAssets('xlsx')}
              loading={loading}
            >
              导出 Excel
            </Button>
          </div>
        </Space>
      </Modal>
    </div>
  )
}

export default Assets
