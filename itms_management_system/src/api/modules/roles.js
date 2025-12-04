import request from '@/api/request'

// 查询所有角色
export function queryAllRoles() {
  return request.get('/roles/list')
}

// 查询单个角色详情
export function queryRoleDetail(roleId) {
  return request.get(`/roles/${roleId}`)
}

// 查询角色的权限列表
export function queryRolePermissions(roleId) {
  return request.get(`/roles/${roleId}/permissions`)
}

// 创建角色
export function createRole(data) {
  return request.post('/roles', data)
}

// 更新角色信息
export function updateRole(data) {
  return request.put('/roles', data)
}

// 删除角色
export function deleteRole(roleId) {
  return request.delete(`/roles/${roleId}`)
}

// 更新角色权限
export function updateRolePermissions(roleId, permissions) {
  return request.put(`/roles/${roleId}/permissions`, {
    permissions,
  })
}
