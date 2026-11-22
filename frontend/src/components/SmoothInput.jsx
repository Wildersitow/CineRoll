import { useLayoutEffect, useRef } from 'react'

export default function SmoothInput(props) {
  const field = useRef(null)
  const cursor = useRef(null)
  useLayoutEffect(() => {
    const input = field.current
    const caret = cursor.current
    const context = document.createElement('canvas').getContext('2d')
    if (!context) return
    const preference = matchMedia('(prefers-reduced-motion: reduce)')
    let composing = false
    function update() {
      const start = input.selectionStart
      const active = document.activeElement === input && !composing && !preference.matches &&
        (start === input.selectionEnd) && start !== null
      caret.hidden = !active
      input.classList.toggle('custom-caret', active)
      if (!active) return
      const style = getComputedStyle(input)
      context.font = style.font
      const prefix = input.type === 'password' ? '•'.repeat(start) : input.value.slice(0,start)
      const x = parseFloat(style.paddingLeft) + context.measureText(prefix).width - input.scrollLeft
      caret.style.transform = `translateX(${Math.max(0, Math.min(x, input.clientWidth - 2))}px)`
    }
    function begin() { composing = true; update() }
    function end() { composing = false; update() }
    const events = ['input','focus','blur','keyup','click','select','scroll','selectionchange']
    events.forEach(name => input.addEventListener(name, update))
    document.addEventListener('selectionchange', update)
    preference.addEventListener('change', update)
    input.addEventListener('compositionstart', begin)
    input.addEventListener('compositionend', end)
    update()
    return () => {
      events.forEach(name => input.removeEventListener(name, update))
      document.removeEventListener('selectionchange', update)
      preference.removeEventListener('change', update)
      input.removeEventListener('compositionstart', begin)
      input.removeEventListener('compositionend', end)
    }
  }, [props.type])
  return <><input {...props} ref={field} /><i className="smooth-caret" ref={cursor} hidden aria-hidden="true" /></>
}
