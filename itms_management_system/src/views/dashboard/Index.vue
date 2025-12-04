<script setup>
import { ref, onMounted } from 'vue'
import { fetchDashboardOverview, fetchDashboardTrends } from '@/api/modules/dashboard'

const loading = ref(false)
const overviewCards = ref([])
const trendData = ref([])

const loadData = async () => {
  loading.value = true
  try {
    const [overview, trend] = await Promise.all([fetchDashboardOverview(), fetchDashboardTrends()])
    overviewCards.value = overview
    trendData.value = trend
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<template>
  <div class="dashboard" v-loading="loading">
    <div class="dashboard__cards">
      <el-card v-for="card in overviewCards" :key="card.id" shadow="hover" class="dashboard__card">
        <p class="dashboard__label">{{ card.label }}</p>
        <div class="dashboard__value">
          {{ card.value }}<small>{{ card.unit }}</small>
        </div>
        <span class="dashboard__trend" :class="[`dashboard__trend--${card.trendType}`]">{{ card.trend }}</span>
      </el-card>
    </div>
    <el-card shadow="never" class="dashboard__chart">
      <div class="dashboard__chart-header">
        <div>
          <p class="dashboard__chart-title">实时数据看板</p>
          <p class="dashboard__chart-desc">展示在线人数趋势及告警数（示例数据，可接入真实接口）</p>
        </div>
      </div>
      <div class="dashboard__chart-placeholder">
        <div v-for="item in trendData" :key="item.time" class="dashboard__chart-row">
          <div class="dashboard__chart-time">{{ item.time }}</div>
          <div class="dashboard__chart-bar">
            <div class="dashboard__chart-fill" :style="{ width: `${item.onlinePercent}%` }"></div>
          </div>
          <div class="dashboard__chart-info">{{ item.onlineUsers }} 人在线 ｜ 告警 {{ item.warnings }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dashboard__cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.dashboard__card {
  border-radius: 16px;
}

.dashboard__label {
  color: var(--text-secondary);
  font-size: 14px;
}

.dashboard__value {
  font-size: 32px;
  font-weight: 600;
  margin: 8px 0;
  color: var(--text-primary);
}

.dashboard__value small {
  font-size: 16px;
  margin-left: 4px;
  color: var(--text-secondary);
}

.dashboard__trend {
  font-size: 14px;
}

.dashboard__trend--up {
  color: #67c23a;
}

.dashboard__trend--down {
  color: #f56c6c;
}

.dashboard__chart {
  border-radius: 16px;
}

.dashboard__chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.dashboard__chart-title {
  font-weight: 600;
  color: var(--text-primary);
}

.dashboard__chart-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.dashboard__chart-placeholder {
  border: 1px dashed var(--layout-border);
  border-radius: 12px;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 240px;
}

.dashboard__chart-row {
  display: grid;
  grid-template-columns: 80px 1fr 160px;
  gap: 16px;
  align-items: center;
}

.dashboard__chart-time {
  font-weight: 500;
  color: var(--text-primary);
}

.dashboard__chart-bar {
  height: 8px;
  border-radius: 8px;
  background: #f5f7fa;
  overflow: hidden;
}

.dashboard__chart-fill {
  height: 100%;
  border-radius: 8px;
  background: linear-gradient(90deg, #409eff, #1677ff);
}

.dashboard__chart-info {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
