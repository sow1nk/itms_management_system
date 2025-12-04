import request from '@/api/request'

export function fetchDeviceList() {
  return request.get('/devices/list').then((res) => {
    const list = Array.isArray(res) ? res : res?.devices || []
    return list.map((item) => ({
      id: item.id,
      name: item.name,
      sn: item.sn,
      ip: item.ip,
      online: !!item.online,
      owner: item.owner ? { ...item.owner } : null,
    }))
  })
}

export function createDevice(data) {
  return request.post('/devices', data)
}

export function unbindDevice(deviceId) {
  return request.put(`/devices/unbind/${deviceId}`)
}

export function fetchDeviceDetail(deviceId) {
  return request.get(`/devices/${deviceId}`)
}

export function assignDevice(deviceId, ownerId) {
  return request.put(`/devices/assign/${deviceId}`, { ownerId })
}
