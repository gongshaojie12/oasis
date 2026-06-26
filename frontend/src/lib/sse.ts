// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// SSE-over-fetch reader.
//
// 原生 EventSource 不能带 Authorization 头,而我们的 SSE 端点用 Bearer JWT
// 鉴权。所以用 fetch + ReadableStream 自己读 text/event-stream,按 \n\n 切
// 分事件块,解析 `event:` / `data:` 行,回调 onEvent(event, parsedData)。
import { getTokens } from './auth'

export interface SseHandlers {
  onEvent: (event: string, data: unknown) => void
  onError?: (err: unknown) => void
  signal?: AbortSignal
}

/**
 * 订阅一个 SSE 端点直到流结束或被 abort。
 * @param path 相对 /v1 的路径(如 `/workspaces/x/sandboxes/y/runs/z/events`)
 */
export async function streamSse(path: string,
                                { onEvent, onError, signal }: SseHandlers):
                                Promise<void> {
  const { access } = getTokens()
  const lang = localStorage.getItem('wanxiang.lang') || 'zh'
  try {
    const res = await fetch('/v1' + path, {
      method: 'GET',
      headers: {
        ...(access ? { Authorization: `Bearer ${access}` } : {}),
        'Accept-Language': lang,
        Accept: 'text/event-stream',
      },
      signal,
    })
    if (!res.ok || !res.body) {
      throw new Error(`SSE ${path} failed: HTTP ${res.status}`)
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      // 事件块以空行(\n\n)分隔
      let idx: number
      while ((idx = buf.indexOf('\n\n')) !== -1) {
        const block = buf.slice(0, idx)
        buf = buf.slice(idx + 2)
        parseBlock(block, onEvent)
      }
    }
    // flush 尾部残块
    if (buf.trim()) parseBlock(buf, onEvent)
  } catch (err) {
    // AbortError 是主动取消,不算错误
    if ((err as { name?: string })?.name === 'AbortError') return
    onError?.(err)
  }
}

function parseBlock(block: string,
                    onEvent: (event: string, data: unknown) => void): void {
  let event = 'message'
  const dataLines: string[] = []
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
    // 忽略 `:` 注释行与其它字段
  }
  if (dataLines.length === 0) return
  const raw = dataLines.join('\n')
  let data: unknown = raw
  try {
    data = JSON.parse(raw)
  } catch {
    /* 非 JSON data 原样传 */
  }
  onEvent(event, data)
}
