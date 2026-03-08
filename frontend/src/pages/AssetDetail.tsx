import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, Tag, Button, Typography } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { assetsAPI } from '../utils/api'
import dayjs from 'dayjs'

const { Title } = Typography

const AssetDetail = () => {
  const { id } = useParams<{ id: string }>()
  const [asset, setAsset] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (id) {
      loadAsset()
    }
  }, [id])

  const loadAsset = async () => {
    if (!id) return
    setLoading(true)
    try {
      const data = await assetsAPI.get(Number(id))
      setAsset(data)
    } catch (error) {
      console.error('加载资产详情失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const getTypeTag = (type: string) => {
    const typeMap: Record<string, { color: string; text: string }> = {
      ip: { color: '#0EA5E9', text: 'IP' },
      subdomain: { color: '#22C55E', text: '子域名' },
      endpoint: { color: '#F59E0B', text: '端点' },
      domain: { color: '#A78BFA', text: '域名' },
    }
    const config = typeMap[type] || { color: '#94A3B8', text: type }
    return (
      <Tag
        style={{
          background: `${config.color}20`,
          color: config.color,
          border: 'none',
          borderRadius: 6,
        }}
      >
        {config.text}
      </Tag>
    )
  }

  if (!asset) {
    return (
      <div style={{ color: '#94A3B8', textAlign: 'center', padding: 50 }}>
        加载中...
      </div>
    )
  }

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">资产详情</h1>
        <p className="page-subtitle">查看资产详细信息和关联数据</p>
      </div>

      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/assets')}
        style={{
          marginBottom: 24,
          borderRadius: 8,
          background: 'rgba(51, 65, 85, 0.5)',
          borderColor: 'rgba(148, 163, 184, 0.2)',
          color: '#CBD5E1',
        }}
      >
        返回
      </Button>

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
          {getTypeTag(asset.type)} {asset.value}
        </Title>

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
          <Descriptions.Item label="资产ID">{asset.id}</Descriptions.Item>
          <Descriptions.Item label="类型">{getTypeTag(asset.type)}</Descriptions.Item>
          <Descriptions.Item label="值" span={2}>
            <span style={{ color: '#F8FAFC', fontFamily: 'monospace' }}>{asset.value}</span>
          </Descriptions.Item>
          <Descriptions.Item label="标签">
            {asset.tags?.map((tag: string) => (
              <Tag
                key={tag}
                style={{
                  background: 'rgba(14, 165, 233, 0.15)',
                  color: '#0EA5E9',
                  border: 'none',
                  borderRadius: 6,
                }}
              >
                {tag}
              </Tag>
            )) || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="发现时间">
            {dayjs(asset.discovered_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          <Descriptions.Item label="最后出现">
            {dayjs(asset.last_seen).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
        </Descriptions>

        {asset.data && Object.keys(asset.data).length > 0 && (
          <Card
            title={<span style={{ color: '#F8FAFC' }}>详细信息</span>}
            style={{
              marginTop: 24,
              background: 'rgba(51, 65, 85, 0.3)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
            }}
            headStyle={{
              borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
            }}
          >
            <pre
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                padding: 16,
                borderRadius: 8,
                color: '#CBD5E1',
                fontFamily: 'monospace',
                fontSize: 13,
                overflow: 'auto',
              }}
            >
              {JSON.stringify(asset.data, null, 2)}
            </pre>
          </Card>
        )}
      </Card>
    </div>
  )
}

export default AssetDetail
