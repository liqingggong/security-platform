import { useEffect, useState } from 'react'
import { Button, Table, Space, Modal, Form, Input, Select, Switch, Upload, message, Popconfirm, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined, UploadOutlined, ToolOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { toolsAPI } from '../utils/api'
import dayjs from 'dayjs'
import type { UploadFile } from 'antd'

const TOOL_TYPES = [
  { label: '脚本', value: 'script' },
  { label: '二进制文件', value: 'binary' },
  { label: 'Docker 容器', value: 'docker' },
]

const Tools = () => {
  const [tools, setTools] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [form] = Form.useForm()

  useEffect(() => {
    loadTools()
  }, [])

  const loadTools = async () => {
    setLoading(true)
    try {
      const data = await toolsAPI.list()
      setTools(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载工具列表失败')
    } finally {
      setLoading(false)
    }
  }

  const openModal = (tool?: any) => {
    setEditing(tool || null)
    setModalVisible(true)
    setFileList([])

    if (tool) {
      form.setFieldsValue({
        name: tool.name,
        display_name: tool.display_name,
        description: tool.description,
        version: tool.version,
        author: tool.author,
        tool_type: tool.tool_type,
        command_template: tool.command_template,
        enabled: tool.enabled,
      })
    } else {
      form.resetFields()
      form.setFieldsValue({
        tool_type: 'script',
        enabled: true
      })
    }
  }

  const handleSubmit = async (values: any) => {
    try {
      if (editing) {
        await toolsAPI.update(editing.id, {
          display_name: values.display_name,
          description: values.description,
          version: values.version,
          author: values.author,
          command_template: values.command_template,
          enabled: values.enabled,
        })
        message.success('工具更新成功')
      } else {
        const formData = new FormData()
        formData.append('name', values.name)
        if (values.display_name) formData.append('display_name', values.display_name)
        if (values.description) formData.append('description', values.description)
        if (values.version) formData.append('version', values.version)
        if (values.author) formData.append('author', values.author)
        formData.append('tool_type', values.tool_type)
        if (values.command_template) formData.append('command_template', values.command_template)
        formData.append('enabled', values.enabled.toString())

        if (fileList.length > 0 && fileList[0].originFileObj) {
          formData.append('file', fileList[0].originFileObj)
        }

        await toolsAPI.create(formData)
        message.success('工具创建成功')
      }

      setModalVisible(false)
      form.resetFields()
      setFileList([])
      loadTools()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    }
  }

  const handleDelete = async (tool: any) => {
    try {
      await toolsAPI.remove(tool.id)
      message.success('删除成功')
      loadTools()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  const handleToggle = async (tool: any, enabled: boolean) => {
    try {
      await toolsAPI.toggle(tool.id, enabled)
      message.success(enabled ? '已启用' : '已禁用')
      loadTools()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: any) => (
        <span style={{ fontWeight: 600, color: '#F8FAFC' }}>{text || record.name}</span>
      ),
    },
    {
      title: '工具标识',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Tag style={{ background: 'rgba(51, 65, 85, 0.8)', color: '#94A3B8', border: 'none' }}>
          {name}
        </Tag>
      ),
    },
    {
      title: '类型',
      dataIndex: 'tool_type',
      key: 'tool_type',
      render: (type: string) => {
        const typeMap: Record<string, { label: string; color: string }> = {
          script: { label: '脚本', color: '#0EA5E9' },
          binary: { label: '二进制', color: '#22C55E' },
          docker: { label: '容器', color: '#F97316' },
        }
        const config = typeMap[type] || { label: type, color: '#94A3B8' }
        return (
          <Tag style={{ background: `${config.color}15`, color: config.color, border: 'none', borderRadius: 6 }}>
            {config.label}
          </Tag>
        )
      },
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (text: string) => (
        <span style={{ color: '#94A3B8' }}>{text || '-'}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record: any) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggle(record, checked)}
          disabled={record.is_builtin}
          style={{
            backgroundColor: enabled ? undefined : 'rgba(51, 65, 85, 0.8)',
          }}
        />
      ),
    },
    {
      title: '类别',
      dataIndex: 'is_builtin',
      key: 'is_builtin',
      render: (isBuiltin: boolean) => (
        <Tag style={{
          background: isBuiltin ? 'rgba(14, 165, 233, 0.15)' : 'rgba(34, 197, 94, 0.15)',
          color: isBuiltin ? '#0EA5E9' : '#22C55E',
          border: 'none',
          borderRadius: 6,
        }}>
          {isBuiltin ? '内置' : '自定义'}
        </Tag>
      ),
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
            icon={record.is_builtin ? <EyeOutlined /> : <EditOutlined />}
            onClick={() => openModal(record)}
            style={{ color: '#0EA5E9' }}
          />
          {!record.is_builtin && (
            <Popconfirm title="确认删除该工具？" onConfirm={() => handleDelete(record)}>
              <Button type="text" icon={<DeleteOutlined />} style={{ color: '#EF4444' }} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">工具管理</h1>
        <p className="page-subtitle">管理扫描工具的配置和启用状态</p>
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
              background: 'linear-gradient(135deg, rgba(249, 115, 22, 0.2) 0%, rgba(251, 146, 60, 0.2) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#F97316',
            }}
          >
            <ToolOutlined style={{ fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>扫描工具</div>
            <div style={{ fontSize: 12, color: '#64748B' }}>共 {tools.length} 个工具</div>
          </div>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadTools}
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
            添加工具
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
          dataSource={tools}
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
                background: 'linear-gradient(135deg, rgba(249, 115, 22, 0.2) 0%, rgba(251, 146, 60, 0.2) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#F97316',
              }}
            >
              <ToolOutlined />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                {editing ? (editing.is_builtin ? `查看工具：${editing.display_name || editing.name}` : `编辑工具：${editing.display_name || editing.name}`) : '添加新工具'}
              </div>
            </div>
          </div>
        }
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
          setFileList([])
        }}
        onOk={() => form.submit()}
        okText="保存"
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 24 }}>
          <Form.Item
            name="name"
            label={<span style={{ color: '#CBD5E1' }}>工具标识</span>}
            rules={[{ required: true, message: '请输入工具标识' }]}
            extra={<span style={{ color: '#64748B' }}>用于系统内部识别，建议使用英文小写，如：fscan、xray</span>}
          >
            <Input
              placeholder="如：fscan"
              disabled={!!editing}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item name="display_name" label={<span style={{ color: '#CBD5E1' }}>显示名称</span>}>
            <Input
              placeholder="如：FScan 内网扫描工具"
              disabled={editing?.is_builtin}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item name="description" label={<span style={{ color: '#CBD5E1' }}>描述</span>}>
            <Input.TextArea
              rows={2}
              placeholder="工具功能说明"
              disabled={editing?.is_builtin}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item name="version" label={<span style={{ color: '#CBD5E1' }}>版本号</span>}>
            <Input
              placeholder="如：1.0.0"
              disabled={editing?.is_builtin}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item name="author" label={<span style={{ color: '#CBD5E1' }}>作者</span>}>
            <Input
              placeholder="工具作者"
              disabled={editing?.is_builtin}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item name="tool_type" label={<span style={{ color: '#CBD5E1' }}>工具类型</span>} rules={[{ required: true }]}>
            <Select options={TOOL_TYPES} disabled={!!editing} />
          </Form.Item>

          {!editing && (
            <Form.Item
              label={<span style={{ color: '#CBD5E1' }}>上传工具文件</span>}
              extra={<span style={{ color: '#64748B' }}>可选：上传脚本、二进制文件或配置文件</span>}
            >
              <Upload
                fileList={fileList}
                beforeUpload={(file) => {
                  setFileList([file])
                  return false
                }}
                onRemove={() => setFileList([])}
                maxCount={1}
              >
                <Button
                  icon={<UploadOutlined />}
                  style={{
                    background: 'rgba(51, 65, 85, 0.5)',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    color: '#CBD5E1',
                  }}
                >
                  选择文件
                </Button>
              </Upload>
            </Form.Item>
          )}

          <Form.Item
            name="command_template"
            label={<span style={{ color: '#CBD5E1' }}>执行命令模板</span>}
            extra={<span style={{ color: '#64748B' }}>支持变量：{'{file_path}'}, {'{target}'}, {'{output}'} 等</span>}
          >
            <Input.TextArea
              rows={3}
              placeholder="如：python3 {file_path} -h {target} -o {output}"
              disabled={editing?.is_builtin}
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
                fontFamily: 'monospace',
              }}
            />
          </Form.Item>

          <Form.Item name="enabled" label={<span style={{ color: '#CBD5E1' }}>是否启用</span>} valuePropName="checked">
            <Switch
              style={{
                backgroundColor: 'rgba(51, 65, 85, 0.8)',
              }}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default Tools
