import request from '@/api/request'

// 添加C端用户
export function addAppUser(userData) {
  return request.post('/users', userData)
}

// 重置C端用户对应的密钥
export function resetAppUserKey(userId) {
  return request.post(`/users/key/reset/${userId}`)
}

// 查询所有C端用户用户
export function queryAllAppUsers() {
  return request.get('/users/list')
}

// 编辑C端用户
export function updateAppUser(userData) {
  return request.put('/users', userData)
}

// 通过ID查询C端用户
export function queryById(userId) {
  return request.get(`/users/${userId}`)
}

// 条件分页查询C端用户
export function queryAppUsers(phone, email, pageNum, pageSize) {
  return request.get('/users', {
    params: {
      phone,
      email,
      pageNum,
      pageSize
    }
  })
}

// 修改C端用户账号状态
export function updateAppUserStatus(userId, isOnline) {
  console.log('updateAppUserStatus', userId, isOnline)
  return request.put(`/users/status/${userId}`, {
    isOnline
  })
}

// 为指定用户分配设备列表
export function assignDevicesToUser(userId, deviceIds) {
  return request.put(`/users/devices/assign/${userId}`, {
    deviceIds,
  })
}