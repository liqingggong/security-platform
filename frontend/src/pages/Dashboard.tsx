import { useEffect, useState } from 'react'
import { Row, Col, Table, Tag, Button, Progress } from 'antd'
import {
  DatabaseOutlined,
  BugOutlined,
  SyncOutlined,
  GlobalOutlined,
  AlertOutlined,
  SafetyOutlined,
  ArrowRightOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { assetsAPI, vulnerabilitiesAPI, tasksAPI } from '../utils/api'
import { useNavigate } from 'react-router-dom'
import { DashboardSkeleton } from '../components/PageSkeleton'

const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [assetStats, setAssetStats] = useState<any>({})
  const [vulnStats, setVulnStats] = useState<any>({})
  const [recentTasks, setRecentTasks] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [assets, vulns, tasks] = await Promise.all([
        assetsAPI.getStats(),
        vulnerabilitiesAPI.getStats(),
        tasksAPI.list({ limit: 5 }),
      ])
      setAssetStats(assets)
      setVulnStats(vulns)
      setRecentTasks(Array.isArray(tasks) ? tasks : [])
    } catch (error) {
      console.error('加载数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 显示骨架屏避免白屏
  if (loading && !assetStats.total) {
    return <DashboardSkeleton />
  }

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string; bgColor: string }> = {
      pending: { color: '#94A3B8', text: '等待中', bgColor: 'rgba(148, 163, 184, 0.15)' },
      running: { color: '#0EA5E9', text: '运行中', bgColor: 'rgba(14, 165, 233, 0.15)' },
      completed: { color: '#22C55E', text: '已完成', bgColor: 'rgba(34, 197, 94, 0.15)' },
      failed: { color: '#EF4444', text: '失败', bgColor: 'rgba(239, 68, 68, 0.15)' },
      cancelled: { color: '#F97316', text: '已取消', bgColor: 'rgba(249, 115, 22, 0.15)' },
    }
    const config = statusMap[status] || { color: '#94A3B8', text: status, bgColor: 'rgba(148, 163, 184, 0.15)' }
    return (
      <Tag
        style={{
          background: config.bgColor,
          color: config.color,
          border: 'none',
          borderRadius: 6,
          fontWeight: 500,
          padding: '4px 12px',
        }}
      >
        {config.text}
      </Tag>
    )
  }

  const getSeverityBadge = (severity: string) => {
    const severityMap: Record<string, { color: string; bgColor: string; label: string }> = {
      critical: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', label: '严重' },
      high: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', label: '高危' },
      medium: { color: '#F97316', bgColor: 'rgba(249, 115, 22, 0.15)', label: '中危' },
      low: { color: '#0EA5E9', bgColor: 'rgba(14, 165, 233, 0.15)', label: '低危' },
    }
    const config = severityMap[severity] || { color: '#94A3B8', bgColor: 'rgba(148, 163, 184, 0.15)', label: '信息' }
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

  const taskColumns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <span style={{ fontWeight: 500, color: '#F8FAFC' }}>{name}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 120,
      render: (progress: number, record: any) =>
        record.status === 'running' ? (
          <Progress
            percent={progress}
            size="small"
            strokeColor={{ '0%': '#0EA5E9', '100%': '#22C55E' }}
            showInfo={false}
          />
        ) : (
          <span style={{ color: '#64748B', fontSize: 13 }}>{progress}%</span>
        ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#64748B', fontSize: 13 }}>
          <ClockCircleOutlined />
          {new Date(time).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
        </div>
      ),
    },
    {
      title: '',
      key: 'action',
      width: 60,
      render: (_: any, record: any) => (
        <Button
          type="text"
          icon={<ArrowRightOutlined />}
          onClick={() => navigate(`/tasks/${record.id}`)}
          style={{ color: '#0EA5E9' }}
        />
      ),
    },
  ]

  const StatCard = ({
    icon,
    iconBg,
    title,
    value,
    color,
    trend,
    onClick,
  }: {
    icon: React.ReactNode
    iconBg: string
    title: string
    value: number
    color: string
    trend?: string
    onClick?: () => void
  }) => (
    <div
      className="stat-card"
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      <div
        className="stat-icon"
        style={{
          background: iconBg,
          color: color,
        }}
      >
        {icon}
      </div>
      <div className="stat-value" style={{ color }}>
        {value?.toLocaleString() || 0}
      </div>
      <div className="stat-label">{title}</div>
      {trend && (
        <div
          style={{
            marginTop: 8,
            fontSize: 12,
            color: '#22C55E',
            fontWeight: 500,
          }}
        >
          {trend}
        </div>
      )}
    </div>
  )

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">仪表盘</h1>
        <p className="page-subtitle">实时监控资产状况与安全态势</p>
      </div>

      {/* Stats Cards */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            icon={<DatabaseOutlined />}
            iconBg="linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(56, 189, 248, 0.2) 100%)"
            title="总资产数"
            value={assetStats.total || 0}
            color="#0EA5E9"
            trend="+12% 较上周"
            onClick={() => navigate('/assets')}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            icon={<GlobalOutlined />}
            iconBg="linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(129, 140, 248, 0.2) 100%)"
            title="域名资产"
            value={assetStats.by_type?.subdomain || 0}
            color="#818CF8"
            onClick={() => navigate('/domains')}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            icon={<BugOutlined />}
            iconBg="linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(248, 113, 113, 0.2) 100%)"
            title="总漏洞数"
            value={vulnStats.total || 0}
            color="#F87171"
            trend="需关注"
            onClick={() => navigate('/vulnerabilities')}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            icon={<SyncOutlined spin />}
            iconBg="linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(74, 222, 128, 0.2) 100%)"
            title="运行中任务"
            value={recentTasks.filter((t: any) => t.status === 'running').length}
            color="#22C55E"
            onClick={() => navigate('/tasks')}
          />
        </Col>
      </Row>

      {/* Charts Row */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        {/* Asset Distribution */}
        <Col xs={24} lg={12}>
          <div className="glass-card" style={{ padding: 24 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 24,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 10,
                    background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(56, 189, 248, 0.2) 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#0EA5E9',
                  }}
                >
                  <DatabaseOutlined />
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                    资产类型分布
                  </div>
                  <div style={{ fontSize: 12, color: '#64748B' }}>按资产类别统计</div>
                </div>
              </div>
              <Button type="text" icon={<ArrowRightOutlined />} onClick={() => navigate('/assets')} style={{ color: '#0EA5E9' }}>
                查看全部
              </Button>
            </div>

            <Row gutter={[16, 16]}>
              {assetStats.by_type ?
                Object.entries(assetStats.by_type).map(([type, count]: [string, any]) => (
                  <Col span={12} key={type}>
                    <div
                      style={{
                        padding: 16,
                        background: 'rgba(51, 65, 85, 0.5)',
                        borderRadius: 12,
                        border: '1px solid rgba(148, 163, 184, 0.1)',
                      }}
                    >
                      <div
                        style={{
                          fontSize: 12,
                          color: '#94A3B8',
                          textTransform: 'uppercase',
                          letterSpacing: 0.5,
                          marginBottom: 8,
                        }}
                      >
                        {type === 'ip'
                          ? 'IP 地址'
                          : type === 'subdomain'
                            ? '子域名'
                            : type === 'endpoint'
                              ? '端点'
                              : type}
                      </div>
                      <div style={{ fontSize: 24, fontWeight: 700, color: '#F8FAFC' }}>
                        {count.toLocaleString()}
                      </div>
                    </div>
                  </Col>
                )) : (
                  <Col span={24}>
                    <div style={{ textAlign: 'center', padding: 40, color: '#64748B' }}>
                      暂无数据
                    </div>
                  </Col>
                )}
            </Row>
          </div>
        </Col>

        {/* Vulnerability Distribution */}
        <Col xs={24} lg={12}>
          <div className="glass-card" style={{ padding: 24 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 24,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 10,
                    background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(248, 113, 113, 0.2) 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#F87171',
                  }}
                >
                  <AlertOutlined />
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                    漏洞严重程度分布
                  </div>
                  <div style={{ fontSize: 12, color: '#64748B' }}>按风险等级统计</div>
                </div>
              </div>
              <Button type="text" icon={<ArrowRightOutlined />} onClick={() => navigate('/vulnerabilities')} style={{ color: '#F87171' }}>
                查看全部
              </Button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {vulnStats.by_severity ?
                Object.entries(vulnStats.by_severity).map(([severity, count]: [string, any]) => (
                  <div
                    key={severity}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                      padding: 12,
                      background: 'rgba(51, 65, 85, 0.5)',
                      borderRadius: 10,
                      border: '1px solid rgba(148, 163, 184, 0.1)',
                    }}
                  >
                    {getSeverityBadge(severity)}
                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          height: 6,
                          background: 'rgba(51, 65, 85, 0.8)',
                          borderRadius: 3,
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            height: '100%',
                            width: `${Math.min((count / (vulnStats.total || 1)) * 100, 100)}%`,
                            background:
                              severity === 'critical' || severity === 'high'
                                ? '#EF4444'
                                : severity === 'medium'
                                  ? '#F97316'
                                  : '#0EA5E9',
                            borderRadius: 3,
                            transition: 'width 0.5s ease',
                          }}
                        />
                      </div>
                    </div>
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 600,
                        color: '#F8FAFC',
                        minWidth: 50,
                        textAlign: 'right',
                      }}
                    >
                      {count.toLocaleString()}
                    </div>
                  </div>
                )) : (
                  <div style={{ textAlign: 'center', padding: 40, color: '#64748B' }}>
                    暂无数据
                  </div>
                )}
            </div>
          </div>
        </Col>
      </Row>

      {/* Recent Tasks */}
      <div className="glass-card" style={{ padding: 24 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 24,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(74, 222, 128, 0.2) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#22C55E',
              }}
            >
              <SafetyOutlined />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                最近任务
              </div>
              <div style={{ fontSize: 12, color: '#64748B' }}>最新的扫描任务状态</div>
            </div>
          </div>
          <Button
            type="primary"
            onClick={() => navigate('/tasks')}
            style={{
              background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
              border: 'none',
              borderRadius: 8,
            }}
          >
            查看全部任务
          </Button>
        </div>

        <Table
          columns={taskColumns}
          dataSource={recentTasks}
          rowKey="id"
          pagination={false}
          loading={loading}
          style={{ background: 'transparent' }}
        />
      </div>
    </div>
  )
}

export default Dashboard
