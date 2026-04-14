export interface ProgressEvent {
  simulationId: string
  type: 'progress' | 'complete' | 'error'
  status: string
  progress: number
  currentStep: number
  totalSteps: number
  data?: Record<string, any>
  error?: string
  result?: Record<string, any>
}

type ProgressListener = (event: ProgressEvent) => void

class ProgressStore {
  private listeners = new Map<string, Set<ProgressListener>>()

  subscribe(simulationId: string, listener: ProgressListener): () => void {
    if (!this.listeners.has(simulationId)) {
      this.listeners.set(simulationId, new Set())
    }
    this.listeners.get(simulationId)!.add(listener)
    return () => {
      const set = this.listeners.get(simulationId)
      if (set) {
        set.delete(listener)
        if (set.size === 0) this.listeners.delete(simulationId)
      }
    }
  }

  emit(simulationId: string, event: ProgressEvent): void {
    const set = this.listeners.get(simulationId)
    if (set) {
      for (const listener of set) {
        listener(event)
      }
    }
  }

  hasListeners(simulationId: string): boolean {
    return (this.listeners.get(simulationId)?.size ?? 0) > 0
  }
}

export const progressStore = new ProgressStore()
