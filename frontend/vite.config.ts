import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import vitePluginImp from 'vite-plugin-imp'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    // Ant Design 按需导入
    vitePluginImp({
      libList: [
        {
          libName: 'antd',
          style: (name) => `antd/es/${name}/style`,
        },
      ],
    }),
    // PWA 和 Service Worker
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        // 缓存策略
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/.*\.(?:png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'images-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30天
              },
            },
          },
          {
            urlPattern: /^https:\/\/.*\.js$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'js-cache',
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 * 24 * 7, // 7天
              },
            },
          },
          {
            urlPattern: /^https:\/\/.*\.css$/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'css-cache',
              expiration: {
                maxEntries: 20,
                maxAgeSeconds: 60 * 60 * 24 * 7,
              },
            },
          },
        ],
        // 预缓存所有静态资源
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        // 跳过等待，立即激活
        skipWaiting: true,
        clientsClaim: true,
      },
      // 禁用 manifest 生成（可选）
      manifest: false,
    }),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 启用压缩
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    },
    // 分包策略
    rollupOptions: {
      output: {
        // 手动分块
        manualChunks: (id) => {
          // React 核心库
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') || id.includes('node_modules/react-router')) {
            return 'react-vendor'
          }
          // Ant Design 组件库 - 按使用频率分块
          if (id.includes('node_modules/antd')) {
            // 核心组件（Layout, Menu, Button 等首屏必需）
            if (/\/(button|menu|layout|dropdown|avatar|badge|space)/.test(id)) {
              return 'antd-core'
            }
            // 表单组件
            if (/\/(form|input|input-number|select|checkbox|radio|switch|upload)/.test(id)) {
              return 'antd-form'
            }
            // 数据展示组件（Table 很大，单独处理）
            if (/\/(table|pagination)/.test(id)) {
              return 'antd-table'
            }
            // 其他数据展示
            if (/\/(card|descriptions|list|tag|tooltip|statistic|progress|collapse)/.test(id)) {
              return 'antd-data'
            }
            // 反馈组件
            if (/\/(modal|message|popconfirm|notification|skeleton|spin)/.test(id)) {
              return 'antd-feedback'
            }
            // Ant Design 其他
            return 'antd-other'
          }
          // 工具库
          if (id.includes('node_modules/dayjs') || id.includes('node_modules/axios')) {
            return 'utils-vendor'
          }
          // XLSX 单独分包（很大）
          if (id.includes('node_modules/xlsx')) {
            return 'xlsx'
          }
          // Ant Design 图标库
          if (id.includes('node_modules/@ant-design/icons')) {
            return 'antd-icons'
          }
        },
        // 自动分块配置
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name.split('.')
          const ext = info[info.length - 1]
          if (/\.(png|jpe?g|gif|svg|webp|ico)$/i.test(assetInfo.name)) {
            return 'assets/images/[name]-[hash][extname]'
          }
          if (/\.css$/i.test(assetInfo.name)) {
            return 'assets/css/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        },
      },
    },
    // 启用 sourcemap 用于分析（生产环境可关闭）
    sourcemap: false,
    // 压缩 chunk 大小警告阈值
    chunkSizeWarningLimit: 1000,
  },
  // 优化依赖预构建
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', 'antd', 'dayjs'],
  },
})
