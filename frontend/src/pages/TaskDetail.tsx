import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Descriptions,
  Tag,
  Progress,
  Tabs,
  Button,
  message,
  Popconfirm,
  Space,
  Typography,
  List,
  Select,
} from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { tasksAPI } from '../utils/api'
import dayjs from 'dayjs'

const { Title, Paragraph } = Typography

const TaskDetail = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [task, setTask] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState<any[]>([])
  const [logsLoading, setLogsLoading] = useState(false)
  const [selectedPhase, setSelectedPhase] = useState<string | undefined>(undefined)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    if (id) {
      loadTask()
      loadLogs()
      if (autoRefresh) {
        const interval = setInterval(() => {
          if (task?.status === 'running') {
            loadTask()
            loadLogs()
          }
        }, 5000)
        return () => clearInterval(interval)
      }
    }
  }, [id, task?.status, autoRefresh])

  useEffect(() => {
    loadLogs()
  }, [selectedPhase])

  const loadTask = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await tasksAPI.get(Number(id))
      setTask(data)
    } catch (error) {
      message.error('加载任务详情失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = async () => {
    if (!id) return
    try {
      await tasksAPI.cancel(Number(id))
      message.success('任务已取消')
      loadTask()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '取消任务失败')
    }
  }

  const loadLogs = async () => {
    if (!id) return
    setLogsLoading(true)
    try {
      const data = await tasksAPI.getLogs(Number(id), selectedPhase ? { phase: selectedPhase } : undefined)
      setLogs(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载任务日志失败')
    } finally {
      setLogsLoading(false)
    }
  }

  const phaseOptions = useMemo(() => {
    const phases = Array.from(new Set(logs.map((l) => l.phase)))
    return phases.map((p) => ({ label: p, value: p }))
  }, [logs])

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; bgColor: string; text: string }> = {
      pending: { color: '#94A3B8', bgColor: 'rgba(148, 163, 184, 0.15)', text: '等待中' },
      running: { color: '#0EA5E9', bgColor: 'rgba(14, 165, 233, 0.15)', text: '运行中' },
      completed: { color: '#22C55E', bgColor: 'rgba(34, 197, 94, 0.15)', text: '已完成' },
      failed: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', text: '失败' },
      cancelled: { color: '#F97316', bgColor: 'rgba(249, 115, 22, 0.15)', text: '已取消' },
    }
    const config = statusMap[status] || { color: '#94A3B8', bgColor: 'rgba(148, 163, 184, 0.15)', text: status }
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

  if (!task) {
    return (
      <div style={{ color: '#94A3B8', textAlign: 'center', padding: 50 }}>
        加载中...
      </div>
    )
  }

  const inputData = task.input_data || {}
  const outputData = task.output_data || {}

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">任务详情</h1>
        <p className="page-subtitle">查看任务执行状态和结果</p>
      </div>

      <Space style={{ marginBottom: 24 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/tasks')}
          style={{
            borderRadius: 8,
            background: 'rgba(51, 65, 85, 0.5)',
            borderColor: 'rgba(148, 163, 184, 0.2)',
            color: '#CBD5E1',
          }}
        >
          返回
        </Button>
        <Button
          type={autoRefresh ? 'primary' : 'default'}
          onClick={() => setAutoRefresh(!autoRefresh)}
          style={{
            borderRadius: 8,
            background: autoRefresh ? 'rgba(34, 197, 94, 0.2)' : 'rgba(51, 65, 85, 0.5)',
            borderColor: autoRefresh ? '#22C55E' : 'rgba(148, 163, 184, 0.2)',
            color: autoRefresh ? '#22C55E' : '#CBD5E1',
          }}
        >
          {autoRefresh ? '停止自动刷新' : '开启自动刷新'}
        </Button>
        {['pending', 'running'].includes(task.status) && (
          <Popconfirm
            title="确定要取消这个任务吗？"
            onConfirm={handleCancel}
          >
            <Button
              danger
              style={{
                borderRadius: 8,
              }}
            >
              取消任务
            </Button>
          </Popconfirm>
        )}
      </Space>

      <Card
        loading={loading}
        style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(148, 163, 184, 0.1)',
          borderRadius: 16,
        }}
        headStyle={{
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
        }}
      >
        <Title level={2} style={{ color: '#F8FAFC', marginTop: 0 }}>
          {task.name}
        </Title>
        <Paragraph style={{ color: '#94A3B8' }}>
          {task.description || '无描述'}
        </Paragraph>

        <Descriptions
          bordered
          column={2}
          style={{ marginTop: 24 }}
          labelStyle={{
            color: '#94A3B8',
            background: 'rgba(51, 65, 85, 0.5)',
          }}
          contentStyle={{
            color: '#CBD5E1',
            background: 'rgba(30, 41, 59, 0.4)',
          }}
        >
          <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
          <Descriptions.Item label="状态">{getStatusTag(task.status)}</Descriptions.Item>
          <Descriptions.Item label="进度" span={2}>
            <Progress
              percent={task.progress}
              strokeColor={{
                '0%': '#0EA5E9',
                '100%': task.status === 'completed' ? '#22C55E' : '#0EA5E9',
              }}
            />
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          {task.started_at && (
            <Descriptions.Item label="开始时间">
              {dayjs(task.started_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          )}
          {task.completed_at && (
            <Descriptions.Item label="完成时间">
              {dayjs(task.completed_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
          )}
        </Descriptions>

        {task.error && (
          <Card
            title={<span style={{ color: '#EF4444' }}>错误信息</span>}
            style={{
              marginTop: 24,
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
            }}
            type="inner"
            headStyle={{
              background: 'rgba(239, 68, 68, 0.1)',
              borderBottom: '1px solid rgba(239, 68, 68, 0.2)',
            }}
          >
            <Typography.Text type="danger" style={{ color: '#F87171' }}>
              {task.error}
            </Typography.Text>
          </Card>
        )}

        <Tabs
          defaultActiveKey="input"
          items={[
            {
              key: 'input',
              label: <span style={{ color: '#CBD5E1' }}>输入参数</span>,
              children: (
                <div>
                  <Card
                    title={<span style={{ color: '#F8FAFC' }}>根域名</span>}
                    size="small"
                    style={{
                      marginBottom: 16,
                      background: 'rgba(51, 65, 85, 0.3)',
                      border: '1px solid rgba(148, 163, 184, 0.1)',
                    }}
                    headStyle={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}
                  >
                    {inputData.root_domains?.length > 0 ? (
                      <ul style={{ color: '#CBD5E1', paddingLeft: 20 }}>
                        {inputData.root_domains.map((d: string, i: number) => (
                          <li key={i}>{d}</li>
                        ))}
                      </ul>
                    ) : (
                      <span style={{ color: '#64748B' }}>无</span>
                    )}
                  </Card>
                  <Card
                    title={<span style={{ color: '#F8FAFC' }}>IP 地址</span>}
                    size="small"
                    style={{
                      marginBottom: 16,
                      background: 'rgba(51, 65, 85, 0.3)',
                      border: '1px solid rgba(148, 163, 184, 0.1)',
                    }}
                    headStyle={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}
                  >
                    {inputData.ips?.length > 0 ? (
                      <ul style={{ color: '#CBD5E1', paddingLeft: 20 }}>
                        {inputData.ips.map((ip: string, i: number) => (
                          <li key={i}>{ip}</li>
                        ))}
                      </ul>
                    ) : (
                      <span style={{ color: '#64748B' }}>无</span>
                    )}
                  </Card>
                  <Card
                    title={<span style={{ color: '#F8FAFC' }}>FOFA 查询</span>}
                    size="small"
                    style={{
                      marginBottom: 16,
                      background: 'rgba(51, 65, 85, 0.3)',
                      border: '1px solid rgba(148, 163, 184, 0.1)',
                    }}
                    headStyle={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}
                  >
                    {inputData.fofa_query ? (
                      <Tag
                        style={{
                          background: 'rgba(14, 165, 233, 0.15)',
                          color: '#0EA5E9',
                          border: 'none',
                          borderRadius: 6,
                          fontFamily: 'monospace',
                        }}
                      >
                        {inputData.fofa_query}
                      </Tag>
                    ) : (
                      <span style={{ color: '#64748B' }}>无</span>
                    )}
                  </Card>
                  <Card
                    title={<span style={{ color: '#F8FAFC' }}>Hunter 查询</span>}
                    size="small"
                    style={{
                      marginBottom: 16,
                      background: 'rgba(51, 65, 85, 0.3)',
                      border: '1px solid rgba(148, 163, 184, 0.1)',
                    }}
                    headStyle={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}
                  >
                    {inputData.hunter_query ? (
                      <Tag
                        style={{
                          background: 'rgba(129, 140, 248, 0.15)',
                          color: '#818CF8',
                          border: 'none',
                          borderRadius: 6,
                          fontFamily: 'monospace',
                        }}
                      >
                        {inputData.hunter_query}
                      </Tag>
                    ) : (
                      <span style={{ color: '#64748B' }}>无</span>
                    )}
                  </Card>
                  <Card
                    title={<span style={{ color: '#F8FAFC' }}>启用的工具</span>}
                    size="small"
                    style={{
                      background: 'rgba(51, 65, 85, 0.3)',
                      border: '1px solid rgba(148, 163, 184, 0.1)',
                    }}
                    headStyle={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}
                  >
                    <Space>
                      {inputData.enable?.fofa && (
                        <Tag style={{ background: 'rgba(14, 165, 233, 0.15)', color: '#0EA5E9', border: 'none', borderRadius: 6 }}>
                          FOFA
                        </Tag>
                      )}
                      {inputData.enable?.hunter && (
                        <Tag style={{ background: 'rgba(129, 140, 248, 0.15)', color: '#818CF8', border: 'none', borderRadius: 6 }}>
                          Hunter
                        </Tag>
                      )}
                      {inputData.enable?.subfinder && (
                        <Tag style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#22C55E', border: 'none', borderRadius: 6 }}>
                          Subfinder
                        </Tag>
                      )}
                      {inputData.enable?.nmap && (
                        <Tag style={{ background: 'rgba(249, 115, 22, 0.15)', color: '#F97316', border: 'none', borderRadius: 6 }}>
                          Nmap
                        </Tag>
                      )}
                      {inputData.enable?.httpx && (
                        <Tag style={{ background: 'rgba(14, 165, 233, 0.15)', color: '#0EA5E9', border: 'none', borderRadius: 6 }}>
                          HTTPX
                        </Tag>
                      )}
                      {inputData.enable?.nuclei && (
                        <Tag style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#F87171', border: 'none', borderRadius: 6 }}>
                          Nuclei
                        </Tag>
                      )}
                      {inputData.enable?.naabu && (
                        <Tag style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#A855F7', border: 'none', borderRadius: 6 }}>
                          Naabu
                        </Tag>
                      )}
                    </Space>
                  </Card>
                </div>
              ),
            },
            {
              key: 'output',
              label: <span style={{ color: '#CBD5E1' }}>执行结果</span>,
              children: (
                <div>
                  {outputData.summary ? (
                    <Card
                      title={<span style={{ color: '#F8FAFC' }}>执行摘要</span>}
                      style={{
                        marginBottom: 16,
                        background: 'rgba(51, 65, 85, 0.3)',
                        border: '1px solid rgba(148, 163, 184, 0.1)',
                      }}
                      headStyle={{ borderBottom: '1px solid rgba(148, 163, 184, 0.1)' }}
                    >
                      <Descriptions
                        column={2}
                        bordered
                        labelStyle={{
                          color: '#94A3B8',
                          background: 'rgba(51, 65, 85, 0.5)',
                        }}
                        contentStyle={{
                          color: '#CBD5E1',
                          background: 'rgba(30, 41, 59, 0.4)',
                        }}
                      >
                        <Descriptions.Item label="发现资产数">
                          <span style={{ color: '#0EA5E9', fontWeight: 600 }}>
                            {outputData.summary.total_assets_discovered || 0}
                          </span>
                        </Descriptions.Item>
                        <Descriptions.Item label="发现漏洞数">
                          <span style={{ color: '#EF4444', fontWeight: 600 }}>
                            {outputData.summary.total_vulnerabilities_found || 0}
                          </span>
                        </Descriptions.Item>
                        <Descriptions.Item label="FOFA 记录">
                          {outputData.summary.fofa_records || 0}
                        </Descriptions.Item>
                        <Descriptions.Item label="Hunter 记录">
                          {outputData.summary.hunter_records || 0}
                        </Descriptions.Item>
                        <Descriptions.Item label="子域名数">
                          {outputData.summary.subfinder_subdomains || 0}
                        </Descriptions.Item>
                        <Descriptions.Item label="Subfinder 记录">
                          {outputData.summary.subfinder_records || 0}
                        </Descriptions.Item>
                        <Descriptions.Item label="Nmap IP数">
                          {outputData.summary.nmap_ips || 0}
                        </Descriptions.Item>
                        <Descriptions.Item label="HTTPX 存活">
                          {outputData.summary.httpx_alive || 0}
                        </Descriptions.Item>
                        <Descriptions.Item label="Nuclei 发现">
                          {outputData.summary.nuclei_findings || 0}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>
                  ) : (
                    <div style={{ textAlign: 'center', color: '#64748B', padding: 40 }}>
                      暂无执行结果
                    </div>
                  )}
                </div>
              ),
            },
            {
              key: 'logs',
              label: <span style={{ color: '#CBD5E1' }}>执行日志</span>,
              children: (
                <div>
                  <Space style={{ marginBottom: 12 }}>
                    <Select
                      placeholder="按阶段筛选"
                      allowClear
                      style={{ width: 200 }}
                      options={phaseOptions}
                      value={selectedPhase}
                      onChange={(val) => setSelectedPhase(val || undefined)}
                      loading={logsLoading}
                    />
                    <Button
                      onClick={loadLogs}
                      loading={logsLoading}
                      style={{
                        borderRadius: 8,
                        background: 'rgba(51, 65, 85, 0.5)',
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        color: '#CBD5E1',
                      }}
                    >
                      刷新日志
                    </Button>
                  </Space>
                  <List
                    loading={logsLoading}
                    dataSource={logs}
                    locale={{ emptyText: <span style={{ color: '#64748B' }}>暂无日志</span> }}
                    style={{
                      background: 'rgba(51, 65, 85, 0.3)',
                      borderRadius: 8,
                      padding: '0 16px',
                    }}
                    renderItem={(item: any) => (
                      <List.Item style={{ borderBottomColor: 'rgba(148, 163, 184, 0.1)' }}>
                        <List.Item.Meta
                          title={
                            <Space>
                              <Tag
                                style={{
                                  background: 'rgba(14, 165, 233, 0.15)',
                                  color: '#0EA5E9',
                                  border: 'none',
                                  borderRadius: 6,
                                }}
                              >
                                {item.phase}
                              </Tag>
                              <Tag
                                style={{
                                  background:
                                    item.level === 'error'
                                      ? 'rgba(239, 68, 68, 0.15)'
                                      : item.level === 'warning'
                                      ? 'rgba(249, 115, 22, 0.15)'
                                      : 'rgba(100, 116, 139, 0.15)',
                                  color:
                                    item.level === 'error'
                                      ? '#EF4444'
                                      : item.level === 'warning'
                                      ? '#F97316'
                                      : '#94A3B8',
                                  border: 'none',
                                  borderRadius: 6,
                                }}
                              >
                                {item.level}
                              </Tag>
                              <span style={{ color: '#64748B', fontSize: 12 }}>
                                {dayjs(item.created_at).format('YYYY-MM-DD HH:mm:ss')}
                              </span>
                            </Space>
                          }
                          description={
                            <span style={{ color: '#CBD5E1' }}>{item.message}</span>
                          }
                        />
                      </List.Item>
                    )}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}

export default TaskDetail
