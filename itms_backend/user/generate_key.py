"""
生成用户接入密钥的函数
"""
def _generate_access_key():
    import uuid
    return str(uuid.uuid4()).replace('-', '')