import { computed } from 'vue'
import { useUserStore } from '@/store/modules/user'
import { hasPermission, hasRole, checkAccess } from '@/utils/permission'

/**
 * 权限检查 Composable
 * 用于在 Vue 组件中方便地进行权限检查
 */
export function usePermission() {
  const userStore = useUserStore()
  console.log('usePermission - userStore.permissions:', userStore.permissions)

  // 当前用户权限
  const permissions = computed(() => userStore.permissions || [])

  // 当前用户角色
  const roles = computed(() => userStore.roles || [])

  // 是否是超级管理员
  const isSuperAdmin = computed(() => roles.value.includes('super_admin'))

  /**
   * 检查是否拥有指定权限
   * @param {string|Array} requiredPermissions - 需要的权限
   * @param {string} mode - 'some' 或 'every'
   * @returns {boolean}
   */
  const can = (requiredPermissions, mode = 'some') => {
    // 超级管理员拥有所有权限
    if (isSuperAdmin.value) {
      return true
    }
    return hasPermission(permissions.value, requiredPermissions, mode)
  }

  /**
   * 检查是否拥有指定角色
   * @param {string|Array} requiredRoles - 需要的角色
   * @returns {boolean}
   */
  const is = (requiredRoles) => {
    return hasRole(roles.value, requiredRoles)
  }

  /**
   * 检查是否拥有权限或角色（满足任一即可）
   * @param {Object} requirements - { permissions, roles }
   * @returns {boolean}
   */
  const check = (requirements) => {
    // 超级管理员拥有所有权限
    if (isSuperAdmin.value) {
      return true
    }
    return checkAccess({ permissions: permissions.value, roles: roles.value }, requirements)
  }

  return {
    permissions,
    roles,
    isSuperAdmin,
    can,
    is,
    check,
  }
}
