<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { addAppUser, updateAppUser, queryAllAppUsers, queryById, queryAppUsers, updateAppUserStatus, assignDevicesToUser, resetAppUserKey } from '@/api/modules/users'
import { fetchDeviceList } from '@/api/modules/devices'
import { useUserStore } from '@/store/modules/user'
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS } from '@/utils/permission'

const loading = ref(false)
const users = ref([])
const userDialogVisible = ref(false)
const userDialogMode = ref('create')
const userFormRef = ref()
const submitting = ref(false)

const filterForm = reactive({
  phone: '',
  email: '',
  username: '',
  role: '',
  onlineStatus: '',
})

const roleOptions = [
  { label: '全部角色', value: '' },
  { label: '普通用户', value: 'normal' },
  { label: 'VIP 用户', value: 'vip' },
  { label: '安防专员', value: 'security' },
]

const onlineOptions = [
  { label: '全部状态', value: '' },
  { label: '在线', value: 'online' },
  { label: '离线', value: 'offline' },
]

const roleTagMap = {
  normal: { label: '普通用户', type: 'info' },
  vip: { label: 'VIP 用户', type: 'warning' },
  security: { label: '安防专员', type: 'success' },
}

const tableHeaderStyle = {
  backgroundColor: '#f5f7fa',
  color: '#303133',
  fontWeight: 600,
}

const statusOptions = [
  { label: '正常', value: 'normal' },
  { label: '冻结', value: 'frozen' },
]

const generateUserId = () => `U-${Date.now()}`
// const generateAccessKey = () => `AK-${Math.random().toString(36).slice(2, 10).toUpperCase()}`

const formatDateTime = (date = new Date()) => {
  const pad = (n) => `${n}`.padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

const resetUserForm = () => {
  userForm.id = ''  // ID will be auto-generated when saving
  userForm.username = ''
  userForm.phone = ''
  userForm.email = ''
  userForm.role = 'normal'
  userForm.status = 'normal'
  userForm.devices = []
}

const userStore = useUserStore()
const isSuperAdmin = computed(() => (userStore.roles || []).includes('super_admin'))

// 使用权限 composable
const { can } = usePermission()

const userForm = reactive({
  id: '',
  username: '',
  phone: '',
  email: '',
  role: 'normal',
  status: 'normal',
  devices: [],
  // System-generated fields (not editable):
  registerTime: '',
  isOnline: false,
  accessKey: '',
  keyUpdatedAt: '',
})

const transformUsers = (list = []) =>
  list.map((item) => {
    const rawStatus = item.status ?? item.app_status
    const status = rawStatus === 'frozen' || rawStatus === '0' || rawStatus === 0 ? 'frozen' : 'normal'
    const devices = Array.isArray(item.devices) ? [...item.devices] : []
    return {
      id: item.id || item.user_id || generateUserId(),
      username: item.username || '',
      phone: item.phone || '',
      email: item.email || item.mail || '',
      role: item.role || item.app_role || 'normal',
      status,
      isOnline: status === 'normal' ? Boolean(item.isOnline ?? item.is_online ?? item.online) : false,
      registerTime: item.registerTime || item.register_time || '',
      accessKey: item.accessKey || item.access_key || '',
      keyUpdatedAt: item.keyUpdatedAt || item.key_updated_at || item.registerTime || item.register_time || '',
      deviceCount: item.deviceCount ?? item.device_count ?? devices.length,
      devices,
    }
  })

const loadData = async () => {
  loading.value = true
  try {
    const response = await queryAllAppUsers()
    const list = Array.isArray(response) ? response : response?.users || []
    users.value = transformUsers(list)
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const handleSearch = async () => {
  const phone = filterForm.phone.trim()
  const email = filterForm.email.trim()

  if (!phone && !email) {
    await loadData()
    return
  }

  loading.value = true
  try {
    const response = await queryAppUsers(phone || undefined, email || undefined)
    const list = Array.isArray(response) ? response : response?.users || []
    users.value = transformUsers(list)
  } catch (error) {
    console.error(error)
    ElMessage.error('查询失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const handleReset = () => {
  filterForm.phone = ''
  filterForm.email = ''
  filterForm.username = ''
  filterForm.role = ''
  filterForm.onlineStatus = ''
  loadData()
}

const handleStatusChange = (row) => {
  const nextStatus = row.status === 'normal' ? 'frozen' : 'normal'
  const action = nextStatus === 'normal' ? '解冻' : '冻结'

  return ElMessageBox.confirm(`确定要${action}该用户吗？`, '账号状态确认', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      // 如果要冻结账号且当前用户在线，需要将其设为离线
      const isOnline = nextStatus === 'frozen' && row.isOnline ? false : row.isOnline

      const payload = {
        id: row.id,
        username: row.username,
        phone: row.phone,
        email: row.email,
        role: row.role,
        status: nextStatus,
        app_role: row.role,
        isOnline,  // 添加 isOnline 字段
      }

      console.log('更新用户状态:', payload)

      await updateAppUser(payload)
      row.status = nextStatus
      if (nextStatus === 'frozen') {
        row.isOnline = false
      }
      ElMessage.success(`${action}成功`)
      loadData()
      return true
    })
    .catch(() => false)
}

const handleCreateUser = () => {
  userDialogMode.value = 'create'
  resetUserForm()
  userDialogVisible.value = true
}

const handleEdit = async (row) => {
  userDialogMode.value = 'edit'
  try {
    const response = await queryById(row.id)
    const data = response?.user || response
    userForm.id = data?.id || row.id
    userForm.username = data?.username || row.username
    userForm.phone = data?.phone || row.phone
    userForm.email = data?.email || row.email || ''
    userForm.role = data?.role || data?.app_role || row.role
  } catch (error) {
    console.error(error)
    ElMessage.error('获取用户信息失败')
    return
  }
  userDialogVisible.value = true
}


const handleUserSubmit = () => {
  userFormRef.value?.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (userDialogMode.value === 'create') {
        const payload = {
          username: userForm.username,
          phone: userForm.phone,
          email: userForm.email,
          role: userForm.role,
          app_role: userForm.role,
        }
        await addAppUser(payload)
        ElMessage.success('用户创建成功')
      } else {
        const payload = {
          id: userForm.id,
          username: userForm.username,
          phone: userForm.phone,
          email: userForm.email,
          role: userForm.role,
          app_role: userForm.role,
        }
        await updateAppUser(payload)
        ElMessage.success('用户更新成功')
      }
      userDialogVisible.value = false
      loadData()
    } catch (error) {
      console.log(error)
      ElMessage.error('操作失败，请重试')
    } finally {
      submitting.value = false
    }
  })
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除用户 ${row.username} ?`, '危险操作', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'error',
  })
    .then(() => {
      users.value = users.value.filter((item) => item.id !== row.id)
      ElMessage.success('用户已删除 (mock)')
    })
    .catch(() => {})
}

const handleKick = (row) => {
  if (!row.isOnline) {
    ElMessage.warning('该用户当前不在线')
    return
  }
  ElMessageBox.confirm(`确认强制下线 ${row.username} 吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        await updateAppUserStatus(row.id, row.isOnline)
        ElMessage.success('已强制下线')
        loadData()
      } catch (error) {
        console.error(error)
        ElMessage.error('强制下线失败，请重试')
      }
    })
    .catch(() => {})
}

const maskAccessKey = (key = '') => {
  if (!key || typeof key !== 'string') return '--'
  if (key.length <= 8) return key
  return `${key.slice(0, 4)}****${key.slice(-4)}`
}

const handleCopyKey = async (row) => {
  try {
    await navigator.clipboard.writeText(row.accessKey)
    ElMessage.success('密钥已复制')
  } catch (error) {
    console.error(error)
    ElMessage.error('复制失败，请手动复制')
  }
}

const handleResetKey = (row) => {
  ElMessageBox.confirm('重置密钥将导致旧设备无法连接，是否继续？', '密钥管理', {
    confirmButtonText: '重置',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(async () => {
      try {
        const response = await resetAppUserKey(row.id)
        // 提取密钥字符串，兼容不同的响应格式
        const newAccessKey = response?.accessKey || response?.access_key || response
        row.accessKey = newAccessKey
        row.keyUpdatedAt = formatDateTime()
        ElMessage.success('密钥已重置')
        loadData()
      } catch (error) {
        console.error(error)
        ElMessage.error('重置密钥失败，请稍后重试')
      }
    })
    .catch(() => {})
}

const assignDialogVisible = ref(false)
const assignLoading = ref(false)
const currentUser = ref(null)
const deviceOptions = ref([])
const selectedDeviceIds = ref([])

const openAssignDevices = async (row) => {
  currentUser.value = row
  assignDialogVisible.value = true
  assignLoading.value = true
  try {
    const devices = await fetchDeviceList()
    deviceOptions.value = devices
    // 预选当前已分配给该用户的设备
    selectedDeviceIds.value = devices
      .filter((d) => d.owner && (d.owner.id === row.id || d.owner.user_id === row.id))
      .map((d) => d.id)
  } catch (error) {
    console.error(error)
    ElMessage.error('加载设备列表失败')
  } finally {
    assignLoading.value = false
  }
}

const handleAssignDevices = async () => {
  if (!currentUser.value) return
  if (!Array.isArray(selectedDeviceIds.value)) selectedDeviceIds.value = []
  assignLoading.value = true
  try {
    await assignDevicesToUser(currentUser.value.id, selectedDeviceIds.value)
    ElMessage.success('分配设备成功')
    assignDialogVisible.value = false
    loadData()
  } catch (error) {
    console.error(error)
    ElMessage.error('分配设备失败，请稍后重试')
  } finally {
    assignLoading.value = false
  }
}

const resolveRoleTag = (role) => roleTagMap[role] || { label: '未知角色', type: 'info' }
const userDialogTitle = computed(() => (userDialogMode.value === 'edit' ? '编辑用户' : '新增用户'))

const userFormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

watch(
  () => userForm.status,
  (val) => {
    if (val === 'frozen') {
      userForm.isOnline = false
    }
  },
)
</script>

<template>
  <el-card shadow="never">
    <div class="module-header">
      <div>
        <h3>App 用户管理</h3>
        <p>管理 C 端用户、在线状态、密钥等信息。</p>
      </div>
      <el-button
        type="primary"
        plain
        :disabled="!can(PERMISSIONS.USER.CREATE)"
        @click="handleCreateUser"
      >
        新建用户
      </el-button>
    </div>

    <el-form :inline="true" :model="filterForm" class="filter-form">
      <el-form-item label="手机号">
        <el-input v-model="filterForm.phone" style="width: 240px" placeholder="请输入手机号" clearable />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="filterForm.email" style="width: 240px" placeholder="请输入邮箱" clearable />
      </el-form-item>
      <el-form-item label="用户角色">
        <el-select v-model="filterForm.role" placeholder="全部" clearable>
          <el-option v-for="item in roleOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="在线状态">
        <el-select v-model="filterForm.onlineStatus" placeholder="全部" clearable>
          <el-option v-for="item in onlineOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-table :data="users" v-loading="loading" border :header-cell-style="tableHeaderStyle">
      <el-table-column label="用户 ID" prop="id" min-width="120" />
      <el-table-column label="用户名" prop="username" min-width="120" />
      <el-table-column label="手机号" prop="phone" min-width="130" />
      <el-table-column label="邮箱" prop="email" min-width="180">
        <template #default="{ row }">
          {{ row.email || '--' }}
        </template>
      </el-table-column>
      <el-table-column label="用户角色" min-width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="resolveRoleTag(row.role).type" effect="plain">
            {{ resolveRoleTag(row.role).label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="账号状态" min-width="160">
        <template #default="{ row }">
          <el-switch
            v-model="row.status"
            active-value="normal"
            inactive-value="frozen"
            inline-prompt
            active-text="正常"
            inactive-text="冻结"
            :disabled="!can(PERMISSIONS.USER.STATUS)"
            :before-change="() => handleStatusChange(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="在线状态" min-width="140">
        <template #default="{ row }">
          <div class="online-status">
            <span class="online-status__dot" :class="{ 'online-status__dot--active': row.isOnline }" />
            {{ row.isOnline ? '在线' : '离线' }}
          </div>
        </template>
      </el-table-column>
      <el-table-column label="接入密钥" min-width="200">
        <template #default="{ row }">
          <div class="key-cell">
            <span class="key-cell__value">{{ maskAccessKey(row.accessKey) }}</span>
            <el-tooltip content="复制密钥">
              <el-button link type="primary" circle @click="handleCopyKey(row)">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="320" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button
              link
              type="primary"
              size="small"
              :disabled="!can(PERMISSIONS.USER.UPDATE)"
              @click="handleEdit(row)"
            >
              编辑
            </el-button>
            <el-button
              link
              type="primary"
              size="small"
              :disabled="!can(PERMISSIONS.USER.ASSIGN_DEVICES)"
              @click="openAssignDevices(row)"
            >
              分配设备
            </el-button>
            <el-button
              link
              type="warning"
              size="small"
              :disabled="!can(PERMISSIONS.USER.RESET_KEY)"
              @click="handleResetKey(row)"
            >
              重置密钥
            </el-button>
            <el-button
              link
              type="danger"
              size="small"
              :disabled="!row.isOnline || !can(PERMISSIONS.USER.KICK)"
              @click="handleKick(row)"
            >
              强制下线
            </el-button>
            <el-button
              v-if="isSuperAdmin"
              link
              type="danger"
              size="small"
              :disabled="!can(PERMISSIONS.USER.DELETE)"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="assignDialogVisible" title="分配设备" width="520px" destroy-on-close>
    <el-form label-width="80px">
      <el-form-item label="用户">
        <span>{{ currentUser?.username }}（ID：{{ currentUser?.id }}）</span>
      </el-form-item>
      <el-form-item label="设备">
        <el-select
          v-model="selectedDeviceIds"
          multiple
          filterable
          placeholder="请选择要分配的设备"
          style="width: 100%"
        >
          <el-option
            v-for="dev in deviceOptions"
            :key="dev.id"
            :label="dev.name + '（SN: ' + dev.sn + '）'"
            :value="dev.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="assignDialogVisible = false">取 消</el-button>
      <el-button type="primary" :loading="assignLoading" @click="handleAssignDevices">保 存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="userDialogVisible" :title="userDialogTitle" width="520px" destroy-on-close>
    <el-form ref="userFormRef" :model="userForm" :rules="userFormRules" label-width="90px">
      <el-form-item v-if="userDialogMode === 'edit'" label="用户 ID">
        <el-input v-model="userForm.id" disabled />
      </el-form-item>
      <el-form-item label="用户名" prop="username">
        <el-input v-model="userForm.username" placeholder="请输入用户名" />
      </el-form-item>
      <el-form-item label="手机号" prop="phone">
        <el-input v-model="userForm.phone" placeholder="请输入手机号" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="userForm.email" placeholder="请输入邮箱" />
      </el-form-item>
      <el-form-item label="角色" prop="role">
        <el-select v-model="userForm.role" placeholder="请选择角色">
          <el-option v-for="item in roleOptions.filter((option) => option.value)" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="userDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleUserSubmit">保存</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<style scoped>
.module-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.module-header h3 {
  margin-bottom: 4px;
  color: var(--text-primary);
}

.module-header p {
  color: var(--text-secondary);
  font-size: 13px;
}

.filter-form {
  margin-bottom: 16px;
  padding: 12px 16px;
  background-color: #f9fbff;
  border-radius: 12px;
}

.filter-form .el-form-item {
  margin-bottom: 12px;
}

.filter-form .el-select {
  width: 160px;
}

.user-meta {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.user-meta__name {
  font-weight: 600;
  color: var(--text-primary);
}

.user-meta__sub {
  color: var(--text-secondary);
  font-size: 12px;
}

.online-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-primary);
}

.online-status__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #dcdfe6;
}

.online-status__dot--active {
  background-color: #67c23a;
  box-shadow: 0 0 0 6px rgba(103, 194, 58, 0.15);
}

.key-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.key-cell__value {
  font-weight: 600;
  color: #1f2d3d;
}

.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
}

.dialog-key {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.dialog-key__desc {
  display: block;
  margin-top: 4px;
  color: #909399;
}

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

.permission-tips {
  margin-top: 8px;
  padding: 8px 12px;
  background-color: #f4f4f5;
  border-radius: 4px;
}
</style>
