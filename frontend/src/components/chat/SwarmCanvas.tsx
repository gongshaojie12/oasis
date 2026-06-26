// =========== Copyright 2026 @ WANXIANG. All Rights Reserved. ===========
// 虚拟人群粒子动画 —— 移植自 docs/prototype/chat.html 的 makeSwarm()。
// 纯视觉装饰:粒子数 = 模拟样本规模(上限封顶以保性能),不代表单个真实 agent。
// 真实进度数据来自 SSE progress 事件,在 DataPanel 文字区呈现。
import { useEffect, useRef } from 'react'

interface Props {
  count: number
  height?: number
}

const COLORS = ['#A78BFA', '#C9B6F5', '#B79DF7', '#8B5CF6']
const CLUSTERS = [
  { x: 0.30, y: 0.34 }, { x: 0.68, y: 0.30 },
  { x: 0.38, y: 0.72 }, { x: 0.72, y: 0.68 },
]
// 性能上限:再多粒子肉眼也分不清,且 requestAnimationFrame 会吃满 CPU。
const MAX_PARTICLES = 1200

export function SwarmCanvas({ count, height = 150 }: Props) {
  const ref = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const cv = ref.current
    if (!cv) return
    const ctx = cv.getContext('2d')
    if (!ctx) return
    const dpr = window.devicePixelRatio || 1

    function size() {
      if (!cv) return
      cv.width = cv.offsetWidth * dpr
      cv.height = cv.offsetHeight * dpr
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    size()
    window.addEventListener('resize', size)

    const W = () => cv.offsetWidth
    const H = () => cv.offsetHeight
    const n = Math.max(1, Math.min(count || 1, MAX_PARTICLES))
    const pts = Array.from({ length: n }, () => {
      const c = Math.floor(Math.random() * 4)
      return {
        c, x: Math.random(), y: Math.random(),
        tx: CLUSTERS[c].x, ty: CLUSTERS[c].y,
        vx: 0, vy: 0, r: Math.random() * 1.3 + 0.6, ph: Math.random() * 6.28,
      }
    })

    let t = 0
    let raf = 0
    function draw() {
      ctx!.clearRect(0, 0, W(), H())
      CLUSTERS.forEach((cl, i) => {
        const g = ctx!.createRadialGradient(
          cl.x * W(), cl.y * H(), 0, cl.x * W(), cl.y * H(), W() * 0.18)
        g.addColorStop(0, COLORS[i] + '22')
        g.addColorStop(1, 'transparent')
        ctx!.fillStyle = g
        ctx!.beginPath()
        ctx!.arc(cl.x * W(), cl.y * H(), W() * 0.18, 0, 6.28)
        ctx!.fill()
      })
      t += 0.012
      for (const p of pts) {
        const dx = p.tx - p.x, dy = p.ty - p.y
        p.vx = (p.vx + dx * 0.004) * 0.92
        p.vy = (p.vy + dy * 0.004) * 0.92
        p.x += p.vx + Math.cos(t + p.ph) * 0.0006
        p.y += p.vy + Math.sin(t + p.ph) * 0.0006
        const px = p.x * W(), py = p.y * H()
        ctx!.globalAlpha = 0.85
        ctx!.fillStyle = COLORS[p.c]
        ctx!.beginPath()
        ctx!.arc(px, py, p.r, 0, 6.28)
        ctx!.fill()
        ctx!.globalAlpha = 0.16
        ctx!.beginPath()
        ctx!.arc(px, py, p.r * 2.6, 0, 6.28)
        ctx!.fill()
        ctx!.globalAlpha = 1
      }
      // 偶尔让一个粒子换簇 —— 模拟"群体动态迁移"的视觉
      if (Math.random() < 0.05) {
        const p = pts[Math.floor(Math.random() * pts.length)]
        const nc = Math.floor(Math.random() * 4)
        p.c = nc
        p.tx = CLUSTERS[nc].x + (Math.random() - 0.5) * 0.12
        p.ty = CLUSTERS[nc].y + (Math.random() - 0.5) * 0.12
      }
      raf = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', size)
    }
  }, [count])

  return (
    <canvas
      ref={ref}
      style={{ width: '100%', height, display: 'block', borderRadius: 12 }}
    />
  )
}
