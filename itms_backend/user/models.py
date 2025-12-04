from django.db import models

class Permission(models.Model):
    """与 MySQL permission 表一致，仅存储权限标识。"""

    id = models.BigAutoField(primary_key=True)
    perm_key = models.CharField(max_length=50, unique=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = 'permission'
        managed = False
        verbose_name = '权限'
        verbose_name_plural = '权限'

    def __str__(self):
        return self.perm_key


class Role(models.Model):
    """角色表，关联多条权限，并可与管理员建立多对多关系。"""

    role_id = models.BigAutoField(primary_key=True)
    role_name = models.CharField(max_length=50)
    role_key = models.CharField(max_length=50, unique=True)
    status = models.SmallIntegerField(default=1)
    permissions = models.ManyToManyField(
        'Permission',
        through='RolePermission',
        related_name='roles',
        blank=True,
    )

    class Meta:
        db_table = 'role'
        managed = False
        verbose_name = '角色'
        verbose_name_plural = '角色'

    def __str__(self):
        return self.role_key


class AdminUser(models.Model):
    """后台管理员，对应 MySQL user 表。"""

    user_id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=100)
    status = models.SmallIntegerField(default=1)
    create_time = models.DateTimeField(auto_now_add=True)
    roles = models.ManyToManyField(
        Role,
        through='UserRole',
        related_name='users',
        blank=True,
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = 'user'
        managed = False
        verbose_name = '管理员'
        verbose_name_plural = '管理员'

    def __str__(self):
        return self.username


class UserRole(models.Model):
    """用户与角色的映射表。"""

    user = models.ForeignKey(AdminUser, db_column='user_id', on_delete=models.CASCADE)
    role = models.ForeignKey(Role, db_column='role_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_role'
        managed = False
        unique_together = ('user', 'role')
        verbose_name = '用户角色'
        verbose_name_plural = '用户角色'

    def __str__(self):
        return f'{self.user_id}-{self.role_id}'


class RolePermission(models.Model):
    """角色与权限的映射表。"""

    role = models.ForeignKey(Role, db_column='role_id', on_delete=models.CASCADE)
    permission = models.ForeignKey(Permission, db_column='permission_id', on_delete=models.CASCADE)

    class Meta:
        db_table = 'role_permission'
        managed = False
        unique_together = ('role', 'permission')
        verbose_name = '角色权限'
        verbose_name_plural = '角色权限'

    def __str__(self):
        return f'{self.role_id}-{self.permission_id}'


class AppUser(models.Model):
    """C端用户表。"""

    user_id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=50, blank=True, null=True)
    access_key = models.CharField(max_length=64, unique=True)
    app_role = models.CharField(max_length=20, default='normal')
    status = models.SmallIntegerField(default=1)  # 0-冻结, 1-正常
    is_online = models.SmallIntegerField(default=0) # 0-离线, 1-在线

    
    class Meta:
        db_table = 'client_user'
        managed = False
        verbose_name = 'C端用户'
        verbose_name_plural = 'C端用户'

    def __str__(self):
        return f'{self.user_id}-{self.username}'
    

class Device(models.Model):
    device_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    sn = models.CharField(max_length=64, unique=True)
    ip = models.CharField(max_length=45, blank=True, null=True)
    owner = models.ForeignKey(
        AppUser,
        db_column='owner_id',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='devices',
    )
    online = models.SmallIntegerField(default=0)

    class Meta:
        db_table = 'device'
        managed = False
        verbose_name = '设备'
        verbose_name_plural = '设备'

    def __str__(self):
        return f'{self.device_id}-{self.name}'