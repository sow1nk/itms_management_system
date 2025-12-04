import pinia from '@/store'
import { useUserStore } from '@/store/modules/user'
import { usePermissionStore } from '@/store/modules/permission'
import { addDynamicRoutes } from './index'

const whiteList = ['/login']

export function setupRouterGuard(router) {
  router.beforeEach(async (to, from, next) => {
    const userStore = useUserStore(pinia)
    const permissionStore = usePermissionStore(pinia)
    const hasToken = Boolean(userStore.token)

    if (hasToken) {
      if (to.path === '/login') {
        next({ path: '/' })
        return
      }

      if (!userStore.permissions.length) {
        try {
          await userStore.fetchProfile()
        } catch (error) {
          userStore.logout()
          next('/login')
          return
        }
      }

      if (!permissionStore.isLoaded) {
        try {
          const accessRoutes = await permissionStore.generateRoutes(userStore.permissions, userStore.roles || [])
          addDynamicRoutes(accessRoutes)
          next({ ...to, replace: true })
          return
        } catch {
          userStore.logout()
          next('/login')
          return
        }
      }

      next()
    } else if (whiteList.includes(to.path)) {
      next()
    } else {
      next('/login')
    }
  })
}
