import { createRouter, createWebHistory } from 'vue-router'
import { constantRoutes } from './routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: constantRoutes,
  scrollBehavior: () => ({ left: 0, top: 0 }),
})

const dynamicRouteNames = new Set()

export function addDynamicRoutes(routes = []) {
  routes.forEach((route) => {
    router.addRoute(route)
    if (route.name) {
      dynamicRouteNames.add(route.name)
    }
  })
}

export function resetRouter() {
  dynamicRouteNames.forEach((name) => {
    if (router.hasRoute(name)) {
      router.removeRoute(name)
    }
  })
  dynamicRouteNames.clear()
}

export default router
