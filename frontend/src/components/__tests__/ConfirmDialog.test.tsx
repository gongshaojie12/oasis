// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ConfirmDialog } from '@/components/data/ConfirmDialog'
import { switchLang } from '@/lib/i18n'

describe('ConfirmDialog', () => {
  it('renders nothing when closed', () => {
    switchLang('zh')
    const { container } = render(
      <ConfirmDialog
        isOpen={false}
        title="x"
        message="y"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    )
    expect(container.textContent).toBe('')
  })

  it('renders title, message and fires onConfirm', () => {
    switchLang('zh')
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <ConfirmDialog
        isOpen
        title="删除工作区"
        message="确认删除？"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    )
    expect(screen.getByText('删除工作区')).toBeInTheDocument()
    expect(screen.getByText('确认删除？')).toBeInTheDocument()
    fireEvent.click(screen.getByText('确认'))
    expect(onConfirm).toHaveBeenCalled()
  })

  it('disables buttons while loading', () => {
    switchLang('zh')
    render(
      <ConfirmDialog
        isOpen
        title="x"
        message="y"
        loading
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    )
    expect(screen.getByText('取消')).toBeDisabled()
  })
})
