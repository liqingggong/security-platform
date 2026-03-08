import { useState, useEffect } from 'react'
import { Form, InputNumber, Button, message, Card, Space, Radio, Typography } from 'antd'
import { SaveOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons'

const AssetSettings = () => {
  const [fofaLimit, setFofaLimit] = useState<number>(10000)
  const [hunterLimit, setHunterLimit] = useState<number>(10000)
  const [isWeb, setIsWeb] = useState(true)
  const [page, setPage] = useState<number>(1)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [refreshInterval, setRefreshInterval] = useState<number>(300)

  useEffect(() => {
    let timer: number
    if (autoRefresh) {
      timer = setInterval(() => {
        console.log('Auto refreshing...')
      }, refreshInterval * 1000)
    }
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [autoRefresh, refreshInterval])

  const handleSubmit = async () => {
    message.success('配置已保存（演示）')
  }

  const resetDefaults = () => {
    setFofaLimit(10000)
    setHunterLimit(10000)
    setIsWeb(true)
    setPage(1)
    setRefreshInterval(300)
  }

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">API 配置</h1>
        <p className="page-subtitle">配置 FOFA 和 Hunter API 的搜索参数</p>
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
              background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.2) 0%, rgba(56, 189, 248, 0.2) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#0EA5E9',
            }}
          >
            <SettingOutlined style={{ fontSize: 20 }} />
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#F8FAFC' }}>API 配置</div>
            <div style={{ fontSize: 12, color: '#64748B' }}>管理第三方数据源查询参数</div>
          </div>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={resetDefaults}
          style={{
            borderRadius: 8,
            background: 'rgba(51, 65, 85, 0.5)',
            borderColor: 'rgba(148, 163, 184, 0.2)',
            color: '#CBD5E1',
          }}
        >
          重置
        </Button>
      </div>

      <Card
        style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(148, 163, 184, 0.1)',
          borderRadius: 16,
        }}
        headStyle={{
          borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
        }}
      >
        <Typography.Title level={4} style={{ color: '#F8FAFC', marginTop: 0 }}>
          FOFA/Hunter 资源配置
        </Typography.Title>
        <Typography.Paragraph style={{ color: '#64748B' }}>
          此页面用于配置 FOFA 和 Hunter API 的搜索参数。
          注意：大量查询会消耗 API 配额，请合理配置查询参数。
          支持配置每页数量、页码、是否只查询 Web 资产。
        </Typography.Paragraph>

        <div style={{ marginTop: 24 }}>
          <Radio.Group
            value={isWeb ? '1' : '0'}
            onChange={(e) => setIsWeb(e.target.value === '1')}
            style={{ marginBottom: 24 }}
          >
            <Radio value="1" style={{ color: '#CBD5E1' }}>只查询 Web 资产</Radio>
            <Radio value="0" style={{ color: '#CBD5E1' }}>查询所有资产</Radio>
          </Radio.Group>

          <Form layout="vertical" onFinish={handleSubmit}>
            <Form.Item
              label={<span style={{ color: '#CBD5E1' }}>FOFA 每页数量限制</span>}
            >
              <InputNumber
                min={1}
                max={10000}
                value={fofaLimit}
                onChange={(value) => setFofaLimit(value ?? 10000)}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item
              label={<span style={{ color: '#CBD5E1' }}>Hunter 每页数量限制</span>}
            >
              <InputNumber
                min={1}
                max={10000}
                value={hunterLimit}
                onChange={(value) => setHunterLimit(value ?? 10000)}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item
              label={<span style={{ color: '#CBD5E1' }}>页码</span>}
            >
              <InputNumber
                min={1}
                max={100}
                value={page}
                onChange={(value) => setPage(value ?? 1)}
                disabled={!isWeb}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item
              label={<span style={{ color: '#CBD5E1' }}>自动刷新间隔（秒）</span>}
            >
              <InputNumber
                min={60}
                max={3600}
                step={60}
                value={refreshInterval}
                onChange={(value) => setRefreshInterval(value ?? 300)}
                disabled={!autoRefresh}
                style={{ width: '100%' }}
              />
            </Form.Item>

            <div style={{ marginTop: 24 }}>
              <Space>
                <Button
                  htmlType="submit"
                  type="primary"
                  icon={<SaveOutlined />}
                  style={{
                    borderRadius: 8,
                    background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                    border: 'none',
                  }}
                >
                  保存配置
                </Button>
                <Button
                  htmlType="button"
                  onClick={resetDefaults}
                  style={{
                    borderRadius: 8,
                    background: 'rgba(51, 65, 85, 0.5)',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    color: '#CBD5E1',
                  }}
                >
                  重置为默认值
                </Button>
                <Button
                  htmlType="button"
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
              </Space>
            </div>
          </Form>
        </div>
      </Card>
    </div>
  )
}

export default AssetSettings
