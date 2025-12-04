# 数据库权限设计方案说明

## 📋 推荐方案：混合模式

### 为什么这样设计？

#### 1. **保留现有粗粒度权限作为"父权限"**
```
现有数据（保持不变）：
1    user:manage              ← 父权限（拥有所有用户管理权限）
2    device:manage            ← 父权限（拥有所有设备管理权限）
3    logs:manage              ← 父权限（拥有所有日志管理权限）
4    system_admin:manage      ← 父权限（拥有所有系统管理权限）
```

#### 2. **新增细粒度权限作为"子权限"**
```
新增数据：
5    user:manage:view         ← 子权限（只能查看用户）
6    user:manage:create       ← 子权限（只能创建用户）
7    user:manage:update       ← 子权限（只能编辑用户）
... 共约 27 条细粒度权限
```

## ✅ 这样设计的优势

### 1. **灵活的权限分配**

**场景A：高级管理员（需要全部权限）**
```sql
-- 只需分配 1 条父权限
INSERT INTO admin_permissions (admin_id, permission_id) VALUES (1, 1);  -- user:manage

-- 前端自动识别：该管理员拥有所有 user:manage:* 权限
-- ✅ user:manage:view
-- ✅ user:manage:create
-- ✅ user:manage:update
-- ✅ user:manage:delete
-- ... 等所有子权限
```

**场景B：普通管理员（只需部分权限）**
```sql
-- 只分配具体需要的权限
INSERT INTO admin_permissions (admin_id, permission_id)
VALUES
  (2, 5),  -- user:manage:view（只能查看）
  (2, 6);  -- user:manage:create（只能创建）

-- 该管理员只有这 2 个权限，不能编辑、删除等
```

### 2. **向后兼容**
```
✅ 现有用户的权限配置不需要修改
✅ 已经分配 user:manage 的用户自动拥有所有子权限
✅ 平滑升级，无需数据迁移
```

### 3. **权限管理更清晰**

在权限分配界面，可以展示为树形结构：

```
📁 C端用户管理 (user:manage)
  ├─ 查看用户 (user:manage:view)
  ├─ 创建用户 (user:manage:create)
  ├─ 编辑用户 (user:manage:update)
  ├─ 删除用户 (user:manage:delete)
  └─ ...

📁 设备管理 (device:manage)
  ├─ 查看设备 (device:manage:view)
  ├─ 添加设备 (device:manage:create)
  └─ ...
```

管理员可以：
- **勾选父节点** → 分配所有子权限（快速操作）
- **勾选子节点** → 分配具体权限（精细控制）

## 🔧 表结构优化建议

### 当前表结构
```sql
permission (
  id INT PRIMARY KEY,
  perm_key VARCHAR
)
```

### 建议优化后的表结构
```sql
permission (
  id INT PRIMARY KEY,
  perm_key VARCHAR(100) NOT NULL UNIQUE,   -- 权限标识
  parent_id INT DEFAULT NULL,              -- 父权限ID（可选）
  description VARCHAR(255),                -- 权限描述
  sort_order INT DEFAULT 0,                -- 排序
  INDEX idx_parent_id (parent_id)
)
```

**新增字段说明：**
- `parent_id`：指向父权限的ID，方便查询树形结构
- `description`：权限描述，方便管理员理解
- `sort_order`：排序字段，控制显示顺序

## 📊 最终数据结构示例

```
ID   perm_key                        parent_id  description
---  ------------------------------  ---------  -------------------------
1    user:manage                     NULL       C端用户管理（所有权限）
5    user:manage:view                1          查看C端用户列表
6    user:manage:create              1          创建C端用户
7    user:manage:update              1          编辑C端用户信息
8    user:manage:delete              1          删除C端用户
9    user:manage:status              1          修改用户状态
10   user:manage:assign_devices      1          为用户分配设备
11   user:manage:assign_permissions  1          为用户分配权限
12   user:manage:reset_key           1          重置用户密钥
13   user:manage:kick                1          强制用户下线

2    device:manage                   NULL       设备管理（所有权限）
14   device:manage:view              2          查看设备信息
15   device:manage:create            2          添加新设备
16   device:manage:update            2          编辑设备信息
17   device:manage:delete            2          删除设备
18   device:manage:control           2          控制设备

3    logs:manage                     NULL       审计日志（所有权限）
19   logs:manage:view                3          查看审计日志
20   logs:manage:export              3          导出日志数据
21   logs:manage:delete              3          删除日志记录

4    system_admin:manage             NULL       系统管理（所有权限）
22   system_admin:manage:view        4          查看管理员列表
23   system_admin:manage:create      4          创建管理员账号
24   system_admin:manage:update      4          编辑管理员信息
25   system_admin:manage:delete      4          删除管理员账号
26   system_admin:manage:assign...   4          为管理员分配权限

27   dashboard:view                  NULL       查看数据仪表盘
28   dashboard:export                NULL       导出仪表盘数据
```

**总计：**
- 4 个父权限（粗粒度）
- 24 个子权限（细粒度）
- 2 个独立权限（仪表盘）
- **共 30 条权限记录**

## 🎯 权限继承逻辑（前端已实现）

你的前端代码 `src/utils/permission.js` 中的 `hasPermission()` 函数已经实现了权限继承：

```javascript
const hasMatch = (perm) => {
  return userPermissions.some((userPerm) => {
    // 精确匹配
    if (userPerm === perm) return true

    // 模糊匹配：如果用户有 user:manage，则拥有 user:manage:* 的所有权限
    const parts = perm.split(':')
    if (parts.length > 2) {
      const parentPerm = parts.slice(0, 2).join(':')
      return userPerm === parentPerm
    }
    return false
  })
}
```

**示例：**
```javascript
用户权限：['user:manage']

检查 can('user:manage:view')
→ 拆分为 'user:manage'
→ 匹配成功 ✅

检查 can('user:manage:create')
→ 拆分为 'user:manage'
→ 匹配成功 ✅

检查 can('device:manage:view')
→ 拆分为 'device:manage'
→ 不匹配 ❌
```

## ⚙️ 后端实现建议

### 方案1：后端返回扁平化权限（推荐）

**登录接口返回：**
```json
{
  "token": "xxx",
  "user": {
    "id": 1,
    "username": "admin",
    "permissions": [
      "user:manage",           // 父权限
      "device:manage:view",    // 具体子权限
      "device:manage:create"
    ],
    "roles": ["admin"]
  }
}
```

**后端逻辑：**
```python
def get_user_permissions(user_id):
    # 查询用户被分配的权限
    assigned_perms = db.query("""
        SELECT p.perm_key
        FROM admin_permissions ap
        JOIN permission p ON ap.permission_id = p.id
        WHERE ap.admin_id = ?
    """, user_id)

    # 直接返回，前端会自动处理继承
    return [p['perm_key'] for p in assigned_perms]
```

✅ **优点：**简单直接，前端自动处理继承逻辑

### 方案2：后端展开所有有效权限

**后端逻辑：**
```python
def get_user_permissions(user_id):
    assigned_perms = get_assigned_permissions(user_id)
    expanded_perms = []

    for perm in assigned_perms:
        expanded_perms.append(perm)

        # 如果是父权限，展开所有子权限
        if not ':' in perm.split(':')[2:]:  # 只有两段，是父权限
            children = db.query("""
                SELECT perm_key FROM permission
                WHERE parent_id = (SELECT id FROM permission WHERE perm_key = ?)
            """, perm)
            expanded_perms.extend([c['perm_key'] for c in children])

    return list(set(expanded_perms))  # 去重
```

❌ **缺点：**后端逻辑复杂，数据量大

## 🚀 总结

### ✅ 这样设计是合理的

1. **保留现有数据** → 向后兼容
2. **新增细粒度权限** → 支持精细控制
3. **前端自动继承** → 实现简单
4. **灵活分配** → 适应不同场景

### 📝 执行步骤

1. **执行 SQL 脚本**：`database_permission_upgrade.sql`
2. **验证数据**：查询确认 30 条权限记录
3. **后端调整**：确保登录接口返回 `permissions` 数组
4. **测试**：分配不同权限，测试前端按钮状态

### ⚠️ 注意事项

- **不要删除**现有的 4 条父权限
- **parent_id 字段**可选但推荐添加
- **超级管理员**建议继续使用 `roles: ['super_admin']` 判断，自动拥有所有权限
