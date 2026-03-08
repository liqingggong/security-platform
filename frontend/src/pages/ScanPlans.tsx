import { useEffect, useState } from 'react'
import { Button, Table, Space, Modal, Form, Input, Checkbox, message, Popconfirm, Tag, Collapse } from 'antd'
import { PlusOutlined, ReloadOutlined, FileTextOutlined, DeleteOutlined, EditOutlined, DeploymentUnitOutlined } from '@ant-design/icons'
import { scanPlansAPI, toolsAPI } from '../utils/api'
import dayjs from 'dayjs'

const { Panel } = Collapse

const ScanPlans = () => {
  const [plans, setPlans] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [availableTools, setAvailableTools] = useState<any[]>([])
  const [toolsLoading, setToolsLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    loadPlans()
    loadTools()
  }, [])

  const loadPlans = async () => {
    setLoading(true)
    try {
      const data = await scanPlansAPI.list()
      setPlans(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载扫描方案失败')
    } finally {
      setLoading(false)
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

  const openModal = (plan?: any) => {
    loadTools()
    setEditing(plan || null)
    setModalVisible(true)
    if (plan) {
      const toolConfigs: Record<string, string> = {}
      plan.tools?.forEach((t: any) => {
        if (t.enabled && t.config?.command_template) {
          toolConfigs[`command_${t.tool_name}`] = t.config.command_template
        }
      })
      form.setFieldsValue({
        name: plan.name,
        description: plan.description,
        tools: plan.tools?.filter((t: any) => t.enabled).map((t: any) => t.tool_name) || [],
        optionsText: plan.options ? JSON.stringify(plan.options, null, 2) : '',
        ...toolConfigs,
      })
    } else {
      form.resetFields()
    }
  }

  const handleSubmit = async (values: any) => {
    const payload: any = {
      description: values.description || undefined,
      options: undefined,
      tools: (values.tools || []).map((tool: string) => {
        const config: any = {}
        const commandKey = `command_${tool}`
        if (values[commandKey]) {
          config.command_template = values[commandKey]
        }
        return {
          tool_name: tool,
          enabled: true,
          config: config,
        }
      }),
    }
    if (values.optionsText) {
      try {
        payload.options = JSON.parse(values.optionsText)
      } catch (e) {
        message.error('options 需要是合法 JSON')
        return
      }
    }

    try {
      if (editing) {
        await scanPlansAPI.update(editing.id, payload)
        message.success('方案更新成功')
      } else {
        await scanPlansAPI.create({
          name: values.name,
          description: payload.description,
          options: payload.options,
          tools: payload.tools,
        })
        message.success('方案创建成功')
      }
      setModalVisible(false)
      form.resetFields()
      loadPlans()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    }
  }

  const handleDelete = async (plan: any) => {
    try {
      await scanPlansAPI.remove(plan.id)
      message.success('删除成功')
      loadPlans()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <span style={{ fontWeight: 600, color: '#F8FAFC' }}>{name}</span>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <span style={{ color: '#94A3B8' }}>{text || '-'}</span>
      ),
    },
    {
      title: '已启用工具',
      key: 'tools',
      render: (_: any, record: any) =>
        record.tools?.filter((t: any) => t.enabled).map((t: any) => (
          <Tag
            key={t.tool_name}
            style={{
              background: 'rgba(14, 165, 233, 0.15)',
              color: '#0EA5E9',
              border: 'none',
              borderRadius: 6,
            }}
          >
            {t.tool_name}
          </Tag>
        )) || <span style={{ color: '#64748B' }}>-</span>,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (val: string) => (
        <span style={{ color: '#94A3B8' }}>{val ? dayjs(val).format('YYYY-MM-DD HH:mm:ss') : '-'}</span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: any) => (
        <Space size={8}>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => openModal(record)}
            style={{ color: '#0EA5E9' }}
          />
          <Popconfirm
            title="确认删除该方案？"
            onConfirm={() => handleDelete(record)}
            okText="删除"
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

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">扫描方案</h1>
        <p className="page-subtitle">配置扫描任务使用的工具和参数方案</p>
      </div>

      {/* Action Bar */}
      <div
        className="glass-card"
        style={{ padding: 24, marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
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
            <DeploymentUnitOutlined style={{ fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>扫描方案</div>
            <div style={{ fontSize: 12, color: '#64748B' }}>共 {plans.length} 个方案</div>
          </div>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadPlans}
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
            onClick={() => openModal()}
            style={{
              borderRadius: 8,
              background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
              border: 'none',
            }}
          >
            新建方案
          </Button>
        </Space>
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
          dataSource={plans}
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
              <FileTextOutlined />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                {editing ? `编辑方案：${editing.name}` : '新建扫描方案'}
              </div>
              <div style={{ fontSize: 12, color: '#64748B' }}>
                {editing ? '修改方案配置' : '创建新的扫描方案'}
              </div>
            </div>
          </div>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        okText="保存"
        destroyOnClose
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 24 }}>
          <Form.Item
            name="name"
            label={<span style={{ color: '#CBD5E1' }}>名称</span>}
            rules={[{ required: true, message: '请输入名称' }]}
            extra={<span style={{ color: '#64748B' }}>名称不可修改</span>}
          >
            <Input
              placeholder="如：默认扫描方案"
              disabled={!!editing}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={<span style={{ color: '#CBD5E1' }}>描述</span>}
          >
            <Input.TextArea
              rows={3}
              placeholder="方案说明"
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item
            name="tools"
            label={<span style={{ color: '#CBD5E1' }}>启用的工具</span>}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              {availableTools.map((tool: any) => (
                <Checkbox key={tool.id} value={tool.name}>
                  <span style={{ color: '#CBD5E1', fontWeight: 500 }}>{tool.display_name || tool.name}</span>
                  {tool.description && (
                    <span style={{ color: '#64748B', marginLeft: 8, fontSize: 12 }}>
                      - {tool.description}
                    </span>
                  )}
                </Checkbox>
              ))}
              {availableTools.length === 0 && !toolsLoading && (
                <span style={{ color: '#94A3B8' }}>暂无可用工具，请先在工具管理中上传并启用工具</span>
              )}
              {toolsLoading && (
                <span style={{ color: '#94A3B8' }}>加载中...</span>
              )}
            </Space>
          </Form.Item>

          <Form.Item
            label={<span style={{ color: '#CBD5E1' }}>工具命令配置</span>}
            extra={<span style={{ color: '#64748B' }}>为每个启用的工具配置完整的命令模板，支持变量：{'{targets}'}, {'{ports}'}, {'{domain}'} 等</span>}
          >
            <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => prevValues.tools !== currentValues.tools}>
              {({ getFieldValue }) => {
                const selectedTools = getFieldValue('tools') || []
                if (selectedTools.length === 0) {
                  return <span style={{ color: '#64748B' }}>请先选择要启用的工具</span>
                }
                return (
                  <Collapse
                    style={{
                      background: 'rgba(51, 65, 85, 0.5)',
                      borderColor: 'rgba(148, 163, 184, 0.2)',
                    }}
                  >
                    {selectedTools.map((toolName: string) => {
                      const tool = availableTools.find((t: any) => t.name === toolName)
                      const defaultCommand = tool?.command_template || ''
                      return (
                        <Panel
                          header={
                            <span style={{ color: '#F8FAFC' }}>
                              {tool?.display_name || toolName}
                              {defaultCommand && (
                                <span style={{ color: '#64748B', fontSize: 12, marginLeft: 8 }}>
                                  (默认: {defaultCommand})
                                </span>
                              )}
                            </span>
                          }
                          key={toolName}
                        >
                          <Form.Item
                            name={`command_${toolName}`}
                            label={<span style={{ color: '#CBD5E1' }}>{tool?.display_name || toolName} 命令模板</span>}
                            extra={<span style={{ color: '#64748B' }}>完整命令模板，将覆盖工具的默认命令。例如：nmap -sV -p {'{ports}'} -oX - {'{targets}'}</span>}
                          >
                            <Input.TextArea
                              rows={2}
                              placeholder={defaultCommand || `输入 ${toolName} 的完整命令模板`}
                              style={{
                                background: 'rgba(15, 23, 42, 0.5)',
                                borderColor: 'rgba(148, 163, 184, 0.2)',
                                color: '#F8FAFC',
                                borderRadius: 8,
                              }}
                            />
                          </Form.Item>
                        </Panel>
                      )
                    })}
                  </Collapse>
                )
              }}
            </Form.Item>
          </Form.Item>

          <Form.Item
            name="optionsText"
            label={<span style={{ color: '#CBD5E1' }}>任务级选项（JSON）</span>}
            extra={<span style={{ color: '#64748B' }}>可选，用于覆盖并发、超时等任务参数</span>}
          >
            <Input.TextArea
              rows={4}
              placeholder='如：{"concurrency":5}'
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
                fontFamily: 'monospace',
              }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default ScanPlans
