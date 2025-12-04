import axios from 'axios'
import { ElMessage } from 'element-plus'
import pinia from '@/store'
import { useUserStore } from '@/store/modules/user'

const service = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 60000,
})

service.interceptors.request.use(
  (config) => {
    const userStore = useUserStore(pinia)
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

service.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.message || '请求出错，请稍后再试'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export default service
