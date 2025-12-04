<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'
import { usePermissionStore } from '@/store/modules/permission'

const loginFormRef = ref()
const router = useRouter()
const userStore = useUserStore()
const permissionStore = usePermissionStore()
const loading = ref(false)
const rememberMe = ref(true)

const loginForm = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = () => {
  loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const response = await userStore.login({ ...loginForm })
      permissionStore.reset()
      if (!response?.user) {
        await userStore.fetchProfile()
      }
      router.replace('/dashboard')
      ElMessage.success('欢迎回来')
    } catch (error) {
      ElMessage.error(error.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<template>
  <div class="login-scene">
    <div class="login-bg">
      <span class="orb orb-1"></span>
      <span class="orb orb-2"></span>
      <span class="orb orb-3"></span>
    </div>
    <div class="glass-card">
      <div class="glass-card__left">
        <div class="hero-copy">
          <h1>后台管理系统</h1>
          <p>服务于智能交通监控用户管理</p>
        </div>
      </div>
      <div class="glass-card__right">
        <div class="login-panel__title">
          <h2>欢迎登录</h2>
          <p>视频监控后台管理系统</p>
        </div>

        <el-form
          ref="loginFormRef"
          :model="loginForm"
          :rules="rules"
          label-position="top"
          class="login-form"
          @keyup.enter.native="handleLogin"
        >
          <el-form-item label="账号" prop="username">
            <el-input
              v-model="loginForm.username"
              size="large"
              placeholder="请输入账号"
              clearable
              prefix-icon="User"
              class="glass-input"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              size="large"
              show-password
              placeholder="请输入密码"
              prefix-icon="Lock"
              class="glass-input"
            />
          </el-form-item>

          <div class="login-extra">
            <el-checkbox v-model="rememberMe">记住密码</el-checkbox>
            <el-link type="primary" :underline="false">忘记密码？</el-link>
          </div>

          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">
            登录
          </el-button>
        </el-form>
        <!-- <p class="login-footer">© 2025 Video Monitor System. All Rights Reserved.</p> -->
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-scene {
  position: relative;
  min-height: 100vh;
  background-color: #f2f6fc;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.login-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 20% 30%, rgba(217, 236, 255, 0.8), transparent 55%),
    radial-gradient(circle at 80% 20%, rgba(233, 233, 235, 0.9), transparent 45%),
    radial-gradient(circle at 30% 80%, rgba(217, 236, 255, 0.6), transparent 50%),
    linear-gradient(135deg, #f8fbff, #f2f6fc 40%, #e8f0fb 100%);
  animation: drift 18s ease-in-out infinite alternate;
}

.orb {
  position: absolute;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.7), transparent 70%);
  filter: blur(6px);
  opacity: 0.8;
  animation: pulse 20s ease-in-out infinite;
}

.orb-1 {
  top: 8%;
  left: 15%;
}

.orb-2 {
  bottom: 25%;
  right: 20%;
  animation-delay: 3s;
}

.orb-3 {
  bottom: 10%;
  left: 30%;
  animation-delay: 6s;
}

.glass-card {
  position: relative;
  width: 900px;
  max-width: 100%;
  height: 550px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.08);
  display: flex;
  overflow: hidden;
  z-index: 1;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.glass-card__left {
  flex: 0 0 40%;
  padding: 48px;
  background: rgba(64, 158, 255, 0.08);
  display: flex;
  align-items: center;
  color: #1677ff;
}

.hero-copy h1 {
  font-size: 30px;
  font-weight: 600;
  margin-bottom: 16px;
}

.hero-copy p {
  color: rgba(22, 119, 255, 0.8);
  line-height: 1.6;
}

.glass-card__right {
  flex: 1;
  background: rgba(255, 255, 255, 0.9);
  padding: 48px 56px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-panel__title h2 {
  font-size: 30px;
  font-weight: 600;
  color: #303133;
}

.login-panel__title p {
  color: #606266;
  margin-top: 8px;
}

.login-form {
  margin-top: 32px;
}

.glass-input :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.85);
  box-shadow: inset 0 0 0 1px rgba(22, 119, 255, 0.08), 0 8px 16px rgba(31, 45, 61, 0.06);
  border-radius: 12px;
}

.glass-input :deep(.el-input__inner) {
  color: #303133;
}

.login-extra {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  color: #606266;
}

.login-btn {
  width: 100%;
  border-radius: 12px;
  background: linear-gradient(135deg, #409eff, #1677ff);
  border: none;
  color: #fff;
  box-shadow: 0 12px 30px rgba(64, 158, 255, 0.25);
}

.login-btn:hover {
  filter: brightness(1.05);
}

.login-footer {
  text-align: center;
  margin-top: 32px;
  color: rgba(96, 98, 102, 0.8);
  font-size: 12px;
}

@keyframes drift {
  0% {
    transform: translate3d(-2%, 0, 0) scale(1);
  }
  100% {
    transform: translate3d(2%, -1%, 0) scale(1.02);
  }
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.5;
  }
}

@media (max-width: 960px) {
  .glass-card {
    flex-direction: column;
    height: auto;
  }

  .glass-card__left,
  .glass-card__right {
    flex: 1;
    padding: 32px;
  }

  .glass-card__left {
    text-align: center;
  }
}
</style>
