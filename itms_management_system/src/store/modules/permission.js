import { defineStore } from 'pinia'
import { constantRoutes, asyncRoutes } from '@/router/routes'

function hasPermission(route, permissions = [], roles = []) {
  if (!route.meta || !route.meta.permission) {
    return hasRole(route, roles)
  }
  const permResult = route.meta.permission.some((perm) => permissions.includes(perm))
  return permResult && hasRole(route, roles)
}

function hasRole(route, roles = []) {
  if (!route.meta || !route.meta.roles || !route.meta.roles.length) {
    return true
  }
  return route.meta.roles.some((role) => roles.includes(role))
}

function filterAsyncRoutes(routes = [], permissions = [], roles = []) {
  const res = []

  routes.forEach((route) => {
    const current = { ...route }
    if (hasPermission(current, permissions, roles)) {
      if (current.children) {
        current.children = filterAsyncRoutes(current.children, permissions, roles)
      }
      res.push(current)
    }
  })

  return res
}

function getVisibleConstantRoutes() {
  return constantRoutes.filter((route) => !route.meta?.hidden)
}

export const usePermissionStore = defineStore('permission', {
  state: () => ({
    isLoaded: false,
    menuRoutes: getVisibleConstantRoutes(),
  }),
  actions: {
    generateRoutes(permissions, roles = []) {
      const accessedRoutes = filterAsyncRoutes(asyncRoutes, permissions, roles)
      this.menuRoutes = [...getVisibleConstantRoutes(), ...accessedRoutes]
      this.isLoaded = true
      return accessedRoutes
    },
    reset() {
      this.isLoaded = false
      this.menuRoutes = getVisibleConstantRoutes()
    },
  },
})
