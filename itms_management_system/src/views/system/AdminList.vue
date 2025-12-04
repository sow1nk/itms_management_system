<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { queryAllAdmins, queryAdminPermissions, updateAdminPermissions, createAdmin, updateAdmin, deleteAdmin, updateAdminStatus } from '@/api/modules/admins'
import { useUserStore } from '@/store/modules/user'
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS, PERMISSION_TREE } from '@/utils/permission'

const loading = ref(false)
const admins = ref([])
const userStore = useUserStore()

// 使用权限 composable
const { can } = usePermission()

// 获取当前登录用户信息
const currentUser = computed(() => userStore.name)
const currentUserRoles = computed(() => userStore.roles || [])

// 新增管理员相关
const createDialogVisible = ref(false)
const createFormRef = ref()
const createForm = ref({
  username: '',
  password: '',
  phone: '',
  email: '',
})
const createFormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' },
  ],
}
const createLoading = ref(false)

// 编辑管理员相关
const editDialogVisible = ref(false)
const editFormRef = ref()
const editForm = ref({
  user_id: null,
  username: '',
  phone: '',
  email: '',
})
const editFormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' },
  ],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' },
  ],
}
const editLoading = ref(false)

// 权限分配相关
const permissionDialogVisible = ref(false)
const permissionLoading = ref(false)
const currentPermissionAdmin = ref(null)
const permissionTreeRef = ref()
const checkedPermissions = ref([])

const normalizeStatus = (status) => {
  if (typeof status === 'boolean') {
    return status ? 'normal' : 'disabled'
  }

  if (typeof status === 'number') {
    return status === 0 ? 'disabled' : 'normal'
  }

  if (typeof status === 'string') {
    const normalized = status.toLowerCase()

    if (['disabled', 'inactive', 'forbidden', 'frozen', '0', 'off'].includes(normalized)) {
      return 'disabled'
    }

    if (['normal', 'enabled', 'active', '1', 'on'].includes(normalized)) {
      return 'normal'
    }
  }

  return 'normal'
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await queryAllAdmins()
    console.log('管理员列表数据:', data)

    // 从返回的数据中提取 admins 数组，并转换数据格式
    if (data && data.admins) {
      admins.value = data.admins.map(admin => {
        const normalizedRole = admin.roles && admin.roles.length > 0
          ? admin.roles[0].replace(/_/g, '-') // super_admin -> super-admin
          : 'operator'

        return {
          ...admin,
          role: normalizedRole,
          status: normalizeStatus(admin.status),
        }
      })
    }

    console.log('转换后的管理员数据:', admins.value)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

// 检查是否为超级管理员
const isSuperAdmin = (row) => {
  return row.role === 'super-admin' || row.role === '超级管理员'
}

// 检查是否为当前用户
const isCurrentUser = (row) => {
  return row.username === currentUser.value || row.account === currentUser.value
}

// 检查是否可以操作该用户（用于删除和禁用）
const canModifyUser = (row) => {
  // 不能操作超级管理员
  if (isSuperAdmin(row)) return false
  // 不能操作自己
  if (isCurrentUser(row)) return false
  return true
}

// 处理状态切换
const handleStatusChange = async (value, row) => {
  // 双重保护：即使 switch 没被禁用，也要检查权限
  if (!canModifyUser(row)) {
    // 恢复原状态
    row.status = row.status === 'normal' ? 'disabled' : 'normal'
    ElMessage.warning('无法修改该账号状态')
    return
  }

  const action = value === 'disabled' ? '禁用' : '启用'
  ElMessageBox.confirm(`确认${action}该管理员吗？`, '操作确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        // 调用接口更新状态
        // status: true 表示启用(normal), false 表示禁用(disabled)
        const status = value === 'normal'

        console.log('更新状态请求:', {
          user_id: row.user_id,
          status,
          value,
        })

        await updateAdminStatus(row.user_id, status)

        row.status = value
        ElMessage.success(`${action}管理员成功`)
      } catch (error) {
        console.error('修改管理员状态失败:', error)
        console.error('错误详情:', error.response?.data)
        ElMessage.error(`${action}管理员失败，请稍后重试`)
        // 失败时恢复原状态
        row.status = row.status === 'normal' ? 'disabled' : 'normal'
      }
    })
    .catch(() => {
      // 用户取消，恢复原状态
      row.status = row.status === 'normal' ? 'disabled' : 'normal'
    })
}

// 处理删除
const handleDelete = async (row) => {
  // 安全检查
  if (!canModifyUser(row)) {
    ElMessage.error('无法删除该账号')
    return
  }

  ElMessageBox.confirm(`确认删除账号 ${row.username} 吗？此操作不可恢复！`, '危险操作', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'error',
  })
    .then(async () => {
      try {
        // 调用删除接口
        await deleteAdmin(row.user_id)
        ElMessage.success('删除管理员成功')
        // 刷新列表
        await loadData()
      } catch (error) {
        console.error('删除管理员失败:', error)
        ElMessage.error('删除管理员失败，请稍后重试')
      }
    })
    .catch(() => {})
}

// 重置密码
const handleResetPassword = (row) => {
  ElMessageBox.confirm(
    `确定要重置管理员 ${row.username} 的密码吗？重置后将发送新密码到其注册邮箱。`,
    '重置密码',
    {
      confirmButtonText: '确定重置',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(() => {
      // 模拟重置密码
      ElMessage.success('密码已重置，新密码已发送至管理员邮箱 (mock)')
    })
    .catch(() => {})
}

// 打开编辑管理员对话框
const handleEdit = (row) => {
  editDialogVisible.value = true
  // 填充表单数据
  editForm.value = {
    user_id: row.user_id,
    username: row.username,
    phone: row.phone || '',
    email: row.email || '',
  }
  // 清除表单验证
  nextTick(() => {
    editFormRef.value?.clearValidate()
  })
}

// 提交编辑管理员
const handleEditSubmit = async () => {
  // 表单验证
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return

  editLoading.value = true
  try {
    // 调用接口更新管理员信息
    await updateAdmin({
      user_id: editForm.value.user_id,
      username: editForm.value.username,
      phone: editForm.value.phone || null,
      email: editForm.value.email || null,
    })

    ElMessage.success('管理员信息更新成功')
    editDialogVisible.value = false

    // 刷新列表
    await loadData()
  } catch (error) {
    console.error('更新管理员失败:', error)
    ElMessage.error('更新管理员失败，请稍后重试')
  } finally {
    editLoading.value = false
  }
}

// 打开新增管理员对话框
const handleCreate = () => {
  createDialogVisible.value = true
  // 重置表单
  createForm.value = {
    username: '',
    password: '',
    phone: '',
    email: '',
  }
  // 清除表单验证
  nextTick(() => {
    createFormRef.value?.clearValidate()
  })
}

// 提交新增管理员
const handleCreateSubmit = async () => {
  // 表单验证
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  createLoading.value = true
  try {
    // 生成当前时间 (格式: YYYY-MM-DD HH:mm:ss)
    const now = new Date()
    const create_time = now.getFullYear() + '-' +
      String(now.getMonth() + 1).padStart(2, '0') + '-' +
      String(now.getDate()).padStart(2, '0') + ' ' +
      String(now.getHours()).padStart(2, '0') + ':' +
      String(now.getMinutes()).padStart(2, '0') + ':' +
      String(now.getSeconds()).padStart(2, '0')

    // 调用接口创建管理员
    await createAdmin({
      username: createForm.value.username,
      password: createForm.value.password,
      phone: createForm.value.phone,
      email: createForm.value.email,
      create_time,
    })

    ElMessage.success('管理员创建成功')
    createDialogVisible.value = false

    // 刷新列表
    await loadData()
  } catch (error) {
    console.error('创建管理员失败:', error)
    ElMessage.error('创建管理员失败，请稍后重试')
  } finally {
    createLoading.value = false
  }
}

// 格式化角色显示
const formatRole = (role) => {
  const roleMap = {
    'super-admin': '超级管理员',
    'admin': '管理员',
    'operator': '操作员',
  }
  return roleMap[role] || role
}

// 获取角色标签类型
const getRoleTagType = (role) => {
  const typeMap = {
    'super-admin': 'danger',
    'admin': 'warning',
    'operator': '',
  }
  return typeMap[role] || 'info'
}

// 处理分配权限
const handleAssignPermissions = async (row) => {
  currentPermissionAdmin.value = row
  permissionDialogVisible.value = true
  permissionLoading.value = true

  try {
    // 判断是否为超级管理员
    if (isSuperAdmin(row)) {
      // 超级管理员：自动拥有所有权限
      const allPermissionKeys = []
      PERMISSION_TREE.forEach((module) => {
        if (module.children) {
          module.children.forEach((child) => {
            allPermissionKeys.push(child.id)
          })
        } else {
          allPermissionKeys.push(module.id)
        }
      })
      checkedPermissions.value = allPermissionKeys
      console.log('超级管理员，拥有全部权限:', checkedPermissions.value)
    } else {
      // 普通管理员：调用接口获取权限
      const response = await queryAdminPermissions(row.user_id)
      console.log('管理员当前权限:', response)

      // 从返回的数据中提取 perm_key
      if (response && response.permissions && Array.isArray(response.permissions)) {
        checkedPermissions.value = response.permissions.map(item => item.perm_key).filter(Boolean)
        console.log('转换后的权限列表:', checkedPermissions.value)
      } else {
        checkedPermissions.value = []
      }
    }

    // 等待 DOM 更新后设置选中的权限
    await nextTick()
    permissionTreeRef.value?.setCheckedKeys(checkedPermissions.value)
  } catch (error) {
    console.error(error)
    ElMessage.error('获取管理员权限失败')
  } finally {
    permissionLoading.value = false
  }
}

// 提交权限分配
const handlePermissionSubmit = async () => {
  if (!currentPermissionAdmin.value) return

  permissionLoading.value = true
  try {
    // 获取选中的权限（包括半选中的父节点）
    const checkedKeys = permissionTreeRef.value.getCheckedKeys()
    const halfCheckedKeys = permissionTreeRef.value.getHalfCheckedKeys()
    const allPermissions = [...checkedKeys, ...halfCheckedKeys]

    // 过滤掉分组节点（带 _group 后缀的），只保留真实权限（三段式格式）
    const validPermissions = allPermissions.filter(perm => {
      // 真实权限格式：module:function:action（包含两个冒号）
      return perm && perm.includes(':') && !perm.endsWith('_group')
    })

    console.log('保存管理员权限:', {
      adminId: currentPermissionAdmin.value.user_id,
      permissions: validPermissions,
    })

    // 调用接口保存权限
    await updateAdminPermissions(currentPermissionAdmin.value.user_id, validPermissions)
    ElMessage.success('权限分配成功')
    permissionDialogVisible.value = false
  } catch (error) {
    console.error(error)
    ElMessage.error('权限分配失败，请稍后重试')
  } finally {
    permissionLoading.value = false
  }
}
</script>

<template>
  <el-card shadow="never">
    <div class="module-header">
      <div>
        <h3>管理员管理</h3>
        <p>维护后台账号、角色与启用状态。</p>
      </div>
      <el-button type="primary" plain @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新增管理员
      </el-button>
    </div>

    <el-table :data="admins" v-loading="loading" border stripe>
      <!-- 账号列 - 用于登录的账号名 -->
      <el-table-column label="用户 ID" prop="user_id" min-width="140"/>

      <!-- 用户名列 -->
      <el-table-column label="用户名" prop="username" min-width="140" />

      <!-- 角色列 -->
      <el-table-column label="角色" prop="role" min-width="140">
        <template #default="{ row }">
          <el-tag :type="getRoleTagType(row.role)" effect="plain">
            {{ formatRole(row.role) }}
          </el-tag>
          <el-tooltip v-if="isSuperAdmin(row)" content="系统最高权限，不可删除或禁用" placement="top">
            <el-icon style="margin-left: 4px; color: #e6a23c;">
              <Warning />
            </el-icon>
          </el-tooltip>
        </template>
      </el-table-column>

      <!-- 创建时间 -->
      <el-table-column label="创建时间" prop="create_time" min-width="160" />

      <!-- 手机号 -->
      <el-table-column label="手机号" prop="phone" min-width="140">
        <template #default="{ row }">
          <span>{{ row.phone || '-' }}</span>
        </template>
      </el-table-column>

      <!-- 邮箱 -->
      <el-table-column label="邮箱" prop="email" min-width="180">
        <template #default="{ row }">
          <span>{{ row.email || '-' }}</span>
        </template>
      </el-table-column>

      <!-- 状态列 - 使用 Switch -->
      <el-table-column label="状态" min-width="140">
        <template #default="{ row }">
          <div class="status-cell">
            <el-switch
              v-model="row.status"
              active-value="normal"
              inactive-value="disabled"
              active-text="启用"
              inactive-text="禁用"
              :disabled="!canModifyUser(row)"
              @change="(value) => handleStatusChange(value, row)"
            />
            <el-tooltip v-if="!canModifyUser(row)" placement="top">
              <template #content>
                <span v-if="isSuperAdmin(row)">超级管理员不可禁用</span>
                <span v-else-if="isCurrentUser(row)">不能禁用自己的账号</span>
              </template>
              <el-icon style="margin-left: 4px; color: #909399;">
                <InfoFilled />
              </el-icon>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>

      <!-- 操作列 -->
      <el-table-column label="操作" min-width="340" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <!-- 编辑按钮 -->
            <el-button
              type="primary"
              link
              size="small"
              :disabled="!can(PERMISSIONS.SYSTEM_ADMIN.UPDATE)"
              @click="handleEdit(row)"
            >
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>

            <!-- 分配权限按钮 -->
            <el-button
              type="warning"
              link
              size="small"
              :disabled="!can(PERMISSIONS.SYSTEM_ADMIN.ASSIGN_PERMISSIONS)"
              @click="handleAssignPermissions(row)"
            >
              <el-icon><Key /></el-icon>
              分配权限
            </el-button>

            <!-- 重置密码按钮 -->
            <el-button
              type="warning"
              link
              size="small"
              @click="handleResetPassword(row)"
            >
              <el-icon><Refresh /></el-icon>
              重置密码
            </el-button>

            <!-- 删除按钮 - 根据权限显示 -->
            <el-button
              v-if="canModifyUser(row)"
              type="danger"
              link
              size="small"
              :disabled="!can(PERMISSIONS.SYSTEM_ADMIN.DELETE)"
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>

            <!-- 不可删除时的占位提示 -->
            <el-tooltip v-else placement="top">
              <template #content>
                <span v-if="isSuperAdmin(row)">超级管理员账号不可删除</span>
                <span v-else-if="isCurrentUser(row)">不能删除自己的账号</span>
              </template>
              <el-button type="info" link size="small" disabled>
                <el-icon><Lock /></el-icon>
                不可删除
              </el-button>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 权限分配对话框 -->
  <el-dialog
    v-model="permissionDialogVisible"
    title="分配权限"
    width="600px"
    destroy-on-close
  >
    <div v-loading="permissionLoading" style="min-height: 200px">
      <el-form label-width="100px">
        <el-form-item label="用户 ID">
          <span>{{ currentPermissionAdmin?.user_id }}</span>
        </el-form-item>
        <el-form-item label="用户名">
          <span>{{ currentPermissionAdmin?.username }}</span>
        </el-form-item>
        <el-form-item label="角色">
          <el-tag :type="getRoleTagType(currentPermissionAdmin?.role)">
            {{ formatRole(currentPermissionAdmin?.role) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="功能权限">
          <div class="permission-tree-container">
            <el-tree
              ref="permissionTreeRef"
              :data="PERMISSION_TREE"
              show-checkbox
              node-key="id"
              :props="{ children: 'children', label: 'label' }"
              default-expand-all
              :check-strictly="false"
            >
              <template #default="{ node, data }">
                <span class="custom-tree-node">
                  <span :class="{ 'tree-parent-node': data.children && data.children.length > 0 }">
                    {{ node.label }}
                  </span>
                </span>
              </template>
            </el-tree>
          </div>
        </el-form-item>
        <el-alert
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 12px"
        >
          <template #title>
            <div style="font-size: 13px">
              <div>· 勾选父节点将自动勾选所有子权限</div>
              <div>· 超级管理员默认拥有所有权限</div>
            </div>
          </template>
        </el-alert>
      </el-form>
    </div>
    <template #footer>
      <el-button @click="permissionDialogVisible = false">取 消</el-button>
      <el-button
        type="primary"
        :loading="permissionLoading"
        @click="handlePermissionSubmit"
      >
        保 存
      </el-button>
    </template>
  </el-dialog>

  <!-- 新增管理员对话框 -->
  <el-dialog
    v-model="createDialogVisible"
    title="新增管理员"
    width="500px"
    destroy-on-close
  >
    <el-form
      ref="createFormRef"
      :model="createForm"
      :rules="createFormRules"
      label-width="100px"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="createForm.username"
          placeholder="请输入用户名（字母、数字、下划线）"
          maxlength="20"
          show-word-limit
          clearable
        />
      </el-form-item>
      <el-form-item label="密码" prop="password">
        <el-input
          v-model="createForm.password"
          type="password"
          placeholder="请输入密码（6-20位）"
          maxlength="20"
          show-word-limit
          show-password
          clearable
        />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input
          v-model="createForm.phone"
          placeholder="请输入手机号"
          maxlength="11"
          clearable
        />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input
          v-model="createForm.email"
          placeholder="请输入邮箱"
          maxlength="50"
          clearable
        />
      </el-form-item>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 12px"
      >
        <template #title>
          <div style="font-size: 13px">
            <div>· 用户名：3-20个字符，仅支持字母、数字、下划线</div>
            <div>· 密码：6-20个字符</div>
            <div>· 新建管理员默认为普通操作员角色</div>
          </div>
        </template>
      </el-alert>
    </el-form>
    <template #footer>
      <el-button @click="createDialogVisible = false">取 消</el-button>
      <el-button
        type="primary"
        :loading="createLoading"
        @click="handleCreateSubmit"
      >
        创 建
      </el-button>
    </template>
  </el-dialog>

  <!-- 编辑管理员对话框 -->
  <el-dialog
    v-model="editDialogVisible"
    title="编辑管理员"
    width="500px"
    destroy-on-close
  >
    <el-form
      ref="editFormRef"
      :model="editForm"
      :rules="editFormRules"
      label-width="100px"
    >
      <el-form-item label="用户 ID">
        <span style="color: #606266">{{ editForm.user_id }}</span>
      </el-form-item>
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="editForm.username"
          placeholder="请输入用户名（字母、数字、下划线）"
          maxlength="20"
          show-word-limit
          clearable
        />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input
          v-model="editForm.phone"
          placeholder="请输入手机号（选填）"
          maxlength="11"
          clearable
        />
      </el-form-item>
      <el-form-item label="邮箱" prop="email">
        <el-input
          v-model="editForm.email"
          placeholder="请输入邮箱（选填）"
          maxlength="50"
          clearable
        />
      </el-form-item>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        style="margin-top: 12px"
      >
        <template #title>
          <div style="font-size: 13px">
            <div>· 用户名：3-20个字符，仅支持字母、数字、下划线</div>
            <div>· 手机号和邮箱为选填项，可留空</div>
          </div>
        </template>
      </el-alert>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取 消</el-button>
      <el-button
        type="primary"
        :loading="editLoading"
        @click="handleEditSubmit"
      >
        保 存
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.module-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.module-header h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.module-header p {
  margin: 0;
  color: #909399;
  font-size: 14px;
}

.account-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* Switch 样式优化 */
:deep(.el-switch.is-disabled) {
  opacity: 0.6;
}

:deep(.el-switch__label) {
  font-size: 12px;
}

/* 表格样式优化 */
:deep(.el-table th.el-table__cell) {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

:deep(.el-table .el-table__row) {
  transition: background-color 0.25s ease;
}

:deep(.el-table .el-table__row:hover) {
  background-color: #f5f7fa;
}

/* 权限树样式 */
.permission-tree-container {
  width: 100%;
  max-height: 400px;
  overflow-y: auto;
  padding: 12px;
  background-color: #f9fbff;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.permission-tree-container :deep(.el-tree) {
  background-color: transparent;
}

.permission-tree-container :deep(.el-tree-node__content) {
  height: 36px;
  margin: 2px 0;
  border-radius: 4px;
}

.permission-tree-container :deep(.el-tree-node__content:hover) {
  background-color: #f0f2f5;
}

.custom-tree-node {
  flex: 1;
  display: flex;
  align-items: center;
  font-size: 14px;
}

.tree-parent-node {
  font-weight: 600;
  color: #303133;
}
</style>
