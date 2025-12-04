/**
 * 权限工具函数
 * 用于细粒度的权限控制
 */

/**
 * 权限定义：采用三段式命名
 * 格式：模块:功能:操作
 * 例如：user:manage:create
 */

// 权限常量定义
export const PERMISSIONS = {
  // C端用户管理权限
  USER: {
    VIEW: 'user:manage:view',           // 查看用户
    CREATE: 'user:manage:create',       // 创建用户
    UPDATE: 'user:manage:update',       // 编辑用户
    DELETE: 'user:manage:delete',       // 删除用户
    STATUS: 'user:manage:status',       // 修改用户状态（冻结/解冻）
    ASSIGN_DEVICES: 'user:manage:assign_devices',     // 分配设备
    ASSIGN_PERMISSIONS: 'user:manage:assign_permissions', // 分配权限
    RESET_KEY: 'user:manage:reset_key', // 重置密钥
    KICK: 'user:manage:kick',           // 强制下线
  },
  // 设备管理权限
  DEVICE: {
    VIEW: 'device:manage:view',         // 查看设备
    CREATE: 'device:manage:create',     // 添加设备
    UPDATE: 'device:manage:update',     // 编辑设备
    DELETE: 'device:manage:delete',     // 删除设备
    CONTROL: 'device:manage:control',   // 控制设备
  },
  // 日志管理权限
  LOGS: {
    VIEW: 'logs:manage:view',           // 查看日志
    EXPORT: 'logs:manage:export',       // 导出日志
    DELETE: 'logs:manage:delete',       // 删除日志
  },
  // 系统管理员管理权限
  SYSTEM_ADMIN: {
    VIEW: 'system_admin:manage:view',           // 查看管理员
    CREATE: 'system_admin:manage:create',       // 创建管理员
    UPDATE: 'system_admin:manage:update',       // 编辑管理员
    DELETE: 'system_admin:manage:delete',       // 删除管理员
    // ASSIGN_PERMISSIONS: 'system_admin:manage:assign_permissions', // 分配权限
    RESET_PASSWORD: 'system_admin:manage:reset_password', // 重置密码
  },
  // 系统角色管理权限
  SYSTEM_ROLE: {
    VIEW: 'system_role:manage:view',           // 查看角色
    CREATE: 'system_role:manage:create',       // 创建角色
    UPDATE: 'system_role:manage:update',       // 编辑角色
    DELETE: 'system_role:manage:delete',       // 删除角色
    ASSIGN_PERMISSIONS: 'system_role:manage:assign_permissions', // 分配权限
  },
  // 仪表盘权限
  DASHBOARD: {
    VIEW: 'dashboard:view',             // 查看仪表盘
    EXPORT: 'dashboard:export',         // 导出数据
  },
}

/**
 * 权限树结构 - 用于权限分配界面
 * 注意：父节点仅用于分组展示，不是实际权限
 */
export const PERMISSION_TREE = [
  {
    id: 'user_manage_group',
    label: 'C端用户管理',
    children: [
      { id: PERMISSIONS.USER.VIEW, label: '查看用户' },
      { id: PERMISSIONS.USER.CREATE, label: '创建用户' },
      { id: PERMISSIONS.USER.UPDATE, label: '编辑用户' },
      { id: PERMISSIONS.USER.DELETE, label: '删除用户' },
      { id: PERMISSIONS.USER.STATUS, label: '修改用户状态' },
      { id: PERMISSIONS.USER.ASSIGN_DEVICES, label: '分配设备' },
      { id: PERMISSIONS.USER.ASSIGN_PERMISSIONS, label: '分配权限' },
      { id: PERMISSIONS.USER.RESET_KEY, label: '重置密钥' },
      { id: PERMISSIONS.USER.KICK, label: '强制下线' },
    ],
  },
  {
    id: 'device_manage_group',
    label: '设备管理',
    children: [
      { id: PERMISSIONS.DEVICE.VIEW, label: '查看设备' },
      { id: PERMISSIONS.DEVICE.CREATE, label: '添加设备' },
      { id: PERMISSIONS.DEVICE.UPDATE, label: '编辑设备' },
      { id: PERMISSIONS.DEVICE.DELETE, label: '删除设备' },
      { id: PERMISSIONS.DEVICE.CONTROL, label: '控制设备' },
    ],
  },
  {
    id: 'logs_manage_group',
    label: '审计日志',
    children: [
      { id: PERMISSIONS.LOGS.VIEW, label: '查看日志' },
      { id: PERMISSIONS.LOGS.EXPORT, label: '导出日志' },
      { id: PERMISSIONS.LOGS.DELETE, label: '删除日志' },
    ],
  },
  {
    id: 'system_admin_manage_group',
    label: '系统管理',
    children: [
      { id: PERMISSIONS.SYSTEM_ADMIN.VIEW, label: '查看管理员' },
      { id: PERMISSIONS.SYSTEM_ADMIN.CREATE, label: '创建管理员' },
      { id: PERMISSIONS.SYSTEM_ADMIN.UPDATE, label: '编辑管理员' },
      { id: PERMISSIONS.SYSTEM_ADMIN.DELETE, label: '删除管理员' },
      { id: PERMISSIONS.SYSTEM_ADMIN.ASSIGN_PERMISSIONS, label: '分配权限' },
    ],
  },
  {
    id: 'system_role_manage_group',
    label: '角色管理',
    children: [
      { id: PERMISSIONS.SYSTEM_ROLE.VIEW, label: '查看角色' },
      { id: PERMISSIONS.SYSTEM_ROLE.CREATE, label: '创建角色' },
      { id: PERMISSIONS.SYSTEM_ROLE.UPDATE, label: '编辑角色' },
      { id: PERMISSIONS.SYSTEM_ROLE.DELETE, label: '删除角色' },
      { id: PERMISSIONS.SYSTEM_ROLE.ASSIGN_PERMISSIONS, label: '分配角色权限' },
    ],
  },
  {
    id: 'dashboard_group',
    label: '数据仪表盘',
    children: [
      { id: PERMISSIONS.DASHBOARD.VIEW, label: '查看仪表盘' },
      { id: PERMISSIONS.DASHBOARD.EXPORT, label: '导出数据' },
    ],
  },
]

/**
 * 检查是否拥有指定权限（精确匹配，无继承）
 * @param {Array} userPermissions - 用户的权限列表
 * @param {string|Array} requiredPermissions - 需要检查的权限（单个字符串或数组）
 * @param {string} mode - 检查模式：'some'（满足任一） 或 'every'（全部满足）
 * @returns {boolean}
 */
export function hasPermission(userPermissions = [], requiredPermissions, mode = 'some') {
  if (!userPermissions || !Array.isArray(userPermissions)) {
    return false
  }

  if (!requiredPermissions) {
    return true
  }

  // 如果是单个权限字符串，转为数组处理
  const permissions = Array.isArray(requiredPermissions) ? requiredPermissions : [requiredPermissions]

  // 精确匹配（不再支持继承）
  const hasMatch = (perm) => {
    return userPermissions.includes(perm)
  }

  if (mode === 'every') {
    return permissions.every(hasMatch)
  }
  return permissions.some(hasMatch)
}

/**
 * 检查是否拥有指定角色
 * @param {Array} userRoles - 用户的角色列表
 * @param {string|Array} requiredRoles - 需要检查的角色
 * @returns {boolean}
 */
export function hasRole(userRoles = [], requiredRoles) {
  if (!userRoles || !Array.isArray(userRoles)) {
    return false
  }

  if (!requiredRoles) {
    return true
  }

  const roles = Array.isArray(requiredRoles) ? requiredRoles : [requiredRoles]
  return roles.some((role) => userRoles.includes(role))
}

/**
 * 检查是否拥有权限或角色（满足任一即可）
 * @param {Object} user - 用户对象，包含 permissions 和 roles
 * @param {Object} requirements - 需求对象 { permissions, roles }
 * @returns {boolean}
 */
export function checkAccess(user, requirements = {}) {
  const { permissions: reqPermissions, roles: reqRoles } = requirements

  // 如果既没有权限要求也没有角色要求，则允许访问
  if (!reqPermissions && !reqRoles) {
    return true
  }

  // 检查角色
  if (reqRoles && hasRole(user.roles, reqRoles)) {
    return true
  }

  // 检查权限
  if (reqPermissions && hasPermission(user.permissions, reqPermissions)) {
    return true
  }

  return false
}

/**
 * 从权限列表中提取所有叶子节点权限（用于展示已选择的权限）
 * 注意：现在所有权限都是细粒度的，无需特殊处理
 * @param {Array} permissions - 权限列表
 * @returns {Array} 权限列表（原样返回）
 */
export function extractLeafPermissions(permissions = []) {
  // 现在所有权限都是细粒度的，直接返回
  return permissions.filter(perm => perm && perm.split(':').length === 3)
}
