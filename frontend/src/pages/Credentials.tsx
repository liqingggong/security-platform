import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Switch, message, Space, Tag } from 'antd'
import { SaveOutlined, ReloadOutlined, KeyOutlined, SafetyOutlined } from '@ant-design/icons'
import { credentialsAPI } from '../utils/api'

const Credentials = () => {
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [credentials, setCredentials] = useState<Record<string, any>>({})
  const [fofaForm] = Form.useForm()
  const [hunterForm] = Form.useForm()

  useEffect(() => {
    loadCredentials()
  }, [])

  const loadCredentials = async () => {
    setLoading(true)
    try {
      const data = await credentialsAPI.list()
      const credsMap: Record<string, any> = {}
      const credsList = Array.isArray(data) ? data : []
      credsList.forEach((cred: any) => {
        credsMap[cred.provider] = cred
        if (cred.provider === 'fofa') {
          fofaForm.setFieldsValue({
            api_key: cred.api_key ? '***已设置***' : '',
            api_email: cred.api_email || '',
            is_active: cred.is_active,
          })
        }
        if (cred.provider === 'hunter') {
          hunterForm.setFieldsValue({
            api_key: cred.api_key ? '***已设置***' : '',
            is_active: cred.is_active,
          })
        }
      })
      setCredentials(credsMap)
    } catch (error) {
      message.error('加载凭据列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (provider: string, values: any) => {
    setSaving({ ...saving, [provider]: true })
    try {
      const payload: any = {
        is_active: values.is_active,
      }

      if (provider === 'fofa') {
        payload.api_email = values.api_email
        payload.api_key = values.api_key === '***已设置***' ? undefined : values.api_key
      } else if (provider === 'hunter') {
        payload.api_key = values.api_key === '***已设置***' ? undefined : values.api_key
      }

      await credentialsAPI.update(provider, payload)
      message.success(`${provider.toUpperCase()} 凭据保存成功`)
      loadCredentials()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    } finally {
      setSaving({ ...saving, [provider]: false })
    }
  }

  const fofaCred = credentials.fofa
  const hunterCred = credentials.hunter

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">API 凭据管理</h1>
        <p className="page-subtitle">配置 FOFA 和 Hunter 平台的 API 凭据</p>
      </div>

      {/* Action Bar */}
      <div
        className="glass-card"
        style={{ padding: 20, marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.2) 0%, rgba(250, 204, 21, 0.2) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#EAB308',
            }}
          >
            <KeyOutlined style={{ fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>API 凭据</div>
            <div style={{ fontSize: 12, color: '#64748B' }}>管理第三方平台接入密钥</div>
          </div>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadCredentials}
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

      {/* FOFA Card */}
      <Card
        title={
          <Space>
            <span style={{ color: '#F8FAFC', fontWeight: 600 }}>FOFA</span>
            {fofaCred && (
              <Tag
                style={{
                  background: fofaCred.is_active ? 'rgba(34, 197, 94, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                  color: fofaCred.is_active ? '#22C55E' : '#94A3B8',
                  border: 'none',
                  borderRadius: 6,
                }}
              >
                {fofaCred.is_active ? '已启用' : '已禁用'}
              </Tag>
            )}
          </Space>
        }
        loading={loading}
        style={{
          marginBottom: 24,
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(148, 163, 184, 0.1)',
          borderRadius: 16,
        }}
        headStyle={{
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
          color: '#F8FAFC',
        }}
      >
        <Form
          form={fofaForm}
          layout="vertical"
          onFinish={(values) => handleSave('fofa', values)}
          initialValues={{ is_active: true }}
        >
          <Form.Item
            name="api_email"
            label={<span style={{ color: '#CBD5E1' }}>FOFA Email</span>}
            rules={[{ required: true, message: '请输入 FOFA Email' }]}
          >
            <Input
              placeholder="your-email@example.com"
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item
            name="api_key"
            label={<span style={{ color: '#CBD5E1' }}>FOFA API Key</span>}
            rules={[{ required: true, message: '请输入 FOFA API Key' }]}
            help={<span style={{ color: '#64748B' }}>{fofaCred?.api_key ? '留空则不更新，输入新值则更新' : ''}</span>}
          >
            <Input.Password
              placeholder="输入新的 API Key 或留空保持原值"
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item name="is_active" valuePropName="checked">
            <Switch
              checkedChildren="启用"
              unCheckedChildren="禁用"
              style={{
                backgroundColor: 'rgba(51, 65, 85, 0.8)',
              }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={saving.fofa}
              style={{
                borderRadius: 8,
                background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                border: 'none',
              }}
            >
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Hunter Card */}
      <Card
        title={
          <Space>
            <span style={{ color: '#F8FAFC', fontWeight: 600 }}>Hunter</span>
            {hunterCred && (
              <Tag
                style={{
                  background: hunterCred.is_active ? 'rgba(34, 197, 94, 0.15)' : 'rgba(100, 116, 139, 0.15)',
                  color: hunterCred.is_active ? '#22C55E' : '#94A3B8',
                  border: 'none',
                  borderRadius: 6,
                }}
              >
                {hunterCred.is_active ? '已启用' : '已禁用'}
              </Tag>
            )}
          </Space>
        }
        loading={loading}
        style={{
          marginBottom: 24,
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(148, 163, 184, 0.1)',
          borderRadius: 16,
        }}
        headStyle={{
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
          color: '#F8FAFC',
        }}
      >
        <Form
          form={hunterForm}
          layout="vertical"
          onFinish={(values) => handleSave('hunter', values)}
          initialValues={{ is_active: true }}
        >
          <Form.Item
            name="api_key"
            label={<span style={{ color: '#CBD5E1' }}>Hunter API Key</span>}
            rules={[{ required: true, message: '请输入 Hunter API Key' }]}
            help={<span style={{ color: '#64748B' }}>{hunterCred?.api_key ? '留空则不更新，输入新值则更新' : ''}</span>}
          >
            <Input.Password
              placeholder="输入新的 API Key 或留空保持原值"
              style={{
                background: 'rgba(51, 65, 85, 0.5)',
                borderColor: 'rgba(148, 163, 184, 0.2)',
                color: '#F8FAFC',
                borderRadius: 8,
              }}
            />
          </Form.Item>

          <Form.Item name="is_active" valuePropName="checked">
            <Switch
              checkedChildren="启用"
              unCheckedChildren="禁用"
              style={{
                backgroundColor: 'rgba(51, 65, 85, 0.8)',
              }}
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={saving.hunter}
              style={{
                borderRadius: 8,
                background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                border: 'none',
              }}
            >
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {/* Tips Card */}
      <Card
        style={{
          background: 'rgba(30, 41, 59, 0.4)',
          border: '1px dashed rgba(148, 163, 184, 0.2)',
          borderRadius: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'rgba(14, 165, 233, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#0EA5E9',
              flexShrink: 0,
            }}
          >
            <SafetyOutlined />
          </div>
          <div style={{ color: '#94A3B8', lineHeight: 1.8 }}>
            <strong style={{ color: '#CBD5E1' }}>使用提示：</strong>
            <br />
            1. FOFA 需要 Email 和 API Key 两个参数
            <br />
            2. Hunter 只需要 API Key 一个参数
            <br />
            3. 如果 API Key 已设置，留空则不会更新
            <br />
            4. 凭据信息会加密存储，仅用于执行扫描任务
          </div>
        </div>
      </Card>
    </div>
  )
}

export default Credentials
