# -*- coding: utf-8 -*-
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# 导入 PyJWT 库（确保使用正确的包）
try:
    import jwt
except ImportError:
    # 如果导入失败，尝试使用 PyJWT
    import PyJWT as jwt

from datetime import datetime, timedelta
from base import Config, logger


class AuthService:
    """认证服务类，用于JWT令牌生成和验证"""
    
    def __init__(self):
        self.config = Config()
        self.logger = logger
        self.secret_key = self.config.JWT_SECRET_KEY
        self.algorithm = self.config.JWT_ALGORITHM
        self.expire_days = self.config.JWT_EXPIRE_DAYS
    
    def generate_token(self, user_id, email):
        """
        生成JWT令牌
        
        Args:
            user_id: 用户ID
            email: 用户邮箱
            
        Returns:
            str: JWT令牌
        """
        try:
            # 设置过期时间
            expire_time = datetime.utcnow() + timedelta(days=self.expire_days)
            
            # 创建payload
            payload = {
                'user_id': user_id,
                'email': email,
                'exp': expire_time,
                'iat': datetime.utcnow()
            }
            
            # 生成token
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            
            self.logger.info(f"JWT令牌生成成功: user_id={user_id}, email={email}")
            return token
            
        except Exception as e:
            self.logger.error(f"JWT令牌生成失败: {e}")
            raise
    
    def verify_token(self, token):
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            dict: 解码后的payload，包含user_id和email
            None: 验证失败返回None
        """
        try:
            # 解码token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            self.logger.info(f"JWT令牌验证成功: user_id={payload.get('user_id')}")
            return payload
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.error(f"JWT令牌验证失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"JWT令牌验证异常: {e}")
            return None
    
    def decode_token_without_verification(self, token):
        """
        不验证签名，仅解码token（用于调试）
        
        Args:
            token: JWT令牌
            
        Returns:
            dict: 解码后的payload
        """
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload
        except Exception as e:
            self.logger.error(f"JWT令牌解码失败: {e}")
            return None


if __name__ == '__main__':
    # 测试代码
    auth_service = AuthService()
    
    # 生成token
    token = auth_service.generate_token(user_id=1, email='test@example.com')
    print(f"生成的token: {token}")
    
    # 验证token
    payload = auth_service.verify_token(token)
    print(f"验证结果: {payload}")