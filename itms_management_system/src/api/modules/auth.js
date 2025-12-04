import request from '@/api/request'

// 登录接口：传入 LoginForm（username/password 等字段）
export function loginApi(loginForm) {
  return request.post('/auth/login', loginForm)
}

// 获取当前登录用户信息
export function fetchProfileApi() {
  return request.get('/auth/profile')
}

