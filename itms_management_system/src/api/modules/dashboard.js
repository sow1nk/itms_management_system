import request from '@/api/request'

export function fetchDashboardOverview() {
  return request.get('/dashboard/overview').then((res) => {
    return Array.isArray(res) ? res : res?.overview || []
  })
}

// 目前趋势图仍使用 mock 数据，可后续接入真实接口
const trendMock = [
  { time: '08:00', onlineUsers: 940, warnings: 2, onlinePercent: 72 },
  { time: '12:00', onlineUsers: 1110, warnings: 1, onlinePercent: 84 },
  { time: '16:00', onlineUsers: 980, warnings: 3, onlinePercent: 76 },
]

export function fetchDashboardTrends() {
  return Promise.resolve(trendMock)
}
