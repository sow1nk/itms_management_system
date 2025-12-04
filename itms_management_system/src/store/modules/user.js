import { defineStore } from 'pinia'
import pinia from '@/store'
import { loginApi, fetchProfileApi } from '@/api/modules/auth'
import { resetRouter } from '@/router'
import { usePermissionStore } from './permission'

const TOKEN_KEY = 'ms-access-token'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    id: '',
    username: '',
    name: '',
    permissions: [],
    roles: [],
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
  },
  actions: {
    async login(payload) {
      const response = await loginApi(payload)
      const token = response?.token
      if (!token) {
        throw new Error('登录失败：未获取到有效的 token')
      }
      this.token = token
      localStorage.setItem(TOKEN_KEY, token)

      const user = response.user
      if (user) {
        this.id = user.id || ''
        this.username = user.username || ''
        this.name = user.name || this.username
        this.permissions = user.permissions || []
        this.roles = user.roles || []
      } else {
        this.id = ''
        this.username = ''
        this.name = ''
        this.permissions = []
        this.roles = []
      }

      return response
    },
    async fetchProfile() {
      if (!this.token) return null
      const profile = await fetchProfileApi()
      this.id = profile.id || ''
      this.username = profile.username || ''
      this.name = profile.name || this.username
      this.permissions = profile.permissions || []
      this.roles = profile.roles || []
      return profile
    },
    logout() {
      this.token = ''
      this.id = ''
      this.username = ''
      this.name = ''
      this.permissions = []
      this.roles = []
      localStorage.removeItem(TOKEN_KEY)
      resetRouter()
      const permissionStore = usePermissionStore(pinia)
      permissionStore.reset()
    },
  },
})
