<script setup>
import { ref } from 'vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'

const isCollapse = ref(false)

const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}
</script>

<template>
  <el-container class="main-layout">
    <el-aside :width="isCollapse ? '68px' : '220px'" class="main-layout__aside">
      <app-sidebar :collapse="isCollapse" />
    </el-aside>
    <el-container>
      <el-header class="main-layout__header">
        <app-header :collapse="isCollapse" @toggle="toggleSidebar" />
      </el-header>
      <el-main class="main-layout__content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.main-layout__aside {
  background-color: #ffffff;
  border-right: 1px solid var(--layout-border);
}

.main-layout__header {
  padding: 0;
}

.main-layout__content {
  background-color: var(--layout-bg);
  padding: 24px;
}
</style>
