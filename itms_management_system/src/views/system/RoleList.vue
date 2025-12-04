<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { queryAllRoles, queryRolePermissions, createRole, updateRole, deleteRole, updateRolePermissions } from '@/api/modules/roles'
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS, PERMISSION_TREE } from '@/utils/permission'

const loading = ref(false)
const roles = ref([])
const queryParams = ref({
  role_name: '',
  role_key: '',
  page: 1,
  pageSize: 10,
})
const pagination = ref({
  page: 1,
  pageSize: 10,
  total: 0,
})

const normalizeRoleStatus = (status) => {
  if (typeof status === 'number') {
    return status === 0 ? 0 : 1
  }
  if (typeof status === 'boolean') {
    return status ? 1 : 0
  }
  if (typeof status === 'string') {
    const lowered = status.toLowerCase()
    if (['0', 'false', 'disabled', 'inactive', 'off'].includes(lowered)) {
      return 0
    }
    if (['1', 'true', 'enabled', 'active', 'on', 'normal'].includes(lowered)) {
      return 1
    }
  }
  return 1
}

// 使用权限 composable
const { can } = usePermission()

// 新增角色相关
const createDialogVisible = ref(false)
const createFormRef = ref()
const createForm = ref({
  role_name: '',
  role_key: '',
})
const createFormRules = {
  role_name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' },
    { min: 2, max: 50, message: '角色名称长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  role_key: [
    { required: true, message: '请输入角色标识', trigger: 'blur' },
    { min: 2, max: 50, message: '角色标识长度在 2 到 50 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '角色标识只能包含字母、数字和下划线', trigger: 'blur' },
  ],
}
const createLoading = ref(false)

// 编辑角色相关
const editDialogVisible = ref(false)
const editFormRef = ref()
const editForm = ref({
  role_id: null,
  role_name: '',
  role_key: '',
})
const editFormRules = {
  role_name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' },
    { min: 2, max: 50, message: '角色名称长度在 2 到 50 个字符', trigger: 'blur' },
  ],
  role_key: [
    { required: true, message: '请输入角色标识', trigger: 'blur' },
    { min: 2, max: 50, message: '角色标识长度在 2 到 50 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '角色标识只能包含字母、数字和下划线', trigger: 'blur' },
  ],
}
const editLoading = ref(false)

// 权限分配相关
const permissionDialogVisible = ref(false)
const permissionLoading = ref(false)
const currentPermissionRole = ref(null)
const permissionTreeRef = ref()
const checkedPermissions = ref([])

// 加载角色列表数据
const loadData = async () => {
  loading.value = true
  try {
    const params = {
      role_name: queryParams.value.role_name || undefined,
      role_key: queryParams.value.role_key || undefined,
      page: queryParams.value.page,
      page_size: queryParams.value.pageSize,
    }
    const data = await queryAllRoles(params)
    console.log('角色列表数据:', data)

    if (data && data.roles) {
      roles.value = data.roles.map(role => ({
        ...role,
        status: normalizeRoleStatus(role.status),
      }))
    } else {
      roles.value = []
    }

    const paginationData = data?.pagination || {}
    pagination.value = {
      page: paginationData.page || queryParams.value.page,
      pageSize: paginationData.page_size || paginationData.pageSize || queryParams.value.pageSize,
      total: paginationData.total ?? (data?.roles ? data.roles.length : 0),
    }

    console.log('角色数据:', roles.value)
  } catch (error) {
    console.error('加载角色列表失败:', error)
    ElMessage.error('加载角色列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const handleSearch = () => {
  queryParams.value.page = 1
  loadData()
}

const handleReset = () => {
  queryParams.value.role_name = ''
  queryParams.value.role_key = ''
  handleSearch()
}

const handlePageChange = (page) => {
  queryParams.value.page = page
  loadData()
}

const handlePageSizeChange = (size) => {
  queryParams.value.pageSize = size
  queryParams.value.page = 1
  loadData()
}

// 检查是否为超级管理员角色
const isSuperAdminRole = (row) => {
  return row.role_key === 'super_admin'
}

// 打开新增角色对话框
const handleCreate = () => {
  createDialogVisible.value = true
  createForm.value = {
    role_name: '',
    role_key: '',
  }
  nextTick(() => {
    createFormRef.value?.clearValidate()
  })
}

// 提交新增角色
const handleCreateSubmit = async () => {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return

  createLoading.value = true
  try {
    await createRole({
      role_name: createForm.value.role_name,
      role_key: createForm.value.role_key,
    })

    ElMessage.success('角色创建成功')
    createDialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('创建角色失败:', error)
    ElMessage.error('创建角色失败，请稍后重试')
  } finally {
    createLoading.value = false
  }
}

// 打开编辑角色对话框
const handleEdit = (row) => {
  editDialogVisible.value = true
  editForm.value = {
    role_id: row.role_id,
    role_name: row.role_name,
    role_key: row.role_key || '',
  }
  nextTick(() => {
    editFormRef.value?.clearValidate()
  })
}

// 提交编辑角色
const handleEditSubmit = async () => {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return

  editLoading.value = true
  try {
    await updateRole({
      role_id: editForm.value.role_id,
      role_name: editForm.value.role_name,
      role_key: editForm.value.role_key,
    })

    ElMessage.success('角色信息更新成功')
    editDialogVisible.value = false
    await loadData()
  } catch (error) {
    console.error('更新角色失败:', error)
    ElMessage.error('更新角色失败，请稍后重试')
  } finally {
    editLoading.value = false
  }
}

// 处理删除角色
const handleDelete = async (row) => {
  ElMessageBox.confirm(`确认删除角色 "${row.role_name}" 吗？此操作不可恢复！`, '危险操作', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'error',
  })
    .then(async () => {
      try {
        await deleteRole(row.role_id)
        ElMessage.success('删除角色成功')
        await loadData()
      } catch (error) {
        console.error('删除角色失败:', error)
        ElMessage.error('删除角色失败，请稍后重试')
      }
    })
    .catch(() => {})
}

const handleStatusChange = async (row, value) => {
  // 双重保护：即使 switch 没被禁用，也要检查权限
  if (isSuperAdminRole(row)) {
    // 恢复原状态
    row.status = value === 1 ? 0 : 1
    ElMessage.warning('超级管理员角色不可禁用')
    return
  }

  const action = value === 1 ? '启用' : '禁用'
  ElMessageBox.confirm(`确认${action}该角色吗？`, '操作确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await updateRole({
          role_id: row.role_id,
          status: value,
        })
        row.status = value
        ElMessage.success(`角色已${action}`)
      } catch (error) {
        console.error('更新角色状态失败:', error)
        ElMessage.error('更新角色状态失败，请稍后重试')
        // 失败时恢复原状态
        row.status = value === 1 ? 0 : 1
      }
    })
    .catch(() => {
      // 用户取消，恢复原状态
      row.status = value === 1 ? 0 : 1
    })
}

// 处理分配权限
const handleAssignPermissions = async (row) => {
  currentPermissionRole.value = row
  permissionDialogVisible.value = true
  permissionLoading.value = true

  try {
    const response = await queryRolePermissions(row.role_id)
    console.log('角色当前权限:', response)

    if (response && response.permissions && Array.isArray(response.permissions)) {
      checkedPermissions.value = response.permissions.map(item => item.perm_key).filter(Boolean)
      console.log('转换后的权限列表:', checkedPermissions.value)
    } else {
      checkedPermissions.value = []
    }

    await nextTick()
    permissionTreeRef.value?.setCheckedKeys(checkedPermissions.value)
  } catch (error) {
    console.error('获取角色权限失败:', error)
    ElMessage.error('获取角色权限失败')
  } finally {
    permissionLoading.value = false
  }
}

// 提交权限分配
const handlePermissionSubmit = async () => {
  if (!currentPermissionRole.value) return

  permissionLoading.value = true
  try {
    const checkedKeys = permissionTreeRef.value.getCheckedKeys()
    const halfCheckedKeys = permissionTreeRef.value.getHalfCheckedKeys()
    const allPermissions = [...checkedKeys, ...halfCheckedKeys]

    // 过滤掉分组节点，只保留真实权限
    const validPermissions = allPermissions.filter(perm => {
      return perm && perm.includes(':') && !perm.endsWith('_group')
    })

    console.log('保存角色权限:', {
      roleId: currentPermissionRole.value.role_id,
      permissions: validPermissions,
    })

    await updateRolePermissions(currentPermissionRole.value.role_id, validPermissions)
    ElMessage.success('权限分配成功')
    permissionDialogVisible.value = false
  } catch (error) {
    console.error('权限分配失败:', error)
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
        <h3>角色管理</h3>
        <p>管理系统角色及其权限配置。</p>
      </div>
      <el-button
        type="primary"
        plain
        :disabled="!can(PERMISSIONS.SYSTEM_ROLE.CREATE)"
        @click="handleCreate"
      >
        <el-icon><Plus /></el-icon>
        新增角色
      </el-button>
    </div>

    <el-form inline class="query-form" @submit.prevent>
      <el-form-item label="角色名称">
        <el-input
          v-model="queryParams.role_name"
          placeholder="请输入角色名称"
          clearable
          style="width: 200px"
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item label="角色标识">
        <el-input
          v-model="queryParams.role_key"
          placeholder="请输入角色标识"
          clearable
          style="width: 200px"
          @keyup.enter="handleSearch"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSearch">
          查询
        </el-button>
        <el-button @click="handleReset">
          重置
        </el-button>
      </el-form-item>
    </el-form>

    <el-table :data="roles" v-loading="loading" border stripe>
      <el-table-column label="角色 ID" prop="role_id" min-width="100"/>
      <el-table-column label="角色名称" prop="role_name" min-width="160" />
      <el-table-column label="角色标识" prop="role_key" min-width="160" />
      <el-table-column label="状态" min-width="140">
        <template #default="{ row }">
          <div class="status-cell">
            <el-switch
              v-model="row.status"
              :active-value="1"
              :inactive-value="0"
              active-text="启用"
              inactive-text="禁用"
              :disabled="!can(PERMISSIONS.SYSTEM_ROLE.UPDATE) || isSuperAdminRole(row)"
              @change="(value) => handleStatusChange(row, value)"
            />
            <el-tooltip v-if="isSuperAdminRole(row)" placement="top">
              <template #content>
                <span>超级管理员角色不可禁用</span>
              </template>
              <el-icon style="margin-left: 4px; color: #909399;">
                <InfoFilled />
              </el-icon>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" min-width="280" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button
              type="primary"
              link
              size="small"
              :disabled="!can(PERMISSIONS.SYSTEM_ROLE.UPDATE)"
              @click="handleEdit(row)"
            >
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>

            <el-button
              type="warning"
              link
              size="small"
              :disabled="!can(PERMISSIONS.SYSTEM_ROLE.ASSIGN_PERMISSIONS)"
              @click="handleAssignPermissions(row)"
            >
              <el-icon><Key /></el-icon>
              分配权限
            </el-button>

            <el-button
              type="danger"
              link
              size="small"
              :disabled="!can(PERMISSIONS.SYSTEM_ROLE.DELETE)"
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="table-pagination" v-if="pagination.total > 0">
      <el-pagination
        background
        layout="total, prev, pager, next, sizes"
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="handlePageChange"
        @size-change="handlePageSizeChange"
      />
    </div>
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
        <el-form-item label="角色 ID">
          <span>{{ currentPermissionRole?.role_id }}</span>
        </el-form-item>
        <el-form-item label="角色名称">
          <span>{{ currentPermissionRole?.role_name }}</span>
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
              <div>· 权限变更后，拥有该角色的管理员需重新登录生效</div>
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

  <!-- 新增角色对话框 -->
  <el-dialog
    v-model="createDialogVisible"
    title="新增角色"
    width="500px"
    destroy-on-close
  >
    <el-form
      ref="createFormRef"
      :model="createForm"
      :rules="createFormRules"
      label-width="100px"
    >
      <el-form-item label="角色名称" prop="role_name">
        <el-input
          v-model="createForm.role_name"
          placeholder="请输入角色名称"
          maxlength="50"
          show-word-limit
          clearable
        />
      </el-form-item>
      <el-form-item label="角色标识" prop="role_key">
        <el-input
          v-model="createForm.role_key"
          placeholder="请输入角色标识，例如 super_admin"
          maxlength="50"
          show-word-limit
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
            <div>· 角色名称：2-50个字符</div>
            <div>· 角色标识：仅限字母/数字/下划线，建议全局唯一</div>
            <div>· 新建角色默认没有任何权限，需要单独分配</div>
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

  <!-- 编辑角色对话框 -->
  <el-dialog
    v-model="editDialogVisible"
    title="编辑角色"
    width="500px"
    destroy-on-close
  >
    <el-form
      ref="editFormRef"
      :model="editForm"
      :rules="editFormRules"
      label-width="100px"
    >
      <el-form-item label="角色 ID">
        <span style="color: #606266">{{ editForm.role_id }}</span>
      </el-form-item>
      <el-form-item label="角色名称" prop="role_name">
        <el-input
          v-model="editForm.role_name"
          placeholder="请输入角色名称"
          maxlength="50"
          show-word-limit
          clearable
        />
      </el-form-item>
      <el-form-item label="角色标识" prop="role_key">
        <el-input
          v-model="editForm.role_key"
          placeholder="请输入角色标识"
          maxlength="50"
          show-word-limit
          clearable
        />
      </el-form-item>
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

.query-form {
  margin-bottom: 12px;
}

.table-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
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
