import { useLayoutEffect, useRef } from 'react'
import { animate } from 'motion'
import curtainTexture from '../assets/telon-terciopelo.webp'
import { CLOTH_STEP, createCurtainCloth } from '../utils/curtainCloth'
import { createCurtainRenderer } from '../utils/curtainRenderer'

export default function CurtainOpening() {
  const canvasRef = useRef(null)

  useLayoutEffect(() => {
    const canvas = canvasRef.current
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    if (reducedMotion.matches || document.activeElement !== document.body || !('ResizeObserver' in window)) return

    const renderer = createCurtainRenderer(canvas)
    if (!renderer) return

    const texture = new Image()
    let animation
    let aspect
    let panels = []
    let progress = 0
    let frame = 0
    let lastTime
    let openingStart
    let remainder = 0
    let finished = false

    function resize() {
      const { width, height } = canvas.getBoundingClientRect()
      if (!width || !height) return
      const scale = Math.min(window.devicePixelRatio || 1, 1.75)
      const pixelWidth = Math.round(width * scale)
      const pixelHeight = Math.round(height * scale)
      if (panels.length && canvas.width === pixelWidth && canvas.height === pixelHeight) return
      canvas.width = pixelWidth
      canvas.height = pixelHeight
      aspect = height / width
      panels = [createCurtainCloth(aspect, -1), createCurtainCloth(aspect, 1)]
      // Al rotar la pantalla, reconstruir la postura actual antes de volver a dibujar.
      if (progress > 0) {
        for (let index = 0; index < 44; index += 1) {
          for (const panel of panels) panel.step(progress * index / 43)
        }
      }
      renderer.draw(aspect, panels, progress === 0)
    }

    function draw(time) {
      openingStart ??= time
      remainder += Math.min((time - (lastTime ?? time)) / 1000, .05)
      lastTime = time
      while (remainder >= CLOTH_STEP) {
        for (const panel of panels) panel.step(progress)
        remainder -= CLOTH_STEP
      }
      if (panels.length) renderer.draw(aspect, panels, progress === 0)
      if ((progress > .85 && panels.every((panel) => panel.isOffscreen())) || time - openingStart > 2650) {
        finish()
      } else {
        frame = requestAnimationFrame(draw)
      }
    }

    const observer = new ResizeObserver(resize)

    function finish() {
      if (finished) return
      finished = true
      delete canvas.dataset.opening
      delete canvas.dataset.preparing
      texture.onload = texture.onerror = null
      observer.disconnect()
      cancelAnimationFrame(frame)
      animation?.stop()
      renderer.dispose()
      canvas.removeEventListener('webglcontextlost', finish)
      document.removeEventListener('focusin', finish)
      reducedMotion.removeEventListener('change', handleMotionPreference)
    }

    function handleMotionPreference(event) {
      if (event.matches) finish()
    }

    texture.onload = () => {
      if (finished) return
      renderer.setTexture(texture)
      canvas.dataset.opening = ''
      delete canvas.dataset.preparing
      resize()
      observer.observe(canvas)
      animation = animate(0, 1, {
        duration: 1.55,
        delay: .16,
        ease: [.42, 0, .25, 1],
        onUpdate: (position) => { progress = position },
      })
      frame = requestAnimationFrame(draw)
    }

    canvas.dataset.preparing = ''
    texture.onerror = finish
    canvas.addEventListener('webglcontextlost', finish)
    document.addEventListener('focusin', finish)
    reducedMotion.addEventListener('change', handleMotionPreference)
    texture.src = curtainTexture
    return finish
  }, [])

  return <canvas className="cinema-curtain" ref={canvasRef} aria-hidden="true" />
}
