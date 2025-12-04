<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { usePermissionStore } from '@/store/modules/permission'
import SidebarItem from './SidebarItem.vue'

const props = defineProps({
  collapse: {
    type: Boolean,
    default: false,
  },
})

const route = useRoute()
const permissionStore = usePermissionStore()

const menuRoutes = computed(() => permissionStore.menuRoutes)
const activeMenu = computed(() => route.meta?.activeMenu || route.path)
</script>

<template>
  <div class="sidebar">
    <div class="sidebar__brand">
      <span class="sidebar__title" :class="{ 'sidebar__title--collapse': props.collapse }">监控后台</span>
    </div>
    <el-scrollbar class="sidebar__scroll">
      <el-menu
        :collapse="props.collapse"
        :default-active="activeMenu"
        background-color="#ffffff"
        class="sidebar__menu"
        router
        text-color="#303133"
        active-text-color="#1677ff"
      >
        <sidebar-item v-for="item in menuRoutes" :key="item.path" :item="item" />
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #ffffff;
  border-right: 1px solid var(--layout-border);
}

.sidebar__brand {
  height: 62px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-primary);
  font-weight: 600;
  letter-spacing: 1px;
  border-bottom: 1px solid var(--layout-border);
}

.sidebar__title {
  white-space: nowrap;
  transition: opacity 0.2s ease;
}

.sidebar__title--collapse {
  font-size: 18px;
}

.sidebar__scroll {
  flex: 1;
}

.sidebar__menu {
  border-right: none;
}
</style>
