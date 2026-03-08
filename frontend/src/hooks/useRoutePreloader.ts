/**
 * 路由预加载 Hook
 * 当用户鼠标悬停在菜单项上时，预加载对应页面 chunk
 * 实现接近原生的页面切换体验
 */

import { useCallback, useRef } from 'react'

// 页面组件预加载映射
const pagePreloaders: Record<string, () => Promise<any>> = {
  '/dashboard': () => import('../pages/Dashboard'),
  '/tasks': () => import('../pages/Tasks'),
  '/tasks/:id': () => import('../pages/TaskDetail'),
  '/domains': () => import('../pages/Domains'),
  '/assets': () => import('../pages/Assets'),
  '/assets/:id': () => import('../pages/AssetDetail'),
  '/asset-quality': () => import('../pages/AssetQuality'),
  '/vulnerabilities': () => import('../pages/Vulnerabilities'),
  '/vulnerabilities/:id': () => import('../pages/VulnerabilityDetail'),
  '/credentials': () => import('../pages/Credentials'),
  '/scan-plans': () => import('../pages/ScanPlans'),
  '/fingerprints': () => import('../pages/Fingerprints'),
  '/tools': () => import('../pages/Tools'),
}

export const useRoutePreloader = () => {
  const preloadedRoutes = useRef<Set<string>>(new Set())
  const preloadTimers = useRef<Record<string, number>>({})

  /**
   * 预加载指定路由的页面组件
   * @param path 路由路径
   * @param delay 延迟时间（毫秒），避免快速滑过菜单时无谓加载
   */
  const preloadRoute = useCallback((path: string, delay: number = 100) => {
    // 清理可能存在的定时器
    if (preloadTimers.current[path]) {
      clearTimeout(preloadTimers.current[path])
    }

    // 已预加载过的页面不再重复加载
    if (preloadedRoutes.current.has(path)) {
      return
    }

    // 延迟预加载，避免用户快速滑过菜单时触发大量请求
    preloadTimers.current[path] = setTimeout(() => {
      const preloader = pagePreloaders[path]
      if (preloader) {
        preloader()
          .then(() => {
            preloadedRoutes.current.add(path)
            console.log(`[Preload] Route ${path} preloaded successfully`)
          })
          .catch((err) => {
            console.warn(`[Preload] Failed to preload ${path}:`, err)
          })
      }
    }, delay)
  }, [])

  /**
   * 取消预加载（鼠标离开菜单时调用）
   */
  const cancelPreload = useCallback((path: string) => {
    if (preloadTimers.current[path]) {
      clearTimeout(preloadTimers.current[path])
      delete preloadTimers.current[path]
    }
  }, [])

  /**
   * 预加载多个路由（可用于预加载相关页面）
   */
  const preloadRoutes = useCallback((paths: string[], delay: number = 200) => {
    setTimeout(() => {
      paths.forEach((path) => {
        if (!preloadedRoutes.current.has(path)) {
          const preloader = pagePreloaders[path]
          if (preloader) {
            preloader().then(() => {
              preloadedRoutes.current.add(path)
            })
          }
        }
      })
    }, delay)
  }, [])

  return {
    preloadRoute,
    cancelPreload,
    preloadRoutes,
    preloadedRoutes: preloadedRoutes.current,
  }
}

export default useRoutePreloader
