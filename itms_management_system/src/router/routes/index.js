import MainLayout from '@/layouts/MainLayout.vue'

// 静态路由
export const constantRoutes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { hidden: true },
  },
  {
    path: '/',
    name: 'Root',
    component: MainLayout,
    redirect: '/dashboard',
    meta: { title: '仪表盘', icon: 'DataAnalysis' },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
        meta: { title: '数据总览', icon: 'DataBoard' },
      },
    ],
  },
  // 404 页面兜底（暂时使用面板页面）
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    redirect: '/dashboard',
    meta: { hidden: true },
  },
]

// 动态路由
export const asyncRoutes = [
  // C端用户模块
  {
    path: '/users',
    name: 'UserModule',
    component: MainLayout,
    redirect: '/users/list',
    meta: { title: 'C端用户', icon: 'UserFilled', permission: ['user:manage:view'] },
    children: [
      {
        path: 'list',
        name: 'UserList',
        component: () => import('@/views/users/AppUserList.vue'),
        meta: { title: '用户管理', permission: ['user:manage:view'] },
      },
    ],
  },
  // 设备管理模块
  {
    path: '/devices',
    name: 'DeviceModule',
    component: MainLayout,
    redirect: '/devices/list',
    meta: { title: '设备管理', icon: 'VideoCameraFilled', permission: ['device:manage:view'] },
    children: [
      {
        path: 'list',
        name: 'DeviceList',
        component: () => import('@/views/devices/DeviceList.vue'),
        meta: { title: '设备列表', permission: ['device:manage:view'] },
      },
    ],
  },
  // 日志
  {
    path: '/logs',
    name: 'LogsModule',
    component: MainLayout,
    redirect: '/logs/audit',
    meta: { title: '审计日志', icon: 'Document', permission: ['logs:manage:view'], roles: ['super_admin'] },
    children: [
      {
        path: 'audit',
        name: 'AuditLogs',
        component: () => import('@/views/logs/AuditLogs.vue'),
        meta: { title: '操作日志', permission: ['logs:manage:view'], roles: ['super_admin'] },
      },
    ],
  },
  // 管理员管理系统
  {
    path: '/system',
    name: 'SystemModule',
    component: MainLayout,
    redirect: '/system/admins',
    meta: { title: '系统管理', icon: 'Setting', permission: ['system_admin:manage:view'], roles: ['super_admin'] },
    children: [
      {
        path: 'admins',
        name: 'AdminList',
        component: () => import('@/views/system/AdminList.vue'),
        meta: { title: '管理员', permission: ['system_admin:manage:view'], roles: ['super_admin'] },
      },
      {
        path: 'roles',
        name: 'RoleList',
        component: () => import('@/views/system/RoleList.vue'),
        meta: { title: '角色管理', permission: ['system_role:manage:view'], roles: ['super_admin'] },
      },
    ],
  },
]
