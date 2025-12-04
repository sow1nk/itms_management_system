<script setup>
import { reactive, watch, ref } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  user: {
    type: Object,
    default: () => ({
      id: '',
      username: '',
      phone: '',
      role: 'normal',
    }),
  },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const formRef = ref()
const form = reactive({
  id: '',
  username: '',
  phone: '',
  role: 'normal',
})

watch(
  () => props.user,
  (val) => {
    // Only copy editable fields
    form.id = val.id || ''
    form.username = val.username || ''
    form.phone = val.phone || ''
    form.role = val.role || 'normal'
  },
  { immediate: true, deep: true },
)

// 用户角色选项 - 按权限等级排序
const roleOptions = [
  { label: 'VIP用户', value: 'vip' },
  { label: '普通用户', value: 'normal' },
  { label: '安防专员', value: 'security' },
]

// 表单验证规则
const rules = {
  username: [
    { required: true, message: '用户名不能为空', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度为 2-20 个字符', trigger: 'blur' },
  ],
  phone: [
    { required: true, message: '手机号不能为空', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的11位手机号', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择用户角色', trigger: 'change' }],
}

const handleClose = () => emit('update:modelValue', false)

const handleSubmit = () => {
  formRef.value?.validate((valid) => {
    if (!valid) return
    emit('submit', { ...form })
  })
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="编辑用户基本信息"
    width="520px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
      <el-form-item label="用户 ID">
        <el-input v-model="form.id" disabled />
      </el-form-item>

      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" placeholder="请输入用户名" />
      </el-form-item>

      <el-form-item label="手机号" prop="phone">
        <el-input v-model="form.phone" placeholder="请输入手机号" />
      </el-form-item>

      <el-form-item label="用户角色" prop="role">
        <el-select v-model="form.role" placeholder="请选择角色">
          <el-option v-for="option in roleOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
      </el-form-item>

    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button>
      </span>
    </template>
  </el-dialog>
</template>
