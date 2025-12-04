<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { queryAllAdmins, createAdmin, updateAdmin, deleteAdmin, updateAdminStatus, resetAdminPassword } from '@/api/modules/admins'
import { queryAllRoles } from '@/api/modules/roles'
import { useUserStore } from '@/store/modules/user'
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS } from '@/utils/permission'

const loading = ref(false)
const admins = ref([])
const roleOptions = ref([])
const roleOptionsLoading = ref(false)
const userStore = useUserStore()

// 使用权限 composable
const { can } = usePermission()

// 获取当前登录用户信息
const currentUser = computed(() => userStore.name)

// 新增管理员相关
const createDialogVisible = ref(false)
const createFormRef = ref()
const createForm = ref({
  username: '',
  password: '',
  phone: '',
  email: '',
  role_id: null,
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
  role_id: [
    { required: true, message: '请选择角色', trigger: 'change' },
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
  role_id: null,
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
  role_id: [
    { required: true, message: '请选择角色', trigger: 'change' },
  ],
}
const editLoading = ref(false)


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

const normalizeRoleList = (admin) => {
  // 优先使用 role_list（结构化的角色数据）
  if (Array.isArray(admin.role_list) && admin.role_list.length > 0) {
    return admin.role_list.map(role => ({
      role_id: role.role_id,
      role_key: role.role_key,
      role_name: role.role_name || role.role_key?.replace(/_/g, ' '),
    }))
  }

  // 从 roles 和 role_ids 数组构建角色列表
  if (Array.isArray(admin.roles) && admin.roles.length > 0) {
    return admin.roles.map((roleKey, index) => ({
      role_id: admin.role_ids?.[index] || null,
      role_key: roleKey,
      role_name: roleKey.replace(/_/g, ' '),
    }))
  }

  return []
}

const loadRoleOptions = async () => {
  roleOptionsLoading.value = true
  try {
    const data = await queryAllRoles()
    const options = (data?.roles || []).map(role => ({
      ...role,
      disabled: role.status !== 1,
      label: `${role.role_name} (${role.role_key})`,
    }))
    roleOptions.value = options
  } catch (error) {
    console.error('加载角色列表失败:', error)
    ElMessage.error('加载角色列表失败')
  } finally {
    roleOptionsLoading.value = false
  }
}

const extractPrimaryRoleId = (roleList = []) => {
  if (!Array.isArray(roleList) || roleList.length === 0) {
    return null
  }
  const target = roleList[0]
  return target?.role_id ?? null
}

const hasRoleKey = (row, targetKey) => {
  return (row.role_list || []).some(role => role.role_key === targetKey)
}

// 检查是否为超级管理员
const isSuperAdmin = (row) => {
  return hasRoleKey(row, 'super_admin')
}

const getRoleTagType = (roleKey) => {
  const map = {
    super_admin: 'danger',
    admin: 'warning',
    operator: '',
  }
  return map[roleKey] || 'info'
}

const loadData = async () => {
  loading.value = true
  try {
    const data = await queryAllAdmins()
    console.log('管理员列表数据:', data)

    // 从返回的数据中提取 admins 数组，并转换数据格式
    if (data && data.admins) {
      admins.value = data.admins.map(admin => {
        const roleList = normalizeRoleList(admin)
        return {
          ...admin,
          role_list: roleList,
          status: normalizeStatus(admin.status),
        }
      })
    } else {
      admins.value = []
    }

    console.log('转换后的管理员数据:', admins.value)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadRoleOptions()
  loadData()
})

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
    `确定要重置管理员 ${row.username} 的密码吗？`,
    '重置密码',
    {
      confirmButtonText: '确定重置',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try{
        await resetAdminPassword(row.user_id)
        ElMessage.success('密码重置成功')
      } catch (error) {
        ElMessage.error('密码重置失败，请稍后重试')
      }
    })
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
    role_id: extractPrimaryRoleId(row.role_list || []),
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
    await updateAdmin({
      user_id: editForm.value.user_id,
      username: editForm.value.username,
      phone: editForm.value.phone || null,
      email: editForm.value.email || null,
      roles: editForm.value.role_id ? [editForm.value.role_id] : [],
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
    role_id: null,
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
    await createAdmin({
      username: createForm.value.username,
      password: createForm.value.password,
      phone: createForm.value.phone,
      email: createForm.value.email,
      roles: createForm.value.role_id ? [createForm.value.role_id] : [],
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

    <el-table :data="admins" v-loading="loading" border stripe row-key="user_id">
      <!-- 账号列 - 用于登录的账号名 -->
      <el-table-column label="用户 ID" prop="user_id" min-width="140"/>

      <!-- 用户名列 -->
      <el-table-column label="用户名" prop="username" min-width="140" />

      <!-- 角色列 -->
      <el-table-column label="角色" min-width="220">
        <template #default="{ row }">
          <div class="role-tags">
            <template v-for="(role, index) in row.role_list" :key="role.role_key || role.role_id || `role-${index}`">
              <el-tag
                :type="getRoleTagType(role.role_key)"
                effect="plain"
              >
                {{ role.role_name || role.role_key }}
              </el-tag>
            </template>
            <span v-if="!row.role_list || !row.role_list.length">-</span>
            <el-tooltip v-if="isSuperAdmin(row)" content="系统最高权限，不可删除或禁用" placement="top">
              <el-icon style="margin-left: 4px; color: #e6a23c;">
                <Warning />
              </el-icon>
            </el-tooltip>
          </div>
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
      <el-table-column label="操作" min-width="300" fixed="right">
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
      <el-form-item label="角色" prop="role_id">
        <el-select
          v-model="createForm.role_id"
          filterable
          placeholder="请选择角色"
          :loading="roleOptionsLoading"
          style="width: 100%;"
        >
          <el-option
            v-for="role in roleOptions"
            :key="role.role_id"
            :label="role.label"
            :value="role.role_id"
            :disabled="role.status !== 1"
          />
        </el-select>
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
            <div>· 至少选择一个角色，角色决定可访问的功能</div>
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
      <el-form-item label="角色" prop="role_id">
        <el-select
          v-model="editForm.role_id"
          filterable
          placeholder="请选择角色"
          :loading="roleOptionsLoading"
          style="width: 100%;"
        >
          <el-option
            v-for="role in roleOptions"
            :key="role.role_id"
            :label="role.label"
            :value="role.role_id"
            :disabled="role.status !== 1"
          />
        </el-select>
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
            <div>· 角色修改后，重新登录即可生效</div>
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

.role-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-height: 32px;
}

.role-tags .el-tag {
  transition: none;
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

/* 禁用表格单元格的过渡效果，防止内容位移 */
:deep(.el-table__body td) {
  transition: none !important;
}

:deep(.el-table__body .cell) {
  transition: none !important;
}
</style>
