import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Form, Input, Button, message } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, SafetyOutlined, EyeOutlined, EyeInvisibleOutlined } from '@ant-design/icons'
import { authAPI } from '../utils/api'

const Register = () => {
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const navigate = useNavigate()

  const onFinish = async (values: {
    email: string
    password: string
    full_name: string
    confirmPassword: string
  }) => {
    if (values.password !== values.confirmPassword) {
      message.error('两次输入的密码不一致')
      return
    }

    setLoading(true)
    try {
      const response = await authAPI.register({
        email: values.email,
        password: values.password,
        full_name: values.full_name,
      })
      if (response) {
        message.success('注册成功，请登录')
        navigate('/login')
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        background: 'linear-gradient(135deg, #0C4A6E 0%, #0F172A 50%, #1E293B 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background Pattern */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: `
            radial-gradient(circle at 20% 80%, rgba(14, 165, 233, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(34, 197, 94, 0.08) 0%, transparent 50%),
            radial-gradient(circle at 40% 40%, rgba(14, 165, 233, 0.05) 0%, transparent 40%)
          `,
        }}
      />

      {/* Left Side - Branding */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '0 80px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div style={{ maxWidth: 480 }}>
          {/* Logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 40 }}>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 16,
                background: 'linear-gradient(135deg, #0EA5E9 0%, #22C55E 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 8px 32px rgba(14, 165, 233, 0.3)',
              }}
            >
              <SafetyOutlined style={{ fontSize: 32, color: 'white' }} />
            </div>
            <div>
              <div style={{ fontSize: 32, fontWeight: 800, color: 'white', lineHeight: 1.1 }}>
                Security
              </div>
              <div style={{ fontSize: 14, color: 'rgba(148, 163, 184, 0.8)', letterSpacing: 3 }}>
                PLATFORM
              </div>
            </div>
          </div>

          <h1
            style={{
              fontSize: 48,
              fontWeight: 700,
              color: 'white',
              marginBottom: 24,
              lineHeight: 1.2,
            }}
          >
            信息安全
            <br />
            <span style={{ color: '#38BDF8' }}>扫描平台</span>
          </h1>

          <p
            style={{
              fontSize: 18,
              color: 'rgba(203, 213, 225, 0.8)',
              lineHeight: 1.7,
              marginBottom: 40,
            }}
          >
            全面的资产发现与漏洞管理系统，帮助您实时监控网络安全态势，保护数字资产安全。
          </p>

          {/* Feature List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[
              { text: '智能资产发现与管理' },
              { text: '多引擎漏洞扫描' },
              { text: '实时安全态势监控' },
            ].map((feature, index) => (
              <div
                key={index}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  color: 'rgba(203, 213, 225, 0.9)',
                  fontSize: 16,
                }}
              >
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: '#22C55E',
                  }}
                />
                {feature.text}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Side - Register Form */}
      <div
        style={{
          width: 520,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 60px',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div
          style={{
            width: '100%',
            background: 'rgba(30, 41, 59, 0.9)',
            backdropFilter: 'blur(20px)',
            borderRadius: 24,
            padding: 48,
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
            border: '1px solid rgba(148, 163, 184, 0.1)',
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <h2
              style={{
                fontSize: 28,
                fontWeight: 700,
                color: '#F8FAFC',
                marginBottom: 8,
              }}
            >
              注册账号
            </h2>
            <p style={{ fontSize: 14, color: '#64748B' }}>
              创建您的账户以开始使用
            </p>
          </div>

          <Form
            name="register"
            onFinish={onFinish}
            autoComplete="off"
            layout="vertical"
            size="large"
          >
            <Form.Item
              name="full_name"
              rules={[{ required: true, message: '请输入姓名' }]}
            >
              <Input
                prefix={
                  <UserOutlined style={{ color: '#64748B', fontSize: 18 }} />
                }
                placeholder="请输入姓名"
                style={{
                  height: 52,
                  borderRadius: 12,
                  border: '1px solid rgba(148, 163, 184, 0.2)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#F8FAFC',
                }}
              />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input
                prefix={
                  <MailOutlined style={{ color: '#64748B', fontSize: 18 }} />
                }
                placeholder="请输入邮箱"
                style={{
                  height: 52,
                  borderRadius: 12,
                  border: '1px solid rgba(148, 163, 184, 0.2)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#F8FAFC',
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少6位' },
              ]}
            >
              <Input
                type={showPassword ? 'text' : 'password'}
                prefix={
                  <LockOutlined style={{ color: '#64748B', fontSize: 18 }} />
                }
                suffix={
                  <Button
                    type="text"
                    icon={
                      showPassword ? (
                        <EyeInvisibleOutlined style={{ color: '#64748B' }} />
                      ) : (
                        <EyeOutlined style={{ color: '#64748B' }} />
                      )
                    }
                    onClick={() => setShowPassword(!showPassword)}
                    style={{ padding: 0, width: 32, height: 32 }}
                  />
                }
                placeholder="请输入密码"
                style={{
                  height: 52,
                  borderRadius: 12,
                  border: '1px solid rgba(148, 163, 184, 0.2)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#F8FAFC',
                }}
              />
            </Form.Item>

            <Form.Item
              name="confirmPassword"
              rules={[
                { required: true, message: '请确认密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}
            >
              <Input
                type={showConfirmPassword ? 'text' : 'password'}
                prefix={
                  <LockOutlined style={{ color: '#64748B', fontSize: 18 }} />
                }
                suffix={
                  <Button
                    type="text"
                    icon={
                      showConfirmPassword ? (
                        <EyeInvisibleOutlined style={{ color: '#64748B' }} />
                      ) : (
                        <EyeOutlined style={{ color: '#64748B' }} />
                      )
                    }
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    style={{ padding: 0, width: 32, height: 32 }}
                  />
                }
                placeholder="请确认密码"
                style={{
                  height: 52,
                  borderRadius: 12,
                  border: '1px solid rgba(148, 163, 184, 0.2)',
                  background: 'rgba(15, 23, 42, 0.6)',
                  color: '#F8FAFC',
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 24 }}>
              <Button
                type="primary"
                htmlType="submit"
                block
                loading={loading}
                style={{
                  height: 52,
                  borderRadius: 12,
                  fontSize: 16,
                  fontWeight: 600,
                  background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                  border: 'none',
                  boxShadow: '0 4px 14px rgba(14, 165, 233, 0.3)',
                }}
              >
                注册
              </Button>
            </Form.Item>

            <div
              style={{
                textAlign: 'center',
                fontSize: 14,
                color: '#64748B',
              }}
            >
              已有账号？{' '}
              <Link
                to="/login"
                style={{
                  color: '#0EA5E9',
                  fontWeight: 600,
                }}
              >
                立即登录
              </Link>
            </div>
          </Form>
        </div>
      </div>
    </div>
  )
}

export default Register
