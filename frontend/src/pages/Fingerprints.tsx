import { useEffect, useState } from 'react'
import { Button, Table, Space, Modal, Form, Input, Select, Switch, message, Popconfirm, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, SecurityScanOutlined } from '@ant-design/icons'
import { fingerprintRulesAPI } from '../utils/api'
import dayjs from 'dayjs'

const TARGET_OPTIONS = [
  { label: 'URL', value: 'url' },
  { label: 'Body', value: 'body' },
  { label: 'Title', value: 'title' },
  { label: 'Header', value: 'header' },
]

const Fingerprints = () => {
  const [rules, setRules] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    setLoading(true)
    try {
      const data = await fingerprintRulesAPI.list()
      setRules(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载指纹规则失败')
    } finally {
      setLoading(false)
    }
  }

  const openModal = (rule?: any) => {
    setEditing(rule || null)
    setModalVisible(true)
    if (rule) {
      form.setFieldsValue({
        name: rule.name,
        description: rule.description,
        enabled: rule.enabled,
        target: rule.target,
        pattern: rule.pattern,
        metadataText: rule.metadata ? JSON.stringify(rule.metadata, null, 2) : '',
      })
    } else {
      form.resetFields()
      form.setFieldsValue({ enabled: true, target: 'url' })
    }
  }

  const handleSubmit = async (values: any) => {
    const payload: any = {
      description: values.description,
      enabled: values.enabled,
      target: values.target,
      pattern: values.pattern,
      metadata: undefined,
    }
    if (values.metadataText) {
      try {
        payload.metadata = JSON.parse(values.metadataText)
      } catch (e) {
        message.error('metadata 需要是合法 JSON')
        return
      }
    }
    try {
      if (editing) {
        await fingerprintRulesAPI.update(editing.id, payload)
        message.success('规则更新成功')
      } else {
        await fingerprintRulesAPI.create({
          name: values.name,
          description: payload.description,
          enabled: payload.enabled,
          target: payload.target,
          pattern: payload.pattern,
          metadata: payload.metadata,
        })
        message.success('规则创建成功')
      }
      setModalVisible(false)
      form.resetFields()
      loadRules()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    }
  }

  const handleDelete = async (rule: any) => {
    try {
      await fingerprintRulesAPI.remove(rule.id)
      message.success('删除成功')
      loadRules()
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
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (val: boolean) => (
        <Tag
          style={{
            background: val ? 'rgba(34, 197, 94, 0.15)' : 'rgba(100, 116, 139, 0.15)',
            color: val ? '#22C55E' : '#94A3B8',
            border: 'none',
            borderRadius: 6,
          }}
        >
          {val ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '目标',
      dataIndex: 'target',
      key: 'target',
      render: (target: string) => (
        <Tag
          style={{
            background: 'rgba(14, 165, 233, 0.15)',
            color: '#0EA5E9',
            border: 'none',
            borderRadius: 6,
          }}
        >
          {target}
        </Tag>
      ),
    },
    {
      title: '模式',
      dataIndex: 'pattern',
      key: 'pattern',
      ellipsis: true,
      render: (pattern: string) => (
        <span style={{ color: '#94A3B8', fontFamily: 'monospace' }}>{pattern}</span>
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
            icon={<EditOutlined />}
            onClick={() => openModal(record)}
            style={{ color: '#0EA5E9' }}
          />
          <Popconfirm title="确认删除该规则？" onConfirm={() => handleDelete(record)}>
            <Button type="text" icon={<DeleteOutlined />} style={{ color: '#EF4444' }} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">指纹规则</h1>
        <p className="page-subtitle">配置指纹识别规则用于资产探测</p>
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
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(167, 139, 250, 0.2) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#A78BFA',
            }}
          >
            <SecurityScanOutlined style={{ fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>指纹规则</div>
            <div style={{ fontSize: 12, color: '#64748B' }}>共 {rules.length} 条规则</div>
          </div>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadRules}
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
            新建规则
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
          dataSource={rules}
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
                background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2) 0%, rgba(167, 139, 250, 0.2) 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#A78BFA',
              }}
            >
              <SecurityScanOutlined />
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>
                {editing ? `编辑规则：${editing.name}` : '新建指纹规则'}
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
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ marginTop: 24 }}>
          <Form.Item
            name="name"
            label={<span style={{ color: '#CBD5E1' }}>名称</span>}
            rules={[{ required: true, message: '请输入名称' }]}
            extra={<span style={{ color: '#64748B' }}>名称不可修改</span>}
          >
            <Input
              disabled={!!editing}
              placeholder="规则名称"
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
              placeholder="规则说明"
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
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

          <Form.Item
            name="target"
            label={<span style={{ color: '#CBD5E1' }}>匹配目标</span>}
            rules={[{ required: true }]}
          >
            <Select options={TARGET_OPTIONS} />
          </Form.Item>

          <Form.Item
            name="pattern"
            label={<span style={{ color: '#CBD5E1' }}>匹配模式</span>}
            rules={[{ required: true, message: '请输入模式' }]}
          >
            <Input.TextArea
              rows={3}
              placeholder="正则表达式或关键词"
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
                fontFamily: 'monospace',
              }}
            />
          </Form.Item>

          <Form.Item
            name="metadataText"
            label={<span style={{ color: '#CBD5E1' }}>元数据（JSON）</span>}
            extra={<span style={{ color: '#64748B' }}>可选，用于描述标签、严重程度等</span>}
          >
            <Input.TextArea
              rows={4}
              placeholder='如：{"tags":["web"],"severity":"info"}'
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

export default Fingerprints
