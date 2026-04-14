import { describe, it, expect, vi } from 'vitest'

describe('ProgressStore', () => {
  it('emits events to subscribers', async () => {
    // Re-import for fresh instance
    const { ProgressStore } = await import('../../server/utils/progress-store')
    // We'll test the class directly since the module exports a singleton
    // Actually test the exported progressStore
    const { progressStore } = await import('../../server/utils/progress-store')

    const listener = vi.fn()
    const unsubscribe = progressStore.subscribe('sim-test-1', listener)

    const event = {
      simulationId: 'sim-test-1',
      type: 'progress' as const,
      status: 'running',
      progress: 0.5,
      currentStep: 3,
      totalSteps: 6,
    }
    progressStore.emit('sim-test-1', event)
    expect(listener).toHaveBeenCalledWith(event)

    unsubscribe()
    progressStore.emit('sim-test-1', event)
    expect(listener).toHaveBeenCalledTimes(1)
  })

  it('does not emit to other simulation listeners', async () => {
    const { progressStore } = await import('../../server/utils/progress-store')

    const listener = vi.fn()
    const unsub = progressStore.subscribe('sim-a-test', listener)
    progressStore.emit('sim-b-test', {
      simulationId: 'sim-b-test', type: 'progress', status: 'running',
      progress: 0.1, currentStep: 1, totalSteps: 10,
    })
    expect(listener).not.toHaveBeenCalled()
    unsub()
  })
})
