<script setup>
import { computed } from 'vue'

defineOptions({ name: 'SidebarItem' })

const props = defineProps({
  item: {
    type: Object,
    required: true,
  },
  basePath: {
    type: String,
    default: '',
  },
})

const visibleChildren = computed(() => (props.item.children || []).filter((child) => !child.meta?.hidden))
const hasChildren = computed(() => visibleChildren.value.length > 0)

const resolvePath = (route) => {
  if (route.path.startsWith('/')) {
    return route.path
  }
  const base = props.basePath || ''
  const combined = base ? `${base}/${route.path}` : route.path
  return combined.replace(/\/+/g, '/')
}
</script>

<template>
  <template v-if="!props.item.meta?.hidden">
    <el-sub-menu v-if="hasChildren" :index="resolvePath(props.item)">
      <template #title>
        <el-icon v-if="props.item.meta?.icon">
          <component :is="props.item.meta.icon" />
        </el-icon>
        <span>{{ props.item.meta?.title }}</span>
      </template>
      <sidebar-item
        v-for="child in visibleChildren"
        :key="child.path"
        :item="child"
        :base-path="resolvePath(props.item)"
      />
    </el-sub-menu>
    <el-menu-item v-else :index="resolvePath(props.item)">
      <el-icon v-if="props.item.meta?.icon">
        <component :is="props.item.meta.icon" />
      </el-icon>
      <template #title>
        <span>{{ props.item.meta?.title }}</span>
      </template>
    </el-menu-item>
  </template>
</template>
