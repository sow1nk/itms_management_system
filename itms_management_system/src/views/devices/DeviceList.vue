<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchDeviceList, createDevice, unbindDevice, fetchDeviceDetail, assignDevice } from '@/api/modules/devices'
import { queryAllAppUsers } from '@/api/modules/users'
import { usePermission } from '@/composables/usePermission'
import { PERMISSIONS } from '@/utils/permission'

// 使用权限 composable
const { can } = usePermission()

const loading = ref(false)
const devices = ref([])
const query = ref({
  name: '',
  sn: '',
  owner: '',
  ip: '',
  online: '', // '', 'online', 'offline'
})

const assignDialogVisible = ref(false)
const assignOwnerId = ref(null)
const currentDevice = ref(null)
const appUserOptions = ref([])

const dialogVisible = ref(false)
const form = ref({
  name: '',
  sn: '',
  ip: '',
  online: true,
})

const resetForm = () => {
  form.value = {
    name: '',
    sn: '',
    ip: '',
    online: true,
  }
}

const loadData = async () => {
  loading.value = true
  try {
    devices.value = await fetchDeviceList()
  } finally {
    loading.value = false
  }
}

onMounted(loadData)

const handleOpenCreate = () => {
  resetForm()
  dialogVisible.value = true
}

const handleCreate = async () => {
  if (!form.value.name || !form.value.sn) {
    ElMessage.warning('请填写设备名称和序列号')
    return
  }
  try {
    await createDevice({
      name: form.value.name,
      sn: form.value.sn,
      ip: form.value.ip || null,
      online: form.value.online,
    })
    ElMessage.success('设备创建成功')
    dialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示由请求拦截器统一处理
  }
}

const handleUnbind = async (row) => {
  try {
    await ElMessageBox.confirm(`确认解除设备【${row.name}】的用户分配？`, '提示', {
      type: 'warning',
    })
  } catch {
    return
  }

  try {
    await unbindDevice(row.id)
    ElMessage.success('设备已解除分配')
    await loadData()
  } catch {
    // 错误提示由请求拦截器统一处理
  }
}

const loadAppUsers = async () => {
  try {
    const res = await queryAllAppUsers()
    const list = Array.isArray(res) ? res : res?.users || []
    appUserOptions.value = list.map((item) => ({
      id: item.id || item.user_id,
      username: item.username,
    }))
  } catch {
    ElMessage.error('加载用户列表失败')
  }
}

const handleOpenAssign = async (row) => {
  currentDevice.value = row
  assignOwnerId.value = row.owner ? row.owner.id : null
  if (!appUserOptions.value.length) {
    await loadAppUsers()
  }
  assignDialogVisible.value = true
}

const handleAssign = async () => {
  if (!currentDevice.value) return
  if (!assignOwnerId.value) {
    ElMessage.warning('请选择要分配的用户')
    return
  }

  try {
    await assignDevice(currentDevice.value.id, assignOwnerId.value)
    ElMessage.success('设备分配成功')
    assignDialogVisible.value = false
    await loadData()
  } catch {
    // 错误提示统一处理
  }
}

const handleDetail = async (row) => {
  try {
    const res = await fetchDeviceDetail(row.id)
    const dev = res?.device || {}
    ElMessage.info(`设备：${dev.name || row.name}\nSN：${dev.sn || row.sn}\nIP：${dev.ip || row.ip || '-'}\n状态：${dev.online ? '在线' : '离线'}`)
  } catch {
    // 交给拦截器
  }
}

const filteredDevices = computed(() => {
  const name = query.value.name.trim().toLowerCase()
  const sn = query.value.sn.trim().toLowerCase()
  const owner = query.value.owner.trim().toLowerCase()
   const ip = query.value.ip.trim().toLowerCase()
   const online = query.value.online

  return devices.value.filter((d) => {
    const matchName = !name || (d.name || '').toLowerCase().includes(name)
    const matchSn = !sn || (d.sn || '').toLowerCase().includes(sn)
    const ownerName = d.owner?.username || ''
    const matchOwner = !owner || ownerName.toLowerCase().includes(owner)
     const matchIp = !ip || (d.ip || '').toLowerCase().includes(ip)
     const matchOnline =
       !online || (online === 'online' ? !!d.online : !d.online)

     return matchName && matchSn && matchOwner && matchIp && matchOnline
  })
})
</script>

<template>
  <el-card shadow="never">
    <div class="module-header">
      <div>
        <h3>设备管理</h3>
        <p>掌握设备运行状态、绑定用户与网络信息。</p>
      </div>
      <el-button
        type="primary"
        plain
        :disabled="!can(PERMISSIONS.DEVICE.CREATE)"
        @click="handleOpenCreate"
      >
        新增设备
      </el-button>
    </div>

    <el-form :inline="true" class="filter-form" @submit.prevent>
      <el-form-item label="设备名称">
        <el-input v-model="query.name" placeholder="支持模糊搜索" clearable />
      </el-form-item>
      <el-form-item label="序列号 SN">
        <el-input v-model="query.sn" placeholder="支持模糊搜索" clearable />
      </el-form-item>
      <el-form-item label="所属用户">
        <el-input v-model="query.owner" placeholder="支持模糊搜索" clearable />
      </el-form-item>
      <el-form-item label="IP 地址">
        <el-input v-model="query.ip" placeholder="支持模糊搜索" clearable />
      </el-form-item>
      <el-form-item label="在线状态">
        <el-select v-model="query.online" placeholder="全部" clearable style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
        </el-select>
      </el-form-item>
    </el-form>

    <el-table :data="filteredDevices" v-loading="loading" border>
      <el-table-column label="设备名称" prop="name" min-width="180" />
      <el-table-column label="序列号 SN" prop="sn" min-width="160" />
      <el-table-column label="IP 地址" prop="ip" min-width="140" />
      <el-table-column label="在线状态" min-width="120">
        <template #default="{ row }">
          <el-tag :type="row.online ? 'success' : 'danger'" effect="plain">
            {{ row.online ? '在线' : '离线' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="所属用户" min-width="160">
        <template #default="{ row }">
          <el-tag v-if="row.owner" type="info">{{ row.owner.username }}</el-tag>
          <el-tag v-else type="warning" effect="plain">未分配</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            text
            size="small"
            :disabled="!can(PERMISSIONS.DEVICE.VIEW)"
            @click="handleDetail(row)"
          >
            查看详情
          </el-button>
          <el-button
            type="success"
            text
            size="small"
            :disabled="!can(PERMISSIONS.DEVICE.UPDATE)"
            @click="handleOpenAssign(row)"
          >
            分配用户
          </el-button>
          <el-button
            type="danger"
            text
            size="small"
            :disabled="!can(PERMISSIONS.DEVICE.UPDATE)"
            @click="handleUnbind(row)"
          >
            解除分配
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="新增设备" width="480px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="设备名称">
          <el-input v-model="form.name" placeholder="请输入设备名称" />
        </el-form-item>
        <el-form-item label="序列号 SN">
          <el-input v-model="form.sn" placeholder="请输入序列号" />
        </el-form-item>
        <el-form-item label="IP 地址">
          <el-input v-model="form.ip" placeholder="例如 192.168.10.10" />
        </el-form-item>
        <el-form-item label="在线状态">
          <el-switch v-model="form.online" active-text="在线" inactive-text="离线" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleCreate">保 存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="assignDialogVisible" title="分配用户" width="420px">
      <el-form label-width="80px">
        <el-form-item label="设备">
          <span>{{ currentDevice?.name }}（SN：{{ currentDevice?.sn }}）</span>
        </el-form-item>
        <el-form-item label="所属用户">
          <el-select v-model="assignOwnerId" placeholder="请选择用户" filterable style="width: 260px">
            <el-option
              v-for="item in appUserOptions"
              :key="item.id"
              :label="item.username + '（ID: ' + item.id + '）'"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="handleAssign">确 定</el-button>
      </template>
    </el-dialog>
  </el-card>
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
  margin-bottom: 12px;
}
</style>
