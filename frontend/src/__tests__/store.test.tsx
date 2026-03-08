import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { StoreProvider, useStore } from '../store'
import { User } from '../types'

describe('useStore', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('should initialize with default state', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <StoreProvider>{children}</StoreProvider>
    )
    const { result } = renderHook(() => useStore(), { wrapper })

    expect(result.current.state.user).toBeNull()
    expect(result.current.state.tasks).toEqual([])
    expect(result.current.state.assets).toEqual([])
    expect(result.current.state.vulnerabilities).toEqual([])
    expect(result.current.state.loading).toBe(false)
    expect(result.current.state.error).toBeNull()
  })

  it('should set user', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <StoreProvider>{children}</StoreProvider>
    )
    const { result } = renderHook(() => useStore(), { wrapper })

    const testUser: User = {
      id: 1,
      email: 'test@example.com',
      full_name: 'Test User',
      is_active: true,
      role: 'user',
      tenant_id: 1,
      created_at: '2024-01-01T00:00:00Z',
    }

    act(() => {
      result.current.actions.setUser(testUser)
    })

    expect(result.current.state.user).toEqual(testUser)
  })

  it('should add task', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <StoreProvider>{children}</StoreProvider>
    )
    const { result } = renderHook(() => useStore(), { wrapper })

    const testTask = {
      id: 1,
      name: 'Test Task',
      status: 'pending' as const,
      progress: 0,
      input_data: {},
      tenant_id: 1,
      created_at: '2024-01-01T00:00:00Z',
    }

    act(() => {
      result.current.actions.addTask(testTask)
    })

    expect(result.current.state.tasks).toHaveLength(1)
    expect(result.current.state.tasks[0]).toEqual(testTask)
  })

  it('should update task', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <StoreProvider>{children}</StoreProvider>
    )
    const { result } = renderHook(() => useStore(), { wrapper })

    const testTask = {
      id: 1,
      name: 'Test Task',
      status: 'pending' as const,
      progress: 0,
      input_data: {},
      tenant_id: 1,
      created_at: '2024-01-01T00:00:00Z',
    }

    act(() => {
      result.current.actions.addTask(testTask)
    })

    act(() => {
      result.current.actions.updateTask(1, { status: 'running', progress: 50 })
    })

    expect(result.current.state.tasks[0].status).toBe('running')
    expect(result.current.state.tasks[0].progress).toBe(50)
  })

  it('should set error', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <StoreProvider>{children}</StoreProvider>
    )
    const { result } = renderHook(() => useStore(), { wrapper })

    act(() => {
      result.current.actions.setError('Test error')
    })

    expect(result.current.state.error).toBe('Test error')
  })

  it('should clear error', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <StoreProvider>{children}</StoreProvider>
    )
    const { result } = renderHook(() => useStore(), { wrapper })

    act(() => {
      result.current.actions.setError('Test error')
      result.current.actions.clearError()
    })

    expect(result.current.state.error).toBeNull()
  })
})
