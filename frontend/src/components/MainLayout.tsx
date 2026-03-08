import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Button, Badge } from 'antd'
import {
  DashboardOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  BugOutlined,
  KeyOutlined,
  UserOutlined,
  LogoutOutlined,
  DeploymentUnitOutlined,
  ExperimentOutlined,
  ToolOutlined,
  GlobalOutlined,
  BarChartOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  SettingOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { removeToken } from '../utils/auth'
import { useRoutePreloader } from '../hooks/useRoutePreloader'

const { Header, Sider, Content } = Layout

const MainLayout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { preloadRoute, cancelPreload, preloadRoutes } = useRoutePreloader()

  // 后台预加载常用路由
  useEffect(() => {
    // 延迟预加载其他常用页面，避免影响首屏加载
    const timer = setTimeout(() => {
      preloadRoutes(['/tasks', '/domains', '/vulnerabilities'], 500)
    }, 2000)
    return () => clearTimeout(timer)
  }, [preloadRoutes])

  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表盘',
    },
    {
      key: '/tasks',
      icon: <FileTextOutlined />,
      label: '任务管理',
    },
    {
      key: '/domains',
      icon: <GlobalOutlined />,
      label: '域名资产',
    },
    {
      key: '/assets',
      icon: <DatabaseOutlined />,
      label: '资产管理',
    },
    {
      key: '/asset-quality',
      icon: <BarChartOutlined />,
      label: '资产质量',
    },
    {
      key: '/vulnerabilities',
      icon: <BugOutlined />,
      label: '漏洞管理',
    },
    {
      key: '/credentials',
      icon: <KeyOutlined />,
      label: 'API 凭据',
    },
    {
      key: '/scan-plans',
      icon: <DeploymentUnitOutlined />,
      label: '扫描方案',
    },
    {
      key: '/fingerprints',
      icon: <ExperimentOutlined />,
      label: '指纹规则',
    },
    {
      key: '/tools',
      icon: <ToolOutlined />,
      label: '工具管理',
    },
  ]

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人信息',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        removeToken()
        navigate('/login')
      },
    },
  ]

  return (
    <Layout style={{ minHeight: '100vh', background: '#0F172A' }}>
      {/* Dark Blue Sidebar */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        style={{
          background: 'linear-gradient(180deg, #0C4A6E 0%, #0F172A 100%)',
          boxShadow: '4px 0 24px rgba(0, 0, 0, 0.4)',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
          overflow: 'auto',
          borderRight: '1px solid rgba(148, 163, 184, 0.1)',
        }}
      >
        {/* Logo Area */}
        <div
          style={{
            height: 80,
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            padding: collapsed ? 0 : '0 24px',
            borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: 12,
              background: 'linear-gradient(135deg, #0EA5E9 0%, #22C55E 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(14, 165, 233, 0.4)',
            }}
          >
            <SafetyOutlined style={{ fontSize: 24, color: 'white' }} />
          </div>
          {!collapsed && (
            <div style={{ marginLeft: 12 }}>
              <div
                style={{
                  color: 'white',
                  fontSize: 18,
                  fontWeight: 700,
                  lineHeight: 1.2,
                }}
              >
                Security
              </div>
              <div
                style={{
                  color: 'rgba(148, 163, 184, 0.8)',
                  fontSize: 10,
                  fontWeight: 500,
                  letterSpacing: 1,
                }}
              >
                PLATFORM
              </div>
            </div>
          )}
        </div>

        {/* Menu */}
        <div
          onMouseOver={(e) => {
            const menuItem = (e.target as HTMLElement).closest('.ant-menu-item')
            if (menuItem) {
              const key = menuItem.getAttribute('data-menu-id')
              if (key && key.startsWith('/')) {
                preloadRoute(key, 100)
              }
            }
          }}
          onMouseOut={(e) => {
            const menuItem = (e.target as HTMLElement).closest('.ant-menu-item')
            if (menuItem) {
              const key = menuItem.getAttribute('data-menu-id')
              if (key && key.startsWith('/')) {
                cancelPreload(key)
              }
            }
          }}
        >
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{
              background: 'transparent',
              border: 'none',
              padding: '12px 8px',
            }}
          />
        </div>
      </Sider>

      <Layout
        style={{
          marginLeft: collapsed ? 80 : 240,
          transition: 'all 0.2s ease',
          background: '#0F172A',
        }}
      >
        {/* Dark Blue Header */}
        <Header
          style={{
            background: 'rgba(30, 41, 59, 0.8)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
            padding: '0 32px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            position: 'sticky',
            top: 0,
            zIndex: 99,
            height: 80,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              style={{
                fontSize: 18,
                color: '#94A3B8',
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'rgba(51, 65, 85, 0.5)',
              }}
            />
            <div>
              <div
                style={{
                  fontSize: 20,
                  fontWeight: 700,
                  color: '#F8FAFC',
                  lineHeight: 1.3,
                }}
              >
                信息安全扫描平台
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: '#64748B',
                }}
              >
                全面资产发现与漏洞管理系统
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* Notification */}
            <Badge count={3} size="small" color="#0EA5E9">
              <Button
                type="text"
                icon={<BellOutlined style={{ fontSize: 20, color: '#94A3B8' }} />}
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 12,
                  background: 'rgba(51, 65, 85, 0.5)',
                  border: '1px solid rgba(148, 163, 184, 0.1)',
                }}
              />
            </Badge>

            {/* User Dropdown */}
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '8px 16px',
                  borderRadius: 12,
                  background: 'rgba(51, 65, 85, 0.5)',
                  border: '1px solid rgba(148, 163, 184, 0.1)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <Avatar
                  size={36}
                  icon={<UserOutlined />}
                  style={{
                    background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
                  }}
                />
                <div>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 600,
                      color: '#F8FAFC',
                      lineHeight: 1.3,
                    }}
                  >
                    管理员
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: '#64748B',
                    }}
                  >
                    admin@security.com
                  </div>
                </div>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* Main Content */}
        <Content
          style={{
            margin: '32px',
            minHeight: 280,
          }}
        >
          <div className="animate-fade-in">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout
