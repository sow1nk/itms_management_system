import request from '@/api/request'

// 查询所有角色
export function queryAllRoles() {
  return request.get('/roles/list')
}

// 查询所有管理员用户
export function queryAllAdmins() {
  return request.get('/admins/list')
}

// 新增管理员
export function createAdmin(data) {
  return request.post('/admins', data)
}

// 修改管理员信息
export function updateAdmin(data) {
  return request.put('/admins', data)
}

// 删除管理员
export function deleteAdmin(adminId) {
  return request.delete(`/admins/${adminId}`)
}

// 修改管理员账号状态
export function updateAdminStatus(adminId, status) {
  return request.put(`/admins/status/${adminId}`, {
    status,
  })
}

// 重置管理员密码
export function resetAdminPassword(adminId) {
  return request.put(`/admins/reset_password/${adminId}`)
}
