/**
 * 权限指令
 * 用于在模板中快速进行权限控制
 * 使用方式：
 * 1. v-permission="'user:manage:create'" - 单个权限
 * 2. v-permission="['user:manage:create', 'user:manage:update']" - 多个权限（满足任一）
 * 3. v-permission:every="['user:manage:create', 'user:manage:update']" - 多个权限（全部满足）
 * 4. v-permission.hide="'user:manage:create'" - 不满足权限时隐藏元素（默认是禁用）
 */

import { useUserStore } from '@/store/modules/user'
import { hasPermission } from '@/utils/permission'

export const permission = {
  mounted(el, binding) {
    const userStore = useUserStore()
    const { value, arg, modifiers } = binding

    // 超级管理员拥有所有权限
    if ((userStore.roles || []).includes('super_admin')) {
      return
    }

    // 获取用户权限
    const userPermissions = userStore.permissions || []

    // 检查模式：some（满足任一） 或 every（全部满足）
    const mode = arg === 'every' ? 'every' : 'some'

    // 检查权限
    const hasAuth = hasPermission(userPermissions, value, mode)

    if (!hasAuth) {
      if (modifiers.hide) {
        // 使用 hide 修饰符时，隐藏元素
        el.style.display = 'none'
      } else {
        // 默认禁用元素
        el.disabled = true
        el.classList.add('is-disabled')
        // 如果是 Element Plus 的组件，可能需要特殊处理
        if (el.classList.contains('el-button')) {
          el.style.pointerEvents = 'none'
          el.style.opacity = '0.6'
        }
      }
    }
  },

  updated(el, binding) {
    // 当权限值更新时重新检查
    const userStore = useUserStore()
    const { value, arg, modifiers } = binding

    // 超级管理员拥有所有权限
    if ((userStore.roles || []).includes('super_admin')) {
      // 确保元素可用
      el.style.display = ''
      el.disabled = false
      el.classList.remove('is-disabled')
      el.style.pointerEvents = ''
      el.style.opacity = ''
      return
    }

    const userPermissions = userStore.permissions || []
    const mode = arg === 'every' ? 'every' : 'some'
    const hasAuth = hasPermission(userPermissions, value, mode)

    if (!hasAuth) {
      if (modifiers.hide) {
        el.style.display = 'none'
      } else {
        el.disabled = true
        el.classList.add('is-disabled')
        if (el.classList.contains('el-button')) {
          el.style.pointerEvents = 'none'
          el.style.opacity = '0.6'
        }
      }
    } else {
      // 恢复元素状态
      el.style.display = ''
      el.disabled = false
      el.classList.remove('is-disabled')
      el.style.pointerEvents = ''
      el.style.opacity = ''
    }
  },
}

export default {
  install(app) {
    app.directive('permission', permission)
  },
}
