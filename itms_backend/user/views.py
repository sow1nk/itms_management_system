import json
import uuid
from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import connection, transaction
from django.db.models import Q

from .models import AdminUser, Permission, AppUser, Device, UserRole, RolePermission, Role
from .generate_key import _generate_access_key

TOKEN_SALT = 'itms-backend-token'
TOKEN_MAX_AGE = 7 * 24 * 60 * 60  # 7 days
DEFAULT_PASSWORD = '123456'


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


def _normalize_status_value(raw_value, default=1):
    """将各种输入统一转换为 0/1 状态值。"""
    if raw_value is None:
        return default

    if isinstance(raw_value, bool):
        return 1 if raw_value else 0

    if isinstance(raw_value, int):
        return 1 if raw_value != 0 else 0

    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered in {'1', 'true', 'enabled', 'enable', 'active', 'on', 'normal'}:
            return 1
        if lowered in {'0', 'false', 'disabled', 'disable', 'inactive', 'off', 'forbidden'}:
            return 0

    return default


def _resolve_roles_from_payload(data, *, required=True, allow_default=False):
    """根据请求体解析角色列表，支持 role_ids / roles (ID) 或 role_keys。"""
    raw_role_ids = data.get('roles')
    if raw_role_ids is None:
        raw_role_ids = data.get('role_ids')
    raw_role_keys = data.get('role_keys')

    if raw_role_ids is not None:
        if not isinstance(raw_role_ids, list):
            return None, JsonResponse({'message': 'roles 必须是数组'}, status=400)
        normalized_ids = []
        for value in raw_role_ids:
            if value in (None, ''):
                continue
            try:
                normalized_ids.append(int(value))
            except (TypeError, ValueError):
                return None, JsonResponse({'message': '角色ID必须是整数'}, status=400)
        if not normalized_ids:
            if required:
                return None, JsonResponse({'message': '请至少选择一个角色'}, status=400)
            return [], None

        roles = list(Role.objects.filter(role_id__in=normalized_ids, status=1))
        found_ids = {role.role_id for role in roles}
        missing_ids = [role_id for role_id in normalized_ids if role_id not in found_ids]
        if missing_ids:
            return None, JsonResponse({'message': f'角色不存在或已禁用: {missing_ids}'}, status=400)
        return roles, None

    if raw_role_keys is not None:
        if not isinstance(raw_role_keys, list):
            return None, JsonResponse({'message': 'role_keys 必须是数组'}, status=400)
        normalized_keys = [str(value).strip() for value in raw_role_keys if value]
        if not normalized_keys:
            if required:
                return None, JsonResponse({'message': '请至少选择一个角色'}, status=400)
            return [], None
        roles = list(Role.objects.filter(role_key__in=normalized_keys, status=1))
        found_keys = {role.role_key for role in roles}
        missing_keys = [key for key in normalized_keys if key not in found_keys]
        if missing_keys:
            missing_text = ", ".join(missing_keys)
            return None, JsonResponse({'message': f'角色不存在或已禁用: {missing_text}'}, status=400)
        return roles, None

    if allow_default:
        default_role = Role.objects.filter(role_key='admin', status=1).first()
        if not default_role:
            default_role = Role.objects.filter(status=1).first()
        if default_role:
            return [default_role], None

    if required:
        return None, JsonResponse({'message': '请至少选择一个角色'}, status=400)
    return [], None


def _parse_pagination_params(request, default_page=1, default_size=10, max_size=200):
    """解析分页参数，支持 page/page_size 或 page/pageSize。"""
    try:
        page = int(request.GET.get('page', default_page))
    except (TypeError, ValueError):
        page = default_page
    if page < 1:
        page = 1

    size_param = request.GET.get('page_size')
    if size_param is None:
        size_param = request.GET.get('pageSize')
    try:
        page_size = int(size_param or default_size)
    except (TypeError, ValueError):
        page_size = default_size

    if page_size < 1:
        page_size = 1

    if max_size and page_size > max_size:
        page_size = max_size

    return page, page_size


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

    # 不支持的密码格式
    return False


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
    username = request.GET.get('username', '').strip()
    role = (request.GET.get('role') or request.GET.get('app_role') or '').strip()
    online_status = (request.GET.get('onlineStatus') or '').strip().lower()
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
    if username:
        queryset = queryset.filter(username__icontains=username)
    if role:
        queryset = queryset.filter(app_role=role)
    if online_status == 'online':
        queryset = queryset.filter(is_online=1)
    elif online_status == 'offline':
        queryset = queryset.filter(is_online=0)

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

    keyword = (request.GET.get('keyword') or '').strip()
    role_name_param = (request.GET.get('role_name') or request.GET.get('roleName') or '').strip()
    role_key_param = (request.GET.get('role_key') or request.GET.get('roleKey') or '').strip()
    page, page_size = _parse_pagination_params(request)

    roles_qs = Role.objects.all().order_by('role_id')
    if role_name_param:
        roles_qs = roles_qs.filter(role_name__icontains=role_name_param)
    if role_key_param:
        roles_qs = roles_qs.filter(role_key__icontains=role_key_param)
    if keyword and not (role_name_param or role_key_param):
        roles_qs = roles_qs.filter(
            Q(role_name__icontains=keyword) | Q(role_key__icontains=keyword)
        )

    total = roles_qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    roles = roles_qs[start:end]

    role_list = []
    for role in roles:
        role_list.append({
            'role_id': role.role_id,
            'role_name': role.role_name,
            'role_key': role.role_key,
            'status': 1 if role.status else 0,
        })
    return JsonResponse({
        'roles': role_list,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
        }
    })


@csrf_exempt
def roles_view(request):
    if request.method == 'GET':
        return list_roles(request)
    if request.method == 'POST':
        return create_role(request)
    if request.method == 'PUT':
        return update_role(request)
    return JsonResponse({'message': 'Method not allowed'}, status=405)


@csrf_exempt
def create_role(request):
    if request.method != 'POST':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    role_name = (data.get('role_name') or '').strip()
    role_key = (data.get('role_key') or '').strip()
    status_value = _normalize_status_value(data.get('status'), 1)

    if not role_name:
        return JsonResponse({'message': '角色名称不能为空'}, status=400)
    if not role_key:
        return JsonResponse({'message': '角色标识不能为空'}, status=400)

    if Role.objects.filter(role_key=role_key).exists():
        return JsonResponse({'message': '角色标识已存在'}, status=400)

    role = Role.objects.create(
        role_name=role_name,
        role_key=role_key,
        status=status_value,
    )

    return JsonResponse({
        'message': '角色创建成功',
        'role': {
            'role_id': role.role_id,
            'role_name': role.role_name,
            'role_key': role.role_key,
            'status': role.status,
        }
    }, status=201)


@csrf_exempt
def update_role(request):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

    role_id = data.get('role_id')
    if not role_id:
        return JsonResponse({'message': '角色ID不能为空'}, status=400)

    try:
        role = Role.objects.get(role_id=role_id)
    except Role.DoesNotExist:
        return JsonResponse({'message': '角色不存在'}, status=404)

    role_name = data.get('role_name')
    role_key = data.get('role_key')
    status_value = data.get('status')

    if role_name is not None:
        role_name = role_name.strip()
        if not role_name:
            return JsonResponse({'message': '角色名称不能为空'}, status=400)
        role.role_name = role_name

    if role_key is not None:
        role_key = role_key.strip()
        if not role_key:
            return JsonResponse({'message': '角色标识不能为空'}, status=400)
        if Role.objects.filter(role_key=role_key).exclude(role_id=role_id).exists():
            return JsonResponse({'message': '角色标识已存在'}, status=400)
        role.role_key = role_key

    if status_value is not None:
        role.status = _normalize_status_value(status_value, role.status)

    role.save()

    return JsonResponse({
        'message': '角色更新成功',
        'role': {
            'role_id': role.role_id,
            'role_name': role.role_name,
            'role_key': role.role_key,
            'status': role.status,
        }
    })


@csrf_exempt
def role_detail(request, role_id):
    try:
        role = Role.objects.get(role_id=role_id)
    except Role.DoesNotExist:
        return JsonResponse({'message': '角色不存在'}, status=404)

    if request.method == 'GET':
        return JsonResponse({
            'role': {
                'role_id': role.role_id,
                'role_name': role.role_name,
                'role_key': role.role_key,
                'status': 1 if role.status else 0,
            }
        })

    if request.method == 'DELETE':
        RolePermission.objects.filter(role_id=role_id).delete()
        UserRole.objects.filter(role_id=role_id).delete()
        role.delete()
        return JsonResponse({'message': '角色删除成功'})

    return JsonResponse({'message': 'Method not allowed'}, status=405)


@csrf_exempt
def role_permissions(request, role_id):
    try:
        role = Role.objects.get(role_id=role_id)
    except Role.DoesNotExist:
        return JsonResponse({'message': '角色不存在'}, status=404)

    if request.method == 'GET':
        permissions = Permission.objects.filter(roles__role_id=role_id).distinct()
        permission_list = [{'perm_key': perm.perm_key} for perm in permissions]
        return JsonResponse({'permissions': permission_list})

    if request.method == 'PUT':
        try:
            data = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)

        perm_keys = data.get('permissions', [])
        if perm_keys is None:
            perm_keys = []
        if not isinstance(perm_keys, list):
            return JsonResponse({'message': '权限列表必须是数组'}, status=400)

        normalized_keys = []
        for key in perm_keys:
            if not key:
                continue
            normalized_keys.append(str(key).strip())

        permissions = list(Permission.objects.filter(perm_key__in=normalized_keys))
        found_keys = {perm.perm_key for perm in permissions}
        missing_keys = [key for key in normalized_keys if key not in found_keys]
        if missing_keys:
            return JsonResponse({'message': f'权限不存在: {", ".join(missing_keys)}'}, status=400)

        RolePermission.objects.filter(role_id=role_id).delete()
        RolePermission.objects.bulk_create([
            RolePermission(role=role, permission=perm)
            for perm in permissions
        ])

        return JsonResponse({'message': '角色权限更新成功'})

    return JsonResponse({'message': 'Method not allowed'}, status=405)


@csrf_exempt
def list_admins(request):
    if request.method != 'GET':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    phone = (request.GET.get('phone') or '').strip()
    email = (request.GET.get('email') or '').strip()
    keyword = (request.GET.get('keyword') or '').strip()
    role_key = (request.GET.get('role_key') or request.GET.get('roleKey') or '').strip()
    page, page_size = _parse_pagination_params(request)

    admins_qs = AdminUser.objects.all().order_by('user_id')
    if phone:
        admins_qs = admins_qs.filter(phone__icontains=phone)
    if email:
        admins_qs = admins_qs.filter(email__icontains=email)
    if keyword and not (phone or email):
        admins_qs = admins_qs.filter(
            Q(phone__icontains=keyword)
            | Q(email__icontains=keyword)
            | Q(username__icontains=keyword)
        )
    if role_key:
        admins_qs = admins_qs.filter(roles__role_key=role_key)

    admins_qs = admins_qs.distinct()
    total = admins_qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    admins = admins_qs[start:end]

    admin_list = []
    for admin in admins:
        roles_qs = admin.roles.filter(status=1)
        role_list = []
        for role in roles_qs:
            role_list.append({
                'role_id': role.role_id,
                'role_name': role.role_name,
                'role_key': role.role_key,
            })

        admin_list.append({
            'user_id': admin.user_id,
            'username': admin.username,
            'roles': [item['role_key'] for item in role_list],
            'role_list': role_list,
            'status': 'normal' if admin.status == 1 else 'frozen',
            'create_time': admin.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'phone': admin.phone,
            'email': admin.email,
        })
    print(f"Retrieved admins: {admin_list}")

    return JsonResponse({
        'admins': admin_list,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
        }
    })

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

    else:
        return JsonResponse({'message': '请在角色管理模块中分配权限'}, status=405)
    
@csrf_exempt
def admins_view(request):
    if request.method == 'GET':
        return query_admins(request)
    if request.method == 'POST':
        return create_admin(request)
    if request.method == 'PUT':
        return update_admin(request)
    return JsonResponse({'message': 'Method not allowed'}, status=405)

# TODO: 实现管理员查询接口
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

    if not username:
        return JsonResponse({'message': '用户名不能为空'}, status=400)
    if not password:
        return JsonResponse({'message': '密码不能为空'}, status=400)

    # 加密密码
    hashed_password = make_password(password)

    roles, error_response = _resolve_roles_from_payload(data, required=True, allow_default=True)
    if error_response:
        return error_response

    with transaction.atomic():
        admin_user = AdminUser.objects.create(
            username=username,
            password=hashed_password,
            status=1,
            create_time=timezone.now(),
            phone=phone,
            email=email
        )

        UserRole.objects.bulk_create(
            [UserRole(user=admin_user, role=role) for role in roles],
            ignore_conflicts=True,
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

    roles_payload_present = any(key in data for key in ('roles', 'role_ids', 'role_keys'))
    new_roles = None
    if roles_payload_present:
        new_roles, error_response = _resolve_roles_from_payload(data, required=True, allow_default=False)
        if error_response:
            return error_response

    with transaction.atomic():
        if username is not None:
            admin_user.username = username.strip()
        if password is not None:
            # 加密密码后存储
            admin_user.password = make_password(password.strip())
        if status_value is not None:
            admin_user.status = 1 if status_value == 'normal' else 0
        if phone is not None:
            admin_user.phone = phone.strip()
        if email is not None:
            admin_user.email = email.strip()
        admin_user.save()

        if new_roles is not None:
            UserRole.objects.filter(user=admin_user).delete()
            UserRole.objects.bulk_create(
                [UserRole(user=admin_user, role=role) for role in new_roles],
                ignore_conflicts=True,
            )

    return JsonResponse({'message': '管理员更新成功'})

@csrf_exempt
def reset_admin_password(request, user_id):
    if request.method != 'PUT':
        return JsonResponse({'message': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'message': '请求体必须是合法的 JSON'}, status=400)
    
    try:
        admin_user = AdminUser.objects.get(user_id=user_id)
    except AdminUser.DoesNotExist:
        return JsonResponse({'message': '管理员不存在'}, status=404)

    # 重置密码默认为123456（加密存储）
    admin_user.password = make_password(DEFAULT_PASSWORD)
    admin_user.save()

    return JsonResponse({'message': '密码重置成功'}, status=200)

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
