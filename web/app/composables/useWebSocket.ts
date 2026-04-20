import { ref, onUnmounted } from 'vue'

export interface WSEvent {
  type: string
  payload: Record<string, any>
  timestamp: number
}

export function useWebSocket(simulationId: string) {
  const connected = ref(false)
  const status = ref('pending')
  const progress = ref(0)
  const currentStep = ref(0)
  const totalSteps = ref(0)
  const error = ref<string | null>(null)
  const posts = ref<any[]>([])
  const metrics = ref<any>(null)
  const health = ref<any>(null)
  const lastEvent = ref<WSEvent | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const authStore = useAuthStore()

  function connect() {
    if (ws) disconnect()

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${location.host}/api/simulations/${simulationId}/ws?token=${authStore.token}`

    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data)
        lastEvent.value = data

        if (data.type === 'status') {
          if (data.payload.status) status.value = data.payload.status
          if (data.payload.progress !== undefined) progress.value = data.payload.progress
          if (data.payload.round !== undefined) currentStep.value = data.payload.round
        } else if (data.type === 'data:post') {
          posts.value.unshift(data.payload.post || data.payload)
          if (posts.value.length > 100) posts.value.pop()
        } else if (data.type === 'data:metrics') {
          metrics.value = data.payload
        } else if (data.type === 'data:health') {
          health.value = data.payload
        }
      } catch {}
    }

    ws.onerror = () => {
      connected.value = false
    }

    ws.onclose = () => {
      connected.value = false
      if (status.value === 'running' || status.value === 'pending') {
        reconnectTimer = setTimeout(() => connect(), 3000)
      }
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    connected.value = false
  }

  function send(type: string, payload: Record<string, any> = {}) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type, payload, timestamp: Date.now() }))
    }
  }

  function pause() { send('command:pause') }
  function resume() { send('command:resume') }
  function setSpeed(speed: number) { send('command:speed', { speed }) }
  function inject(content: string, agentId?: number) { send('command:inject', { content, agent_id: agentId }) }
  function step() { send('command:step') }

  onUnmounted(() => disconnect())

  return {
    connected, status, progress, currentStep, totalSteps, error,
    posts, metrics, health, lastEvent,
    connect, disconnect, send,
    pause, resume, setSpeed, inject, step,
  }
}
