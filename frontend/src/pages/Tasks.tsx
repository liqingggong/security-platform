import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Checkbox,
  message,
  Popconfirm,
  Progress,
} from 'antd'
import {
  PlusOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  CloseCircleOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { tasksAPI, scanPlansAPI, toolsAPI } from '../utils/api'
import dayjs from 'dayjs'
import { TablePageSkeleton } from '../components/PageSkeleton'

const Tasks = () => {
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTask, setEditingTask] = useState<any | null>(null)
  const [scanPlans, setScanPlans] = useState<any[]>([])
  const [planLoading, setPlanLoading] = useState(false)
  const [availableTools, setAvailableTools] = useState<any[]>([])
  const [toolsLoading, setToolsLoading] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  useEffect(() => {
    loadTasks()
    loadScanPlans()
    loadTools()
  }, [])

  const loadTasks = async () => {
    setLoading(true)
    try {
      const data = await tasksAPI.list()
      setTasks(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  const loadScanPlans = async () => {
    setPlanLoading(true)
    try {
      const data = await scanPlansAPI.list()
      setScanPlans(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载扫描方案失败')
    } finally {
      setPlanLoading(false)
    }
  }

  const loadTools = async () => {
    setToolsLoading(true)
    try {
      const data = await toolsAPI.list()
      const enabledTools = Array.isArray(data) ? data.filter((tool: any) => tool.enabled) : []
      setAvailableTools(enabledTools)
    } catch (error) {
      message.error('加载工具列表失败')
    } finally {
      setToolsLoading(false)
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      const enable: Record<string, boolean> = {}

      if (!values.scan_plan_id) {
        const selectedTools = values.enable || []
        if (Array.isArray(selectedTools) && selectedTools.length > 0) {
          selectedTools.forEach((toolName: string) => {
            if (toolName) {
              enable[toolName] = true
            }
          })
        }

        if (Object.keys(enable).length === 0) {
          message.error('至少需要启用一个工具，或选择一个扫描方案')
          return
        }
      }

      const payload = {
        ...values,
        root_domains: values.root_domains
          ? values.root_domains.split('\n').filter((d: string) => d.trim())
          : [],
        ips: values.ips
          ? values.ips.split('\n').filter((ip: string) => ip.trim())
          : [],
        fofa_query: values.fofa_query || null,
        hunter_query: values.hunter_query || null,
        enable,
        scan_plan_id: values.scan_plan_id || null,
      }

      if (editingTask) {
        await tasksAPI.update(editingTask.id, payload)
        message.success('任务更新成功')
      } else {
        await tasksAPI.create(payload)
        message.success('任务创建成功')
      }
      setModalVisible(false)
      form.resetFields()
      setEditingTask(null)
      loadTasks()
    } catch (error: any) {
      message.error(
        error.response?.data?.detail || (editingTask ? '更新任务失败' : '创建任务失败'),
      )
    }
  }

  const handleCancel = async (id: number) => {
    try {
      await tasksAPI.cancel(id)
      message.success('任务已取消')
      loadTasks()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '取消任务失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await tasksAPI.deleteHard(id)
      message.success('任务已删除')
      loadTasks()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除任务失败')
    }
  }

  const openEditModal = (record: any) => {
    setEditingTask(record)
    const input = record.input_data || {}

    let enableArray: string[] = []
    if (input.enable) {
      if (Array.isArray(input.enable)) {
        enableArray = input.enable
      } else if (typeof input.enable === 'object') {
        enableArray = Object.entries(input.enable)
          .filter(([_, enabled]) => enabled === true)
          .map(([toolName]) => toolName)
      }
    } else if (record.scan_plan_id) {
      const plan = scanPlans.find(p => p.id === record.scan_plan_id)
      if (plan && plan.tools) {
        enableArray = plan.tools
          .filter((t: any) => t.enabled)
          .map((t: any) => t.tool_name)
      }
    }

    form.setFieldsValue({
      name: record.name,
      description: record.description,
      root_domains: (input.root_domains || []).join('\n'),
      ips: (input.ips || []).join('\n'),
      fofa_query: input.fofa_query || '',
      hunter_query: input.hunter_query || '',
      enable: enableArray,
      scan_plan_id: record.scan_plan_id || undefined,
    })
    setModalVisible(true)
  }

  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; bgColor: string; icon: React.ReactNode; text: string }> = {
      pending: { color: '#94A3B8', bgColor: 'rgba(148, 163, 184, 0.15)', icon: <ClockCircleOutlined />, text: '等待中' },
      running: { color: '#0EA5E9', bgColor: 'rgba(14, 165, 233, 0.15)', icon: <PlayCircleOutlined />, text: '运行中' },
      completed: { color: '#22C55E', bgColor: 'rgba(34, 197, 94, 0.15)', icon: <SafetyOutlined />, text: '已完成' },
      failed: { color: '#EF4444', bgColor: 'rgba(239, 68, 68, 0.15)', icon: <CloseCircleOutlined />, text: '失败' },
      cancelled: { color: '#F97316', bgColor: 'rgba(249, 115, 22, 0.15)', icon: <CloseCircleOutlined />, text: '已取消' },
    }
    const config = statusMap[status] || { color: '#94A3B8', bgColor: 'rgba(148, 163, 184, 0.15)', icon: null, text: status }
    return (
      <Tag
        style={{
          background: config.bgColor,
          color: config.color,
          border: 'none',
          borderRadius: 6,
          fontWeight: 600,
          padding: '4px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          width: 'fit-content',
        }}
      >
        {config.icon}
        {config.text}
      </Tag>
    )
  }

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: any) => (
        <div>
          <div style={{ fontWeight: 600, color: '#F8FAFC', fontSize: 14 }}>{name}</div>
          {record.description && (
            <div style={{ color: '#64748B', fontSize: 12, marginTop: 2 }}>{record.description}</div>
          )}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      width: 160,
      render: (progress: number, record: any) => (
        <div>
          <Progress
            percent={progress}
            size="small"
            strokeColor={{
              '0%': record.status === 'failed' ? '#EF4444' : '#0EA5E9',
              '100%': record.status === 'completed' ? '#22C55E' : '#0EA5E9',
            }}
            showInfo={false}
          />
          <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>{progress}%</div>
        </div>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (time: string) => (
        <div style={{ color: '#94A3B8', fontSize: 13 }}>
          {dayjs(time).format('YYYY-MM-DD HH:mm')}
        </div>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: any, record: any) => (
        <Space size={8}>
          <Button
            type="text"
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/tasks/${record.id}`)}
            style={{ color: '#0EA5E9' }}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
            style={{ color: '#38BDF8' }}
          />
          {['pending', 'running'].includes(record.status) && (
            <Popconfirm
              title="确定要取消这个任务吗？"
              onConfirm={() => handleCancel(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="text"
                icon={<CloseCircleOutlined />}
                style={{ color: '#F97316' }}
              />
            </Popconfirm>
          )}
          <Popconfirm
            title="确定要删除这个任务吗？"
            description="相关资产和漏洞也会被删除，此操作不可恢复。"
            onConfirm={() => handleDelete(record.id)}
            okText="删除"
            okType="danger"
            cancelText="取消"
          >
            <Button
              type="text"
              icon={<DeleteOutlined />}
              style={{ color: '#EF4444' }}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 显示骨架屏避免白屏
  if (loading && tasks.length === 0) {
    return <TablePageSkeleton />
  }

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">任务管理</h1>
        <p className="page-subtitle">创建和管理资产扫描任务</p>
      </div>

      {/* Action Bar */}
      <div
        className="glass-card"
        style={{ padding: 24, marginBottom: 24 }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
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
              <PlayCircleOutlined style={{ fontSize: 20 }} />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>扫描任务</div>
              <div style={{ fontSize: 12, color: '#64748B' }}>共 {tasks.length} 个任务</div>
            </div>
          </div>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={loadTasks}
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
              icon={<PlusOutlined />}
              onClick={() => {
                loadTools()
                setModalVisible(true)
              }}
              style={{
                borderRadius: 8,
                background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                border: 'none',
              }}
            >
              创建任务
            </Button>
          </Space>
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
          dataSource={tasks}
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
        />
      </div>

      {/* Modal */}
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
                justifyContent: 'center',
                color: '#0EA5E9',
              }}
            >
              <PlayCircleOutlined />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                {editingTask ? '编辑扫描任务' : '创建扫描任务'}
              </div>
              <div style={{ fontSize: 12, color: '#64748B' }}>
                {editingTask ? '修改任务配置' : '配置新的扫描任务'}
              </div>
            </div>
          </div>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
          setEditingTask(null)
        }}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{ enable: [] }}
          style={{ marginTop: 24 }}
        >
          <Form.Item
            name="name"
            label="任务名称"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：example.com 资产扫描" size="large" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="任务描述（可选）" />
          </Form.Item>

          <Form.Item name="scan_plan_id" label="选择扫描方案">
            <Select
              placeholder="可选：选择后将自动使用方案中的工具配置"
              allowClear
              loading={planLoading}
              disabled={editingTask && editingTask.status !== 'pending'}
              onChange={(value) => {
                if (value) {
                  form.setFieldsValue({ enable: [] })
                }
              }}
            >
              {scanPlans.map((plan) => (
                <Select.Option key={plan.id} value={plan.id}>
                  {plan.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="输入数据">
            <Form.Item
              name="root_domains"
              label="根域名（每行一个）"
              style={{ marginBottom: 16 }}
            >
              <Input.TextArea
                rows={3}
                placeholder="example.com&#10;test.com"
                disabled={editingTask && editingTask.status !== 'pending'}
              />
            </Form.Item>

            <Form.Item
              name="ips"
              label="IP 地址（每行一个）"
              style={{ marginBottom: 16 }}
            >
              <Input.TextArea
                rows={3}
                placeholder="1.1.1.1&#10;2.2.2.2"
                disabled={editingTask && editingTask.status !== 'pending'}
              />
            </Form.Item>

            <Form.Item name="fofa_query" label="FOFA 查询语句">
              <Input
                placeholder='例如：domain="example.com"'
                disabled={editingTask && editingTask.status !== 'pending'}
              />
            </Form.Item>

            <Form.Item name="hunter_query" label="Hunter 查询语句">
              <Input
                placeholder='例如：domain="example.com"'
                disabled={editingTask && editingTask.status !== 'pending'}
              />
            </Form.Item>
          </Form.Item>

          <Form.Item
            name="enable"
            label="启用的工具"
            extra="未选择扫描方案时，请手动勾选要执行的工具"
          >
            <Form.Item
              noStyle
              shouldUpdate={(prevValues, currentValues) =>
                prevValues.scan_plan_id !== currentValues.scan_plan_id
              }
            >
              {({ getFieldValue }) => {
                const scanPlanId = getFieldValue('scan_plan_id')
                const locked = !!scanPlanId
                return (
                  <div style={locked ? { opacity: 0.5, pointerEvents: 'none' } : undefined}>
                    <Checkbox.Group disabled={editingTask && editingTask.status !== 'pending' || locked}>
                      <Space direction="vertical">
                        {availableTools.map((tool: any) => (
                          <Checkbox key={tool.id} value={tool.name}>
                            <span style={{ fontWeight: 500, color: '#CBD5E1' }}>{tool.display_name || tool.name}</span>
                            {tool.description && (
                              <span style={{ color: '#64748B', marginLeft: 8, fontSize: 12 }}>
                                {tool.description}
                              </span>
                            )}
                          </Checkbox>
                        ))}
                        {availableTools.length === 0 && !toolsLoading && (
                          <span style={{ color: '#94A3B8' }}>暂无可用工具，请先在工具管理中上传并启用工具</span>
                        )}
                      </Space>
                    </Checkbox.Group>
                  </div>
                )
              }}
            </Form.Item>
          </Form.Item>

          <Form.Item style={{ marginTop: 24 }}>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                style={{
                  borderRadius: 8,
                  background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                  border: 'none',
                  padding: '0 32px',
                }}
              >
                {editingTask ? '更新任务' : '创建任务'}
              </Button>
              <Button
                size="large"
                style={{ borderRadius: 8, padding: '0 32px' }}
                onClick={() => {
                  setModalVisible(false)
                  form.resetFields()
                  setEditingTask(null)
                }}
              >
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Tasks
