import { success, error, ErrorCodes } from './response'

interface EngineTaskResponse {
  task_id: string
  status: string
}

interface EngineStatusResponse {
  task_id: string
  status: string
  progress: number
  current_step: number
  total_steps: number
}

export async function submitToEngine(params: {
  platform_type: string
  num_steps: number
  num_agents: number
  profile_path?: string
  agent_profiles?: Array<Record<string, any>>
  seed_content?: string
  available_actions?: string[]
  llm_provider?: string
  llm_model?: string
}): Promise<EngineTaskResponse> {
  const config = useRuntimeConfig()
  const response = await $fetch<EngineTaskResponse>(`${config.engineUrl}/engine/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Internal-Key': config.internalApiKey,
    },
    body: params,
  })
  return response
}

export async function getEngineTaskStatus(taskId: string): Promise<EngineStatusResponse> {
  const config = useRuntimeConfig()
  return await $fetch<EngineStatusResponse>(`${config.engineUrl}/engine/tasks/${taskId}`, {
    headers: { 'X-Internal-Key': config.internalApiKey },
  })
}

export async function cancelEngineTask(taskId: string): Promise<{ task_id: string; cancelled: boolean }> {
  const config = useRuntimeConfig()
  return await $fetch(`${config.engineUrl}/engine/tasks/${taskId}/cancel`, {
    method: 'POST',
    headers: { 'X-Internal-Key': config.internalApiKey },
  })
}
