// Tiny dependency-free confetti burst. Skipped entirely for reduced-motion users.

interface Bit {
  x: number; y: number; vx: number; vy: number; r: number; vr: number; w: number; h: number; color: string
}

export function confetti(intensity = 1) {
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
  const css = getComputedStyle(document.documentElement)
  const colors = ['--thread', '--chalk', '--brand', '--hint', '--danger'].map((v) => css.getPropertyValue(v).trim() || '#f5b941')
  const canvas = document.createElement('canvas')
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = innerWidth * dpr
  canvas.height = innerHeight * dpr
  Object.assign(canvas.style, { position: 'fixed', inset: '0', width: '100vw', height: '100vh', pointerEvents: 'none', zIndex: '70' })
  document.body.appendChild(canvas)
  const ctx = canvas.getContext('2d')!
  ctx.scale(dpr, dpr)

  const bits: Bit[] = []
  const n = Math.round(150 * intensity)
  for (let i = 0; i < n; i++) {
    const fromLeft = i % 2 === 0
    bits.push({
      x: fromLeft ? -10 : innerWidth + 10,
      y: innerHeight * (0.55 + Math.random() * 0.3),
      vx: (fromLeft ? 1 : -1) * (6 + Math.random() * 9),
      vy: -(9 + Math.random() * 11),
      r: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.4,
      w: 6 + Math.random() * 6,
      h: 4 + Math.random() * 4,
      color: colors[i % colors.length],
    })
  }
  const start = performance.now()
  const frame = (t: number) => {
    const elapsed = t - start
    ctx.clearRect(0, 0, innerWidth, innerHeight)
    for (const b of bits) {
      b.vy += 0.35
      b.vx *= 0.985
      b.x += b.vx
      b.y += b.vy
      b.r += b.vr
      ctx.save()
      ctx.globalAlpha = Math.max(0, 1 - elapsed / 2800)
      ctx.translate(b.x, b.y)
      ctx.rotate(b.r)
      ctx.fillStyle = b.color
      ctx.fillRect(-b.w / 2, -b.h / 2, b.w, b.h)
      ctx.restore()
    }
    if (elapsed < 2800) requestAnimationFrame(frame)
    else canvas.remove()
  }
  requestAnimationFrame(frame)
}
