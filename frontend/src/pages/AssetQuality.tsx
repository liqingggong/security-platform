import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Progress, Button, message, Spin } from 'antd'
import {
  CloudServerOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ScanOutlined,
  GlobalOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import api from '../utils/api'

// Types for asset quality statistics (matches backend API response)
interface CoverageItem {
  count: number
  rate: number
}

interface AssetQualityStats {
  total: number
  protocol: CoverageItem
  fingerprint: CoverageItem
  cdn: CoverageItem
  multi_source: CoverageItem
}

const AssetQuality = () => {
  const [stats, setStats] = useState<AssetQualityStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [enhancing, setEnhancing] = useState(false)

  // Fetch quality statistics from API
  const fetchStats = async () => {
    setLoading(true)
    try {
      console.log('[AssetQuality Debug] Fetching stats...')
      const data = await api.get('/assets/stats/quality')
      console.log('[AssetQuality Debug] Response:', data)
      setStats(data as AssetQualityStats)
    } catch (error: any) {
      console.error('[AssetQuality Debug] Error:', error?.response?.data || error?.message || error)
      message.error('加载资产质量统计失败')
    } finally {
      setLoading(false)
    }
  }

  // Trigger asset enhancement
  const handleEnhance = async () => {
    setEnhancing(true)
    try {
      await api.post('/assets/enhance', {
        enable_cdn_detection: true,
        enable_protocol_inference: true,
        enable_fingerprint: true,
        enable_dedup: true,
      })

      message.success('资产增强任务已启动')
      // Refresh stats after a short delay
      setTimeout(() => {
        fetchStats()
      }, 1000)
    } catch (error: any) {
      message.error('资产增强失败')
      console.error('Error enhancing assets:', error)
    } finally {
      setEnhancing(false)
    }
  }

  // Get color based on coverage rate
  const getRateColor = (rate: number): string => {
    if (rate >= 0.9) return '#22C55E'
    if (rate >= 0.7) return '#F59E0B'
    return '#EF4444'
  }

  // Get progress status based on rate
  const getProgressStatus = (rate: number): 'success' | 'normal' | 'exception' => {
    if (rate >= 0.9) return 'success'
    if (rate >= 0.7) return 'normal'
    return 'exception'
  }

  useEffect(() => {
    fetchStats()
  }, [])

  if (loading && !stats) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  const protocolRate = (stats?.protocol?.rate ?? 0) / 100
  const fingerprintRate = (stats?.fingerprint?.rate ?? 0) / 100
  const cdnRate = (stats?.cdn?.rate ?? 0) / 100

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">资产质量分析</h1>
        <p className="page-subtitle">查看资产覆盖率和数据质量统计</p>
      </div>

      {/* Statistics Cards Row */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              borderRadius: 16,
            }}
            bodyStyle={{ padding: 24 }}
          >
            <Statistic
              title={<span style={{ color: '#94A3B8' }}>总资产数</span>}
              value={stats?.total ?? 0}
              prefix={<CloudServerOutlined style={{ color: '#0EA5E9' }} />}
              valueStyle={{ color: '#F8FAFC', fontWeight: 700 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              borderRadius: 16,
            }}
            bodyStyle={{ padding: 24 }}
          >
            <Statistic
              title={<span style={{ color: '#94A3B8' }}>协议覆盖率</span>}
              value={Math.round(protocolRate * 100)}
              suffix="%"
              prefix={<CheckCircleOutlined style={{ color: getRateColor(protocolRate) }} />}
              valueStyle={{ color: getRateColor(protocolRate), fontWeight: 700 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              borderRadius: 16,
            }}
            bodyStyle={{ padding: 24 }}
          >
            <Statistic
              title={<span style={{ color: '#94A3B8' }}>指纹覆盖率</span>}
              value={Math.round(fingerprintRate * 100)}
              suffix="%"
              prefix={<ScanOutlined style={{ color: getRateColor(fingerprintRate) }} />}
              valueStyle={{ color: getRateColor(fingerprintRate), fontWeight: 700 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            style={{
              background: 'rgba(30, 41, 59, 0.6)',
              border: '1px solid rgba(148, 163, 184, 0.1)',
              borderRadius: 16,
            }}
            bodyStyle={{ padding: 24 }}
          >
            <Statistic
              title={<span style={{ color: '#94A3B8' }}>CDN资产</span>}
              value={stats?.cdn?.count ?? 0}
              suffix={` (${Math.round(cdnRate * 100)}%)`}
              prefix={<GlobalOutlined style={{ color: '#A78BFA' }} />}
              valueStyle={{ color: '#F8FAFC', fontWeight: 700 }}
            />
          </Card>
        </Col>
      </Row>

      {/* Coverage Details */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ color: '#F8FAFC' }}>协议覆盖详情</span>}
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
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#CBD5E1' }}>已识别协议资产</span>
                <span style={{ color: '#F8FAFC' }}>
                  {stats?.protocol?.count ?? 0} / {stats?.total ?? 0}
                </span>
              </div>
              <Progress
                percent={Math.round(protocolRate * 100)}
                status={getProgressStatus(protocolRate)}
                strokeColor={getRateColor(protocolRate)}
              />
            </div>
            <div style={{ color: '#94A3B8', fontSize: 14 }}>
              {protocolRate >= 0.9 ? (
                <span style={{ color: '#22C55E' }}>
                  <CheckCircleOutlined /> 协议覆盖良好
                </span>
              ) : protocolRate >= 0.7 ? (
                <span style={{ color: '#F59E0B' }}>
                  <WarningOutlined /> 协议覆盖一般，建议补充
                </span>
              ) : (
                <span style={{ color: '#EF4444' }}>
                  <WarningOutlined /> 协议覆盖不足，需要增强
                </span>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={<span style={{ color: '#F8FAFC' }}>指纹覆盖详情</span>}
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
            <div style={{ marginBottom: 16 }}>
              <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#CBD5E1' }}>已识别指纹资产</span>
                <span style={{ color: '#F8FAFC' }}>
                  {stats?.fingerprint?.count ?? 0} / {stats?.total ?? 0}
                </span>
              </div>
              <Progress
                percent={Math.round(fingerprintRate * 100)}
                status={getProgressStatus(fingerprintRate)}
                strokeColor={getRateColor(fingerprintRate)}
              />
            </div>
            <div style={{ color: '#94A3B8', fontSize: 14 }}>
              {fingerprintRate >= 0.9 ? (
                <span style={{ color: '#22C55E' }}>
                  <CheckCircleOutlined /> 指纹覆盖良好
                </span>
              ) : fingerprintRate >= 0.7 ? (
                <span style={{ color: '#F59E0B' }}>
                  <WarningOutlined /> 指纹覆盖一般，建议补充
                </span>
              ) : (
                <span style={{ color: '#EF4444' }}>
                  <WarningOutlined /> 指纹覆盖不足，需要增强
                </span>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      {/* Multi-source Assets */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card
            title={<span style={{ color: '#F8FAFC' }}>多源资产统计</span>}
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
            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Statistic
                  title={<span style={{ color: '#94A3B8' }}>多源确认资产</span>}
                  value={stats?.multi_source?.count ?? 0}
                  suffix={` / ${stats?.total ?? 0}`}
                  valueStyle={{ color: '#F8FAFC', fontWeight: 700 }}
                />
                <div style={{ marginTop: 8 }}>
                  <Progress
                    percent={Math.round(stats?.multi_source?.rate ?? 0)}
                    status="success"
                  />
                </div>
                <div style={{ marginTop: 8, color: '#64748B', fontSize: 12 }}>
                  从多个数据源发现的资产，可信度更高
                </div>
              </Col>
              <Col xs={24} sm={12}>
                <Statistic
                  title={<span style={{ color: '#94A3B8' }}>CDN资产占比</span>}
                  value={Math.round(cdnRate * 100)}
                  suffix="%"
                  valueStyle={{ color: '#A78BFA', fontWeight: 700 }}
                />
                <div style={{ marginTop: 8 }}>
                  <Progress
                    percent={Math.round(cdnRate * 100)}
                    status="normal"
                    strokeColor="#A78BFA"
                  />
                </div>
                <div style={{ marginTop: 8, color: '#64748B', fontSize: 12 }}>
                  已识别为CDN服务的资产数量
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Enhancement Control */}
      <Card
        title={<span style={{ color: '#F8FAFC' }}>数据增强</span>}
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
        <div style={{ marginBottom: 24 }}>
          <h4 style={{ marginBottom: 12, color: '#F8FAFC' }}>资产增强功能说明</h4>
          <ul style={{ color: '#94A3B8', lineHeight: '2', paddingLeft: 20 }}>
            <li>自动识别CDN域名并关联原始域名</li>
            <li>基于端口推断HTTP/HTTPS协议</li>
            <li>从Banner/Headers提取指纹信息</li>
            <li>合并重复资产记录</li>
          </ul>
        </div>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          onClick={handleEnhance}
          loading={enhancing}
          size="large"
          style={{
            borderRadius: 8,
            background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
            border: 'none',
          }}
        >
          运行资产增强
        </Button>
        <div style={{ marginTop: 12, color: '#64748B', fontSize: 12 }}>
          点击后将启动后台任务，对现有资产数据进行自动增强处理
        </div>
      </Card>
    </div>
  )
}

export default AssetQuality
