import json
import uuid
from django.contrib.auth.hashers import check_password
from django.core import signing
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

from .models import AdminUser, Permission, AppUser, Device, UserRole, RolePermission
from .generate_key import _generate_access_key

TOKEN_SALT = 'itms-backend-token'
TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


def _resolve_user_roles(user: AdminUser):
    """提取用户启用中的角色编码。"""
    return list(user.roles.filter(status=1).values_list('role_key', flat=True))


def _resolve_permissions(role_keys):
    if not role_keys:
        return []
    return list(
        Permission.objects.filter(roles__role_key__in=role_keys)
        .values_list('perm_key', flat=True)
        .distinct()
    )


def _build_user_payload(user: AdminUser):
    roles = _resolve_user_roles(user)
    permissions = _resolve_permissions(roles)
    display_name = user.username

    return {
        'id': user.user_id,
        'username': user.username,
        'name': display_name,
        'roles': roles,
        'permissions': permissions,
    }


def _generate_token(user: AdminUser):
    payload = {
        'user_id': user.user_id,
        'username': user.username,
        'ts': timezone.now().timestamp(),
    }
    return signing.dumps(payload, salt=TOKEN_SALT)


def _get_user_from_request(request):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header.split(' ', 1)[1].strip()
    if not token:
        return None

    try:
        payload = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None

    user_id = payload.get('user_id')
    if not user_id:
        return None

    try:
        return AdminUser.objects.get(user_id=user_id, status=1)
    except AdminUser.DoesNotExist:
        return None


def _verify_password(raw_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    
    if check_password(raw_password, hashed_password):
        return True

    # 兼容直接存储 $2b$ 开头的 bcrypt 字符串
    if hashed_password.startswith(('$2a$', '$2b$', '$2y$')):
        try:
            import bcrypt
        except ImportError:
            return False
        return bcrypt.checkpw(raw_password.encode('utf-8'), hashed_password.encode('utf-8'))

    # 开发环境兜底，避免明文调试账号无法登录
    return hashed_password == raw_password
    #return False


def dashboard_overview(request):
    """仪表盘总览统计，返回真实用户与设备数据。"""
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    total_users = AppUser.objects.count()
    online_users = AppUser.objects.filter(is_online=1).count()
    total_devices = Device.objects.count()
    # 简单把 offline 设备视为 "异常"，后续可按实际业务调整
    abnormal_devices = Device.objects.filter(online=0).count()

    overview = [
        {
            'id': 'users-total',
            'label': 'C端用户总数',
            'value': total_users,
            'unit': '人',
            'trend': '',
            'trendType': 'up',
        },
        {
            'id': 'online-users',
            'label': '当前在线用户',
            'value': online_users,
            'unit': '人',
            'trend': '',
            'trendType': 'up',
        },
        {
            'id': 'devices-total',
            'label': '设备总数',
            'value': total_devices,
            'unit': '台',
            'trend': '',
            'trendType': 'up',
        },
        {
            'id': 'abnormal-devices',
            'label': '异常设备数',
            'value': abnormal_devices,
            'unit': '台',
            'trend': '',
            'trendType': 'down',
        },
    ]

    return JsonResponse({'overview': overview})


def _write_audit_log(request, operator: str, action: str, target: str, ip=None):
    """将一条审计日志写入默认数据库中的 `audit_log` 表（MySQL）。"""
    try:
        with connection.cursor() as cur:
            # 假设 audit_log 表已经在 MySQL 中创建好
            # 使用数据库的 NOW() 函数写入时间，以保证使用数据库服务器时间戳，避免时区/服务器时间差异
            cur.execute(
                "INSERT INTO audit_log (operator, action, target, ip, time) VALUES (%s, %s, %s, %s, NOW())",
                [operator or '', action or '', target or '', ip or ''],
            )
    except Exception as e:
        # 打印错误方便排查
        print("WRITE AUDIT LOG ERROR:", e)


def list_devices(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    devices = Device.objects.select_related('owner').all()
    data = []
    for dev in devices:
        data.append({
            'id': dev.device_id,
            'name': dev.name,
            'sn': dev.sn,
            'ip': dev.ip,
            'online': bool(dev.online),
            'owner': {
                'id': dev.owner.user_id,
                'username': dev.owner.username,
            } if dev.owner else None,
        })
    return JsonResponse({'devices': data})


@csrf_exempt
def create_device(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    name = (data.get('name') or '').strip()
    sn = (data.get('sn') or '').strip()
    ip = (data.get('ip') or '').strip() or None
    online = 1 if data.get('online') in (1, '1', True, 'true', 'True') else 0
    owner_id = data.get('ownerId') or data.get('owner_id')

    if not name:
        return JsonResponse({'message': '设备名称不能为空'}, status=400)
    if not sn:
        return JsonResponse({'message': '设备序列号不能为空'}, status=400)

    owner = None
    if owner_id:
        try:
            owner = AppUser.objects.get(user_id=owner_id)
        except AppUser.DoesNotExist:
            return JsonResponse({'message': '所属用户不存在'}, status=400)

    try:
        device = Device.objects.create(
            name=name,
            sn=sn,
            ip=ip,
            owner=owner,
            online=online,
        )
    except Exception as exc:  # 简单兜底，例如唯一约束冲突
        return JsonResponse({'message': f'创建设备失败: {exc}'}, status=400)

    resp = {
        'id': device.device_id,
        'name': device.name,
        'sn': device.sn,
        'ip': device.ip,
        'online': bool(device.online),
        'owner': {
            'id': device.owner.user_id,
            'username': device.owner.username,
        } if device.owner else None,
    }
    # 记录审计日志
    try:
        operator_user = _get_user_from_request(request)
        operator = operator_user.username if operator_user else 'anonymous'
        ip = request.META.get('REMOTE_ADDR') or request.headers.get('X-Forwarded-For', '')
        target = f"DEVICE-{device.device_id} ({device.sn})"
        _write_audit_log(request, operator, '新增设备', target, ip)
    except Exception:
        pass
    return JsonResponse({'message': '设备创建成功', 'device': resp}, status=201)


def get_device_detail(request, device_id):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        device = Device.objects.select_related('owner').get(device_id=device_id)
    except Device.DoesNotExist:
        return JsonResponse({'message': '设备不存在'}, status=404)

    data = {
        'id': device.device_id,
        'name': device.name,
        'sn': device.sn,
        'ip': device.ip,
        'online': bool(device.online),
        'owner': {
            'id': device.owner.user_id,
            'username': device.owner.username,
        } if device.owner else None,
    }
    return JsonResponse({'device': data})


@csrf_exempt
def unbind_device(request, device_id):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return JsonResponse({'message': '设备不存在'}, status=404)

    device.owner = None
    device.save(update_fields=['owner'])

    # 记录审计日志
    try:
        operator_user = _get_user_from_request(request)
        operator = operator_user.username if operator_user else 'anonymous'
        ip = request.META.get('REMOTE_ADDR') or request.headers.get('X-Forwarded-For', '')
        target = f"DEVICE-{device.device_id} ({device.sn})"
        _write_audit_log(request, operator, '解除分配设备', target, ip)
    except Exception:
        pass

    return JsonResponse({'message': '设备已解除分配'})


@csrf_exempt
def assign_device(request, device_id):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    owner_id = data.get('ownerId') or data.get('owner_id')
    if not owner_id:
        return JsonResponse({'message': '所属用户ID不能为空'}, status=400)

    try:
        device = Device.objects.get(device_id=device_id)
    except Device.DoesNotExist:
        return JsonResponse({'message': '设备不存在'}, status=404)

    try:
        owner = AppUser.objects.get(user_id=owner_id)
    except AppUser.DoesNotExist:
        return JsonResponse({'message': '所属用户不存在'}, status=400)

    device.owner = owner
    device.save(update_fields=['owner'])

    data = {
        'id': device.device_id,
        'name': device.name,
        'sn': device.sn,
        'ip': device.ip,
        'online': bool(device.online),
        'owner': {
            'id': owner.user_id,
            'username': owner.username,
        },
    }
    # 记录审计日志
    try:
        operator_user = _get_user_from_request(request)
        operator = operator_user.username if operator_user else 'anonymous'
        ip = request.META.get('REMOTE_ADDR') or request.headers.get('X-Forwarded-For', '')
        target = f"DEVICE-{device.device_id} ({device.sn}) -> USER-{owner.user_id} ({owner.username})"
        _write_audit_log(request, operator, '分配设备', target, ip)
    except Exception:
        pass

    return JsonResponse({'message': '设备分配成功', 'device': data})


def _normalize_app_status(raw_status):
    """将前端状态值统一映射为 0/1。"""
    if raw_status in (1, '1', True):
        return 1
    if raw_status in (0, '0', False):
        return 0
    if isinstance(raw_status, str):
        lower = raw_status.lower()
        if lower == 'normal':
            return 1
        if lower == 'frozen':
            return 0
    return 1


def _get_user_by_credentials(username: str, password: str):
    try:
        user = AdminUser.objects.get(username=username)
    except AdminUser.DoesNotExist:
        return None, '账号或密码错误'

    if user.status != 1:
        return None, '账号已停用'

    if not _verify_password(password, user.password):
        return None, '账号或密码错误'

    return user, None


@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return JsonResponse({'message': '请输入账号和密码'}, status=400)

    user, error_message = _get_user_by_credentials(username, password)
    if user is None:
        return JsonResponse({'message': error_message}, status=401)

    token = _generate_token(user)
    user_payload = _build_user_payload(user)
    print(f"token:{token}, user_payload:{user_payload}")

    return JsonResponse({'token': token, 'user': user_payload})


def profile_view(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    user = _get_user_from_request(request)
    if user is None:
        return JsonResponse({'message': '无效或已过期的凭证'}, status=401)

    return JsonResponse(_build_user_payload(user))

@csrf_exempt
def create_user(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    username = data.get('username', '').strip()
    phone = data.get('phone', '').strip()
    role = (data.get('app_role') or data.get('role') or 'normal').strip() or 'normal'
    status_value = _normalize_app_status(data.get('status', 'normal'))
    # 创建用户由后端生成接入密钥
    access_key = _generate_access_key()

    if not username:
        return JsonResponse({'message': '用户名不能为空'}, status=400)
    if not phone:
        return JsonResponse({'message': '手机号不能为空'}, status=400)

    print(f"Creating user with username: {username}, phone: {phone}, role: {role}, status: {status_value}")

    user = AppUser.objects.create(
        username=username,
        phone=phone,
        app_role=role,
        status=status_value,
        access_key=access_key,
        is_online=0,
    )

    response_user = {
        'id': user.user_id,
        'username': user.username,
        'phone': user.phone,
        'role': user.app_role,
        'status': 'normal' if user.status == 1 else 'frozen',
        'accessKey': user.access_key,
    }
    # 记录审计日志
    try:
        operator_user = _get_user_from_request(request)
        operator = operator_user.username if operator_user else 'anonymous'
        ip = request.META.get('REMOTE_ADDR') or request.headers.get('X-Forwarded-For', '')
        target = f"USER-{user.user_id} ({user.username})"
        _write_audit_log(request, operator, '新增用户', target, ip)
    except Exception:
        pass

    return JsonResponse({'message': '用户创建成功', 'user': response_user}, status=201)

@csrf_exempt
def reset_user_key(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    try:
        user = AppUser.objects.get(user_id=user_id)
    except AppUser.DoesNotExist:
        return JsonResponse({'message': '用户不存在'}, status=404)
    
    new_access_key = _generate_access_key()
    user.access_key = new_access_key
    user.save(update_fields=['access_key'])

    print(f"用户 {user_id} 的接入密钥已重置为: {new_access_key}")

    return JsonResponse({'message': '密钥重置成功', 'accessKey': new_access_key})


def get_user(request, user_id):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        user = AppUser.objects.get(user_id=user_id)
    except AppUser.DoesNotExist:
        return JsonResponse({'message': '用户不存在'}, status=404)

    response_user = {
        'id': user.user_id,
        'username': user.username,
        'phone': user.phone,
        'email': user.email,
        'role': user.app_role,
        'status': 'normal' if user.status == 1 else 'frozen',
        'accessKey': user.access_key,
    }
    print(f"Retrieved user: {response_user}")
    return JsonResponse({'user': response_user})


@csrf_exempt
def update_user(request):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    user_id = data.get('id')
    if not user_id:
        return JsonResponse({'message': '用户ID不能为空'}, status=400)

    try:
        user = AppUser.objects.get(user_id=user_id)
    except AppUser.DoesNotExist:
        return JsonResponse({'message': '用户不存在'}, status=404)

    username = data.get('username')
    phone = data.get('phone')
    email = data.get('email')
    role = data.get('app_role') or data.get('role')
    status_value = data.get('status')
    is_online = data.get('isOnline')

    print(f"Updating user {user_id} with username: {username}, phone: {phone}, email: {email} ,role: {role}, status: {status_value}")

    if username is not None:
        user.username = username.strip()
    if phone is not None:
        user.phone = phone.strip()
    if email is not None:
        user.email = email.strip()
    if role is not None:
        user.app_role = role.strip()
    if status_value is not None:
        user.status = _normalize_app_status(status_value)
    if is_online is not None and is_online == False:
        user.is_online = 0 

    user.save()

    # 记录审计日志
    try:
        operator_user = _get_user_from_request(request)
        operator = operator_user.username if operator_user else 'anonymous'
        ip = request.META.get('REMOTE_ADDR') or request.headers.get('X-Forwarded-For', '')
        target = f"USER-{user.user_id} ({user.username})"
        _write_audit_log(request, operator, '更新用户', target, ip)
    except Exception:
        pass

    return JsonResponse({'message': '用户更新成功'})


def list_users(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    users = AppUser.objects.all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.user_id,
            'username': user.username,
            'phone': user.phone,
            'email': user.email,
            'role': user.app_role,
            'status': 'normal' if user.status == 1 else 'frozen',
            'accessKey': user.access_key,
            'isOnline': user.is_online
        })

    return JsonResponse({'users': user_list})

def query_users(request):
    """条件分页查询C端用户"""
    # 获取查询参数
    phone = request.GET.get('phone', '').strip()
    email = request.GET.get('email', '').strip()
    page_num = request.GET.get('pageNum', '1')
    page_size = request.GET.get('pageSize', '10')

    # 转换分页参数
    try:
        page_num = int(page_num)
        page_size = int(page_size)
    except ValueError:
        page_num = 1
        page_size = 10

    # 确保分页参数合法
    if page_num < 1:
        page_num = 1
    if page_size < 1:
        page_size = 10
    if page_size > 100:  # 限制最大每页条数
        page_size = 100

    # 构建查询条件
    queryset = AppUser.objects.all()

    if phone:
        queryset = queryset.filter(phone__icontains=phone)
    if email:
        queryset = queryset.filter(email__icontains=email)

    # 获取总数
    total = queryset.count()

    # 分页
    start = (page_num - 1) * page_size
    end = start + page_size
    users = queryset.order_by('-user_id')[start:end]

    # 构建响应数据
    user_list = []
    for user in users:
        user_list.append({
            'id': user.user_id,
            'username': user.username,
            'phone': user.phone,
            'email': user.email,
            'role': user.app_role,
            'status': 'normal' if user.status == 1 else 'frozen',
            'accessKey': user.access_key,
        })

    return JsonResponse({
        'users': user_list,
        'total': total,
        'pageNum': page_num,
        'pageSize': page_size,
    })

@csrf_exempt
def update_user_isOnline(request, user_id):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    is_online = data.get('isOnline')

    if not user_id:
        return JsonResponse({'message': '用户ID不能为空'}, status=400)
    if is_online is None:
        return JsonResponse({'message': '状态值不能为空'}, status=400)

    try:
        user = AppUser.objects.get(user_id=user_id)
    except AppUser.DoesNotExist:
        return JsonResponse({'message': '用户不存在'}, status=404)

    user.is_online = 0
    user.save()

    # 记录审计日志（强制下线或状态更新）
    try:
        operator_user = _get_user_from_request(request)
        operator = operator_user.username if operator_user else 'anonymous'
        ip = request.META.get('REMOTE_ADDR') or request.headers.get('X-Forwarded-For', '')
        target = f"USER-{user.user_id} ({user.username})"
        _write_audit_log(request, operator, '更新用户状态', target, ip)
    except Exception:
        pass

    return JsonResponse({'message': '用户状态更新成功'})


@csrf_exempt
def assign_devices_to_user(request, user_id):
    """为指定 C 端用户分配设备列表。"""
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    device_ids = data.get('deviceIds') or data.get('device_ids') or []
    if not isinstance(device_ids, list):
        return JsonResponse({'message': 'deviceIds 必须是数组'}, status=400)

    try:
        user = AppUser.objects.get(user_id=user_id)
    except AppUser.DoesNotExist:
        return JsonResponse({'message': '用户不存在'}, status=404)

    # 先解绑该用户当前所有设备，再按列表重新分配
    Device.objects.filter(owner=user).update(owner=None)
    if device_ids:
        Device.objects.filter(device_id__in=device_ids).update(owner=user)

    # 审计日志
    try:
        operator_user = _get_user_from_request(request)
        operator = operator_user.username if operator_user else 'anonymous'
        ip = request.META.get('REMOTE_ADDR') or request.headers.get('X-Forwarded-For', '')
        target = f"USER-{user.user_id} ({user.username}) <- DEVICES: {device_ids}"
        _write_audit_log(request, operator, '为用户分配设备', target, ip)
    except Exception:
        pass

    return JsonResponse({'message': '分配设备成功'})


@csrf_exempt
def users_view(request):
    if request.method == 'GET':
        return query_users(request)
    if request.method == 'POST':
        return create_user(request)
    if request.method == 'PUT':
        return update_user(request)
    return JsonResponse({'message': 'Method not allowed'}, status=405)


def audit_logs(request):
    """返回最近的审计日志记录（从 sqlite 的 audit_log 表读取）。"""
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    logs = []
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT id, operator, action, target, ip, time FROM audit_log ORDER BY id DESC LIMIT 200')
            rows = cur.fetchall()
            for row in rows:
                _id, operator, action, target, ip, time_str = row
                logs.append({
                    'id': _id,
                    'operator': operator,
                    'action': action,
                    'target': target,
                    'ip': ip,
                    'time': time_str,
                })
    except Exception:
        # 表不存在或查询失败时返回空数组
        logs = []

    return JsonResponse({'logs': logs})

@csrf_exempt
def list_roles(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    roles = UserRole.objects.all()
    role_list = []
    for role in roles:
        role_list.append({
            'role_id': role.role_id,
            'role_name': role.role_name,
            'role_key': role.role_key,
        })
    print(f"Retrieved roles: {role_list}")

    return JsonResponse({'roles': role_list})


@csrf_exempt
def list_admins(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    admins = AdminUser.objects.all()
    admin_list = []
    for admin in admins:
        admin_list.append({
            'user_id': admin.user_id,
            'username': admin.username,
            'roles': list(admin.roles.filter(status=1).values_list('role_key', flat=True)),
            'status': 'normal' if admin.status == 1 else 'frozen',
            'create_time': admin.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'phone': admin.phone,
            'email': admin.email,
        })
    print(f"Retrieved admins: {admin_list}")

    return JsonResponse({'admins': admin_list})

@csrf_exempt
def admin_permissions(request, user_id):
    # GET: 查询权限列表
    if request.method == 'GET':
        try:
            admin = AdminUser.objects.get(user_id=user_id)
        except AdminUser.DoesNotExist:
            return JsonResponse({'message': '管理员不存在'}, status=404)

        roles = admin.roles.filter(status=1).values_list('role_key', flat=True)
        permissions = Permission.objects.filter(roles__role_key__in=roles).distinct()
        permission_list = []
        for perm in permissions:
            permission_list.append({
                'perm_key': perm.perm_key,
            })
        print(f"Permissions for admin {user_id}: {permission_list}")

        return JsonResponse({'permissions': permission_list})

    # PUT: 修改管理员权限
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

        # 权限列表
        perm_keys = data.get('permissions')
        print(f"perm_keys:{perm_keys}")
        # 获取对应权限列表的id
        permission_ids = Permission.objects.filter(perm_key__in=perm_keys).values_list('id', flat=True)

        # 删除当前管理员所关联的所有权限
        # 1.先查询当前管理员对应的角色ID
        role_ids = UserRole.objects.filter(user_id=user_id).values_list('role_id', flat=True)
        # 2.删除这些角色对应的权限关联
        RolePermission.objects.filter(role_id__in=role_ids).delete()
        # 3.重新添加新的权限关联
        for role_id in role_ids:
            for permission_id in permission_ids:
                RolePermission.objects.create(role_id=role_id, permission_id=permission_id)
                print(f"Assigned permission ID {permission_id} to role ID {role_id} for admin user ID {user_id}")

        return JsonResponse({'message': '管理员权限更新成功'})

    else:
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
@csrf_exempt
def admins_view(request):
    if request.method == 'GET':
        return query_admins(request)
    if request.method == 'POST':
        return create_admin(request)
    if request.method == 'PUT':
        return update_admin(request)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

@csrf_exempt
def query_admins(request): 
    pass

@csrf_exempt
def create_admin(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    phone = data.get('phone', '').strip()
    email = data.get('email', '').strip()
    create_time = timezone.now()

    if not username:
        return JsonResponse({'message': '用户名不能为空'}, status=400)
    if not password:
        return JsonResponse({'message': '密码不能为空'}, status=400)
    # 创建管理员用户，返回新用户ID
    admin_user = AdminUser.objects.create(
        username=username,
        password=password,
        status=1,
        create_time=create_time,
        phone=phone,
        email=email
    )

    # 关联默认角色
    UserRole.objects.create(
        user_id=admin_user.user_id,
        role_id=2 # 默认为普通管理员
    )
    
    return JsonResponse({'message': '管理员创建成功'}, status=201)

@csrf_exempt
def update_admin(request):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    user_id = data.get('user_id')
    if not user_id:
        return JsonResponse({'message': '用户ID不能为空'}, status=400)

    try:
        admin_user = AdminUser.objects.get(user_id=user_id)
    except AdminUser.DoesNotExist:
        return JsonResponse({'message': '管理员不存在'}, status=404)

    username = data.get('username')
    password = data.get('password')
    status_value = data.get('status')
    phone = data.get('phone')
    email = data.get('email')

    if username is not None:
        admin_user.username = username.strip()
    if password is not None:
        admin_user.password = password.strip()
    if status_value is not None:
        admin_user.status = 1 if status_value == 'normal' else 0
    if phone is not None:
        admin_user.phone = phone.strip()
    if email is not None:
        admin_user.email = email.strip()

    admin_user.save()

    return JsonResponse({'message': '管理员更新成功'})

@csrf_exempt
def delete_admin(request, user_id):
    if request.method != 'DELETE':
        return JsonResponse({'message': 'Method not allowed'}, status=405)
    
    try:
        admin_user = AdminUser.objects.get(user_id=user_id)
    except AdminUser.DoesNotExist:
        return JsonResponse({'message': '管理员不存在'}, status=404)
    
    admin_user.delete()
    UserRole.objects.filter(user_id=user_id).delete()

    return JsonResponse({'message': '管理员删除成功'})

"""
    修改管理员账号状态接口
"""
@csrf_exempt
def update_admin_status(request, user_id):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    status_value = data.get('status')

    if not user_id:
        return JsonResponse({'message': '用户ID不能为空'}, status=400)
    if status_value is None:
        return JsonResponse({'message': '状态值不能为空'}, status=400)

    try:
        admin_user = AdminUser.objects.get(user_id=user_id)
    except AdminUser.DoesNotExist:
        return JsonResponse({'message': '管理员不存在'}, status=404)

    admin_user.status = 1 if status_value else 0
    admin_user.save()

    return JsonResponse({'message': '管理员状态更新成功'})