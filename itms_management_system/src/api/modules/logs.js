import request from '@/api/request'

export async function fetchAuditLogs() {
  const res = await request.get('/logs/audit')
  // res expected shape: { logs: [ {id, operator, action, target, ip, time} ] }
  return (res && res.logs) || []
}
