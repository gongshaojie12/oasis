import { ref, onUnmounted } from 'vue'

export interface SSEProgressEvent {
  type: 'progress' | 'complete' | 'error'
  status: string
  progress: number
  currentStep?: number
  totalSteps?: number
  data?: Record<string, any>
  error?: string
  result?: Record<string, any>
}

export function useSSE(simulationId: string) {
  const progress = ref(0)
  const status = ref('pending')
  const currentStep = ref(0)
  const totalSteps = ref(0)
  const error = ref<string | null>(null)
  const isConnected = ref(false)
  const lastEvent = ref<SSEProgressEvent | null>(null)

  let eventSource: EventSource | null = null

  const authStore = useAuthStore()

  function connect() {
    if (eventSource) disconnect()

    const url = `/api/simulations/${simulationId}/progress?token=${authStore.token}`
    eventSource = new EventSource(url)
    isConnected.value = true

    eventSource.onmessage = (event) => {
      try {
        const data: SSEProgressEvent = JSON.parse(event.data)
        lastEvent.value = data
        progress.value = data.progress
        status.value = data.status
        if (data.currentStep !== undefined) currentStep.value = data.currentStep
        if (data.totalSteps !== undefined) totalSteps.value = data.totalSteps
        if (data.error) error.value = data.error

        if (data.type === 'complete' || data.type === 'error') {
          disconnect()
        }
      } catch {
        // Ignore malformed events
      }
    }

    eventSource.onerror = () => {
      isConnected.value = false
      setTimeout(() => {
        if (status.value === 'running' || status.value === 'pending') {
          connect()
        }
      }, 3000)
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isConnected.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    progress,
    status,
    currentStep,
    totalSteps,
    error,
    isConnected,
    lastEvent,
    connect,
    disconnect,
  }
}
