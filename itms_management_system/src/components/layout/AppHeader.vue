<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/modules/user'

const props = defineProps({
  collapse: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['toggle'])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const roleLabelMap = {
  super_admin: '超级管理员',
  operator: '运营专员',
  security: '安防专员',
}

const breadcrumbs = computed(() => route.matched.filter((item) => item.meta?.title && item.meta?.breadcrumb !== false))

const displayRole = computed(() => {
  const roles = userStore.roles || []
  if (!roles.length) return '访客'
  const primaryRole = roles[0]
  return roleLabelMap[primaryRole] || primaryRole
})

const handleToggle = () => {
  emit('toggle')
}

const handleLogout = () => {
  userStore.logout()
  router.replace('/login')
}
</script>

<template>
  <header class="layout-header">
    <div class="layout-header__left">
      <el-button link type="primary" class="layout-header__trigger" @click="handleToggle">
        <el-icon>
          <component :is="props.collapse ? 'Expand' : 'Fold'" />
        </el-icon>
      </el-button>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
          {{ item.meta?.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <div class="layout-header__right">
      <div class="layout-header__user">
        <p class="layout-header__name">{{ userStore.name || '未登录' }}</p>
        <p class="layout-header__role">{{ displayRole }}</p>
      </div>
      <el-button type="danger" plain size="small" @click="handleLogout">退出</el-button>
    </div>
  </header>
</template>

<style scoped>
.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 24px;
  background-color: #ffffff;
  border-bottom: 1px solid var(--layout-border);
}

.layout-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.layout-header__trigger {
  font-size: 18px;
}

.layout-header__right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.layout-header__user {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.layout-header__name {
  font-size: 14px;
  color: var(--text-primary);
}

.layout-header__role {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
