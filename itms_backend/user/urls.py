# user/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('auth/login', views.login_view, name='login'),
    path('auth/profile', views.profile_view, name='profile'),
    # 新增/更新C端用户 条件分页查询C端用户
    path('users', views.users_view, name='users'),
    # 重置C端用户接入密钥
    path('users/key/reset/<int:user_id>', views.reset_user_key, name='reset_user_key'),
    # 根据ID获取C端用户
    path('users/<int:user_id>', views.get_user, name='get_user'),
    # 查询所有C端用户
    path('users/list', views.list_users, name='list_users'),
    # 将C端用户强制下线 / 更新用户在线状态
    path('users/status/<int:user_id>', views.update_user_isOnline, name='update_user_isOnline'),
    # 为用户分配设备
    path('users/devices/assign/<int:user_id>', views.assign_devices_to_user, name='assign_devices_to_user'),
    # 仪表盘统计
    path('dashboard/overview', views.dashboard_overview, name='dashboard_overview'),
    # 审计日志
    path('logs/audit', views.audit_logs, name='audit_logs'),
    # 查询所有设备
    path('devices/list', views.list_devices, name='list_devices'),
    # 设备详情 / 新增 / 解绑
    path('devices', views.create_device, name='create_device'),
    path('devices/<int:device_id>', views.get_device_detail, name='device_detail'),
    path('devices/unbind/<int:device_id>', views.unbind_device, name='unbind_device'),
    path('devices/assign/<int:device_id>', views.assign_device, name='assign_device'),
    # 查询所有角色
    path('roles/list', views.list_roles, name='list_roles'),
    # 查询所有管理员
    path('admins/list', views.list_admins, name='list_admins'),
    # 查询/修改管理员权限
    path('admins/<int:user_id>/permissions', views.admin_permissions, name='admin_permissions'),
    # 新增/更新管理员 条件分页查询管理员
    path('admins', views.admins_view, name='admins'),
    # 删除管理员
    path('admins/<int:user_id>', views.delete_admin, name='delete_admin'),
    # 更新管理员账号状态
    path('admins/status/<int:user_id>', views.update_admin_status, name='update_admin_status'),
]
