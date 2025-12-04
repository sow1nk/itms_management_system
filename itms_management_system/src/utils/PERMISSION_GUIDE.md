# 细粒度权限系统使用指南

## 概述

本系统实现了细粒度的权限控制，将原来的模块级权限（如 `user:manage`）细化为操作级权限（如 `user:manage:create`、`user:manage:update` 等）。

## 权限命名规范

权限采用**三段式命名**：`模块:功能:操作`

示例：
- `user:manage:create` - C端用户管理的创建权限
- `device:manage:update` - 设备管理的编辑权限
- `logs:manage:view` - 日志管理的查看权限

## 权限定义

### 1. C端用户管理 (user:manage)
- `user:manage:view` - 查看用户
- `user:manage:create` - 创建用户
- `user:manage:update` - 编辑用户
- `user:manage:delete` - 删除用户
- `user:manage:status` - 修改用户状态（冻结/解冻）
- `user:manage:assign_devices` - 分配设备
- `user:manage:assign_permissions` - 分配权限
- `user:manage:reset_key` - 重置密钥
- `user:manage:kick` - 强制下线

### 2. 设备管理 (device:manage)
- `device:manage:view` - 查看设备
- `device:manage:create` - 添加设备
- `device:manage:update` - 编辑设备
- `device:manage:delete` - 删除设备
- `device:manage:control` - 控制设备

### 3. 审计日志 (logs:manage)
- `logs:manage:view` - 查看日志
- `logs:manage:export` - 导出日志
- `logs:manage:delete` - 删除日志

### 4. 系统管理 (system_admin:manage)
- `system_admin:manage:view` - 查看管理员
- `system_admin:manage:create` - 创建管理员
- `system_admin:manage:update` - 编辑管理员
- `system_admin:manage:delete` - 删除管理员
- `system_admin:manage:assign_permissions` - 分配权限

### 5. 数据仪表盘 (dashboard)
- `dashboard:view` - 查看仪表盘
- `dashboard:export` - 导出数据

## 权限兼容性

系统保持**向后兼容**：
- 如果用户拥有 `user:manage` 权限，则自动拥有所有 `user:manage:*` 的子权限
- 可以逐步迁移到细粒度权限，无需一次性修改所有权限配置

## 使用方式

### 方式一：使用 `usePermission` Composable（推荐）

```vue
<script setup>
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS } from '@/utils/permission'

const { can, is, isSuperAdmin } = usePermission()
</script>

<template>
  <!-- 基于权限控制按钮状态 -->
  <el-button
    type="primary"
    :disabled="!can(PERMISSIONS.USER.CREATE)"
    @click="handleCreate"
  >
    新建用户
  </el-button>

  <!-- 检查多个权限（满足任一即可） -->
  <el-button
    :disabled="!can([PERMISSIONS.USER.CREATE, PERMISSIONS.USER.UPDATE])"
  >
    操作
  </el-button>

  <!-- 检查多个权限（必须全部满足） -->
  <el-button
    :disabled="!can([PERMISSIONS.USER.CREATE, PERMISSIONS.USER.UPDATE], 'every')"
  >
    批量操作
  </el-button>

  <!-- 基于角色条件渲染 -->
  <el-button v-if="is('super_admin')">
    管理员操作
  </el-button>
</template>
```

### 方式二：使用自定义指令

在 `main.js` 中注册指令：

```javascript
import permissionDirective from '@/directives/permission'

app.use(permissionDirective)
```

在组件中使用：

```vue
<template>
  <!-- 单个权限：不满足时禁用按钮 -->
  <el-button v-permission="PERMISSIONS.USER.CREATE">
    新建用户
  </el-button>

  <!-- 多个权限（满足任一即可） -->
  <el-button v-permission="[PERMISSIONS.USER.CREATE, PERMISSIONS.USER.UPDATE]">
    操作
  </el-button>

  <!-- 多个权限（必须全部满足） -->
  <el-button v-permission:every="[PERMISSIONS.USER.CREATE, PERMISSIONS.USER.UPDATE]">
    批量操作
  </el-button>

  <!-- 使用 hide 修饰符：不满足权限时隐藏元素 -->
  <el-button v-permission.hide="PERMISSIONS.USER.DELETE">
    删除
  </el-button>
</template>
```

### 方式三：直接使用工具函数

```javascript
import { hasPermission, hasRole } from '@/utils/permission'
import { useUserStore } from '@/store/modules/user'

const userStore = useUserStore()

// 检查单个权限
if (hasPermission(userStore.permissions, 'user:manage:create')) {
  // 执行操作
}

// 检查多个权限（满足任一）
if (hasPermission(userStore.permissions, ['user:manage:create', 'user:manage:update'])) {
  // 执行操作
}

// 检查多个权限（全部满足）
if (hasPermission(userStore.permissions, ['user:manage:create', 'user:manage:update'], 'every')) {
  // 执行操作
}

// 检查角色
if (hasRole(userStore.roles, 'super_admin')) {
  // 执行操作
}
```

## API 参考

### usePermission() Composable

返回对象：
- `permissions` - 当前用户的权限数组（computed）
- `roles` - 当前用户的角色数组（computed）
- `isSuperAdmin` - 是否是超级管理员（computed）
- `can(requiredPermissions, mode)` - 检查权限
  - `requiredPermissions`: 字符串或数组
  - `mode`: `'some'`（默认）或 `'every'`
- `is(requiredRoles)` - 检查角色
- `check({ permissions, roles })` - 综合检查权限或角色

### hasPermission() 函数

```javascript
hasPermission(userPermissions, requiredPermissions, mode = 'some')
```

参数：
- `userPermissions`: 用户权限数组
- `requiredPermissions`: 需要检查的权限（字符串或数组）
- `mode`: `'some'`（满足任一）或 `'every'`（全部满足）

返回：`boolean`

### hasRole() 函数

```javascript
hasRole(userRoles, requiredRoles)
```

参数：
- `userRoles`: 用户角色数组
- `requiredRoles`: 需要检查的角色（字符串或数组）

返回：`boolean`

## 后端接口要求

### 登录接口返回格式

```json
{
  "token": "xxx",
  "user": {
    "id": "1",
    "username": "admin",
    "permissions": [
      "user:manage:view",
      "user:manage:create",
      "user:manage:update",
      "device:manage:view",
      "device:manage:create"
    ],
    "roles": ["admin"]
  }
}
```

### 获取用户信息接口返回格式

```json
{
  "id": "1",
  "username": "admin",
  "permissions": [
    "user:manage:view",
    "user:manage:create",
    "device:manage"
  ],
  "roles": ["admin"]
}
```

注意：
- `permissions` 数组可以包含粗粒度权限（如 `device:manage`）和细粒度权限（如 `user:manage:create`）
- 拥有 `device:manage` 权限会自动拥有所有 `device:manage:*` 的子权限

## 最佳实践

1. **统一使用权限常量**
   ```javascript
   import { PERMISSIONS } from '@/utils/permission'

   // 好的做法
   can(PERMISSIONS.USER.CREATE)

   // 避免硬编码
   can('user:manage:create')
   ```

2. **在组件中使用 composable**
   ```javascript
   // 推荐：使用 composable
   const { can } = usePermission()
   const disabled = computed(() => !can(PERMISSIONS.USER.CREATE))

   // 不推荐：直接访问 store
   const userStore = useUserStore()
   const disabled = computed(() => !userStore.permissions.includes('user:manage:create'))
   ```

3. **超级管理员自动拥有所有权限**
   - 系统会自动识别 `super_admin` 角色
   - 无需为超级管理员单独配置每个权限

4. **渐进式迁移**
   - 先在新页面使用细粒度权限
   - 旧页面保持使用模块级权限
   - 系统会自动处理兼容性

## 示例：完整的页面权限控制

```vue
<script setup>
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS } from '@/utils/permission'

const { can, isSuperAdmin } = usePermission()

const handleCreate = () => {
  if (!can(PERMISSIONS.USER.CREATE)) {
    ElMessage.warning('您没有创建权限')
    return
  }
  // 执行创建操作
}
</script>

<template>
  <el-card>
    <div class="header">
      <h3>用户列表</h3>
      <el-button
        type="primary"
        :disabled="!can(PERMISSIONS.USER.CREATE)"
        @click="handleCreate"
      >
        新建用户
      </el-button>
    </div>

    <el-table :data="users">
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button
            :disabled="!can(PERMISSIONS.USER.UPDATE)"
            @click="handleEdit(row)"
          >
            编辑
          </el-button>
          <el-button
            v-if="isSuperAdmin"
            :disabled="!can(PERMISSIONS.USER.DELETE)"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
```

## 常见问题

### Q: 如何给用户分配权限？
A: 在管理员管理页面，可以通过权限树为用户分配细粒度权限。系统会将选中的权限保存到后端。

### Q: 权限检查失败时会发生什么？
A: 按钮会被禁用（或隐藏），用户无法点击。如果在代码中手动检查，`can()` 会返回 `false`。

### Q: 超级管理员也需要配置权限吗？
A: 不需要。拥有 `super_admin` 角色的用户自动拥有所有权限。

### Q: 可以自定义权限吗？
A: 可以。在 `/src/utils/permission.js` 中的 `PERMISSIONS` 对象和 `PERMISSION_TREE` 数组中添加新的权限定义即可。

### Q: 如何在路由中使用细粒度权限？
A: 路由级别建议继续使用模块级权限（如 `user:manage`），细粒度权限主要用于页面内的按钮和操作控制。
