import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, Button } from 'antd'
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
} from '@ant-design/icons'
import type { MenuProps } from 'antd'
import { removeToken } from '../utils/auth'

const { Header, Sider, Content } = Layout

const MainLayout = () => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()

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
      onClick: () => {
        // TODO: 实现个人信息页面
      },
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
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: collapsed ? 16 : 18,
            fontWeight: 'bold',
          }}
        >
          {collapsed ? 'SP' : 'Security Platform'}
        </div>
        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: 20, fontWeight: 'bold' }}>
            信息安全扫描平台
          </div>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Button type="text" icon={<Avatar icon={<UserOutlined />} />} />
          </Dropdown>
        </Header>
        <Content
          style={{
            margin: '24px',
            padding: 24,
            background: '#fff',
            borderRadius: 8,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout

