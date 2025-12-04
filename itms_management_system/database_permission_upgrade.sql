-- ====================================================================
-- 权限表数据升级 SQL 脚本（混合模式 - 推荐）
-- 保留现有粗粒度权限 + 新增细粒度权限
-- ====================================================================

-- 说明：
-- 1. 保留现有的 4 条粗粒度权限作为"父权限"
-- 2. 添加所有细粒度权限作为"子权限"
-- 3. 前端会自动处理：拥有 user:manage 自动拥有所有 user:manage:* 权限
-- 4. 可选：添加 parent_id 字段建立父子关系

-- ====================================================================
-- 步骤1：优化表结构（可选但推荐）
-- ====================================================================

-- 添加 parent_id 字段，建立权限层级关系
ALTER TABLE permission
ADD COLUMN parent_id INT DEFAULT NULL COMMENT '父权限ID' AFTER perm_key;

-- 添加描述字段
ALTER TABLE permission
ADD COLUMN description VARCHAR(255) DEFAULT NULL COMMENT '权限描述' AFTER parent_id;

-- 添加排序字段
ALTER TABLE permission
ADD COLUMN sort_order INT DEFAULT 0 COMMENT '排序' AFTER description;

-- ====================================================================
-- 步骤2：更新现有数据，添加描述
-- ====================================================================

UPDATE permission SET description = 'C端用户管理（所有权限）', sort_order = 1 WHERE id = 1;
UPDATE permission SET description = '设备管理（所有权限）', sort_order = 2 WHERE id = 2;
UPDATE permission SET description = '审计日志（所有权限）', sort_order = 3 WHERE id = 3;
UPDATE permission SET description = '系统管理（所有权限）', sort_order = 4 WHERE id = 4;

-- ====================================================================
-- 步骤3：插入细粒度权限（子权限）
-- ====================================================================

-- -------------------- C端用户管理子权限（parent_id = 1）--------------------
INSERT INTO permission (perm_key, parent_id, description, sort_order) VALUES
('user:manage:view', 1, '查看C端用户列表', 11),
('user:manage:create', 1, '创建C端用户', 12),
('user:manage:update', 1, '编辑C端用户信息', 13),
('user:manage:delete', 1, '删除C端用户', 14),
('user:manage:status', 1, '修改用户状态（冻结/解冻）', 15),
('user:manage:assign_devices', 1, '为用户分配设备', 16),
('user:manage:assign_permissions', 1, '为用户分配权限', 17),
('user:manage:reset_key', 1, '重置用户接入密钥', 18),
('user:manage:kick', 1, '强制用户下线', 19);

-- -------------------- 设备管理子权限（parent_id = 2）--------------------
INSERT INTO permission (perm_key, parent_id, description, sort_order) VALUES
('device:manage:view', 2, '查看设备信息', 21),
('device:manage:create', 2, '添加新设备', 22),
('device:manage:update', 2, '编辑设备信息', 23),
('device:manage:delete', 2, '删除设备', 24),
('device:manage:control', 2, '控制设备（启动/停止等）', 25);

-- -------------------- 审计日志子权限（parent_id = 3）--------------------
INSERT INTO permission (perm_key, parent_id, description, sort_order) VALUES
('logs:manage:view', 3, '查看审计日志', 31),
('logs:manage:export', 3, '导出日志数据', 32),
('logs:manage:delete', 3, '删除日志记录', 33);

-- -------------------- 系统管理子权限（parent_id = 4）--------------------
INSERT INTO permission (perm_key, parent_id, description, sort_order) VALUES
('system_admin:manage:view', 4, '查看管理员列表', 41),
('system_admin:manage:create', 4, '创建管理员账号', 42),
('system_admin:manage:update', 4, '编辑管理员信息', 43),
('system_admin:manage:delete', 4, '删除管理员账号', 44),
('system_admin:manage:assign_permissions', 4, '为管理员分配权限', 45);

-- -------------------- 数据仪表盘权限（独立，无父权限）--------------------
INSERT INTO permission (perm_key, parent_id, description, sort_order) VALUES
('dashboard:view', NULL, '查看数据仪表盘', 51),
('dashboard:export', NULL, '导出仪表盘数据', 52);

-- ====================================================================
-- 步骤4：验证数据
-- ====================================================================

-- 查看所有权限（按层级分组）
SELECT
    p.id,
    CASE
        WHEN p.parent_id IS NULL AND EXISTS(SELECT 1 FROM permission WHERE parent_id = p.id)
        THEN CONCAT('📁 ', p.perm_key)
        ELSE CONCAT('  └─ ', p.perm_key)
    END AS permission_tree,
    p.description,
    p.parent_id
FROM permission p
ORDER BY
    COALESCE(p.parent_id, p.id),
    p.sort_order;

-- 统计权限数量
SELECT
    '父权限' AS type,
    COUNT(*) AS count
FROM permission
WHERE parent_id IS NULL AND EXISTS(SELECT 1 FROM permission p2 WHERE p2.parent_id = permission.id)
UNION ALL
SELECT
    '子权限' AS type,
    COUNT(*) AS count
FROM permission
WHERE parent_id IS NOT NULL
UNION ALL
SELECT
    '独立权限' AS type,
    COUNT(*) AS count
FROM permission
WHERE parent_id IS NULL AND NOT EXISTS(SELECT 1 FROM permission p2 WHERE p2.parent_id = permission.id);

-- ====================================================================
-- 使用示例：权限分配
-- ====================================================================

-- 示例1：给管理员分配"用户管理"的所有权限（分配父权限即可）
-- INSERT INTO admin_permissions (admin_id, permission_id) VALUES (1, 1);
-- 结果：前端会自动识别该管理员拥有所有 user:manage:* 权限

-- 示例2：只给管理员分配"查看用户"和"创建用户"权限（分配具体的子权限）
-- INSERT INTO admin_permissions (admin_id, permission_id)
-- SELECT 1, id FROM permission WHERE perm_key IN ('user:manage:view', 'user:manage:create');
-- 结果：该管理员只能查看和创建用户，不能编辑、删除等

-- ====================================================================
-- 查询工具：获取某个管理员的所有有效权限（包括继承的）
-- ====================================================================

DELIMITER $$

CREATE FUNCTION IF NOT EXISTS get_admin_permissions(admin_id_param INT)
RETURNS TEXT
DETERMINISTIC
BEGIN
    DECLARE result TEXT DEFAULT '';

    -- 获取直接分配的权限
    SELECT GROUP_CONCAT(p.perm_key SEPARATOR ',')
    INTO result
    FROM admin_permissions ap
    JOIN permission p ON ap.permission_id = p.id
    WHERE ap.admin_id = admin_id_param;

    RETURN result;
END$$

DELIMITER ;

-- 使用示例：
-- SELECT get_admin_permissions(1);

