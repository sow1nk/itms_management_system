// 全局对话框拖拽支持（适用于 Element Plus 的 el-dialog）
// 导入即可初始化：initDialogDrag()

export function initDialogDrag() {
  if (typeof window === 'undefined') return
  if (window.__el_dialog_drag_installed) return
  window.__el_dialog_drag_installed = true

  document.addEventListener('mousedown', (e) => {
    const header = e.target.closest('.el-dialog__header')
    if (!header) return

    const dialog = header.closest('.el-dialog')
    if (!dialog) return

    // ignore clicks on header buttons (close/maximize) so they still work
    if (e.target.closest('.el-dialog__headerbtn') || e.target.classList.contains('el-dialog__close')) return

    const wrapper = dialog.closest('.el-dialog__wrapper')
    if (!wrapper) return

    // only draggable when visible
    if (wrapper.style.display === 'none' || wrapper.getAttribute('aria-hidden') === 'true') return

    const dragDom = dialog

    // cancel text selection while dragging
    document.body.style.userSelect = 'none'

    const startX = e.clientX
    const startY = e.clientY

    // compute current position via bounding rect (handles centered transform cases)
    const rect = dragDom.getBoundingClientRect()
    let left = rect.left
    let top = rect.top

    // ensure fixed positioning (dialog often uses transform for centering)
    dragDom.style.position = 'fixed'
    dragDom.style.margin = '0'
    dragDom.style.left = left + 'px'
    dragDom.style.top = top + 'px'

    function onMove(evt) {
      const deltaX = evt.clientX - startX
      const deltaY = evt.clientY - startY
      let newLeft = left + deltaX
      let newTop = top + deltaY

      const minLeft = 0
      const minTop = 0
      const maxLeft = document.documentElement.clientWidth - dragDom.offsetWidth
      const maxTop = document.documentElement.clientHeight - dragDom.offsetHeight

      if (newLeft < minLeft) newLeft = minLeft
      if (newLeft > maxLeft) newLeft = maxLeft
      if (newTop < minTop) newTop = minTop
      if (newTop > maxTop) newTop = maxTop

      dragDom.style.left = newLeft + 'px'
      dragDom.style.top = newTop + 'px'
    }

    function onUp() {
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.style.userSelect = ''
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  })
}

export default { initDialogDrag }
