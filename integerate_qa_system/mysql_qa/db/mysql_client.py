import sys
import os
import pymysql
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)
from base import Config, logger


class MysqlClient(object):
    def __init__(self):
        try:
            # 1. 连接Mysql数据库
            self.connect = pymysql.connect(host=Config().MYSQL_HOST, user=Config().MYSQL_USER,
                                           password=Config().MYSQL_PASSWORD,
                                           database=Config().MYSQL_DATABASE)

            # 2.获取游标cursor
            self.cursor = self.connect.cursor()
            logger.info('Mysql数据库连接成功')
        except Exception as e:
            logger.error(f'Mysql数据库连接失败: {e}')
            raise

    def create_table(self):
        create_table_query = '''
                CREATE TABLE IF NOT EXISTS jpkb (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    subject_name VARCHAR(20),
                    question VARCHAR(1000),
                    answer VARCHAR(1000))
                '''
        try:
            self.cursor.execute(create_table_query)
            self.connect.commit()
            logger.info('表创建成功')
        except pymysql.MySQLError as e:
            logger.error(f'表创建失败: {e}')
            raise

    def create_conversation_table(self):
        """创建用户表、会话表和对话记录表"""
        try:
            # 创建user表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS user (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '用户ID，主键',
                    email VARCHAR(255) NOT NULL COMMENT '用户邮箱',
                    create_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    PRIMARY KEY (id),
                    UNIQUE INDEX idx_email (email)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表'
            ''')
            
            # 创建user_session表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_session (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
                    user_id INT UNSIGNED NOT NULL COMMENT '用户ID，关联 user 表',
                    session_id VARCHAR(100) NOT NULL COMMENT '会话标识，唯一',
                    status TINYINT(1) NOT NULL DEFAULT 1 COMMENT '状态：0-已删除，1-正常',
                    PRIMARY KEY (id),
                    UNIQUE INDEX uk_session_id (session_id),
                    INDEX idx_user_id (user_id),
                    CONSTRAINT fk_user_session_user_id FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话表'
            ''')
            
            # 创建conversations表
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(100) NOT NULL COMMENT '会话ID，关联 user_session 表',
                    query TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    trace_data TEXT NULL COMMENT '系统执行链路JSON数据',
                    status INT NOT NULL DEFAULT 0 COMMENT '0-默认, 1-GoodCase, 2-BadCase',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
                    INDEX idx_session_id (session_id),
                    INDEX idx_status (status),
                    CONSTRAINT fk_conversations_session_id FOREIGN KEY (session_id) REFERENCES user_session (session_id) ON DELETE CASCADE ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话记录表'
            ''')
            
            self.connect.commit()
            logger.info('用户表、会话表和对话记录表创建成功')
            
            # 检查并添加/修改 trace_data 字段
            self.cursor.execute("SHOW COLUMNS FROM conversations LIKE 'trace_data'")
            result = self.cursor.fetchone()
            if not result:
                self.cursor.execute('ALTER TABLE conversations ADD COLUMN trace_data TEXT NULL COMMENT "系统执行链路JSON数据" AFTER answer')
                self.connect.commit()
                logger.info('conversations表添加trace_data字段成功')
            else:
                # 检查字段类型，如果是VARCHAR则修改为TEXT
                self.cursor.execute("SHOW COLUMNS FROM conversations WHERE Field='trace_data'")
                col_info = self.cursor.fetchone()
                if col_info and 'varchar' in str(col_info[1]).lower():
                    self.cursor.execute('ALTER TABLE conversations MODIFY COLUMN trace_data TEXT NULL COMMENT "系统执行链路JSON数据"')
                    self.connect.commit()
                    logger.info('conversations表trace_data字段类型已修改为TEXT')
            
            # 检查并添加 status 字段
            self.cursor.execute("SHOW COLUMNS FROM conversations LIKE 'status'")
            status_result = self.cursor.fetchone()
            if not status_result:
                self.cursor.execute('ALTER TABLE conversations ADD COLUMN status INT NOT NULL DEFAULT 0 COMMENT "0-默认, 1-GoodCase, 2-BadCase" AFTER trace_data')
                self.cursor.execute('ALTER TABLE conversations ADD INDEX idx_status (status)')
                self.connect.commit()
                logger.info('conversations表添加status字段成功')
        except pymysql.MySQLError as e:
            logger.error(f'表创建失败: {e}')
            raise

    def create_knowledge_tables(self):
        """创建知识库相关表：category和file_info"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS category (
                    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '分类ID，自增主键',
                    category VARCHAR(100) NOT NULL COMMENT '分类名称',
                    UNIQUE KEY uk_category (category)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件分类表'
            ''')
            
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_info (
                    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID，自增',
                    file_path VARCHAR(500) NOT NULL COMMENT '文件路径，不能为空',
                    is_dir TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否为文件夹：0-否，1-是',
                    is_chunk TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否切片：0-否，1-是',
                    category_id INT COMMENT '分类ID，关联category表的id',
                    INDEX idx_category (category_id),
                    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件记录表'
            ''')
            
            self.connect.commit()
            logger.info('知识库相关表创建成功')
        except pymysql.MySQLError as e:
            logger.error(f'知识库表创建失败: {e}')
            raise

    def insert_data(self, csv_path):
        data = pd.read_csv(csv_path)
        insert_query = """INSERT INTO jpkb (subject_name, question, answer) VALUES (%s,%s,%s)"""
        try:
            for _, row in data.iterrows():
                self.cursor.execute(insert_query, (row['学科名称'], row['问题'], row['答案']))
            self.connect.commit()
            logger.info('Mysql数据插入成功')
        except Exception as e:
            logger.error(f'Mysql数据插入失败: {e}')
            # rollback() 取消当前事物的所有操作, 让数据库"回到"执行这些操作状态之前的一个状态
            self.connect.rollback()
            raise

    def fetch_questions(self):
        try:
            # 执行查询语句
            self.cursor.execute("""SELECT question FROM jpkb""")

            # 获取查询结果
            questions = self.cursor.fetchall()
            logger.info('Mysql-questions查询成功')

            # 返回查询结果
            return questions
        except Exception as e:
            logger.error(f'Mysql-question查询失败: {e}')
            return []

    def fetch_answer_by_question(self, question):
        try:
            # 执行查询语句
            self.cursor.execute('SELECT answer FROM jpkb WHERE question = %s', (question,))

            # 获取查询结果
            answer = self.cursor.fetchone()
            logger.info(f'Mysql-answer查询成功: {question}')

            # 返回查询结果
            return answer[0] if answer else None
        except Exception as e:
            logger.error(f'Mysql-answer查询失败: {e}')
            return None

    # ==================== 用户相关操作 ====================
    
    def get_or_create_user(self, email):
        """
        根据邮箱获取或创建用户
        
        Args:
            email: 用户邮箱
            
        Returns:
            int: 用户ID
        """
        try:
            # 查询用户是否存在
            self.cursor.execute('SELECT id FROM user WHERE email = %s', (email,))
            user = self.cursor.fetchone()
            
            if user:
                logger.info(f'用户已存在: {email}')
                return user[0]
            else:
                # 创建新用户
                self.cursor.execute('INSERT INTO user (email) VALUES (%s)', (email,))
                self.connect.commit()
                user_id = self.cursor.lastrowid
                logger.info(f'新用户创建成功: {email}, user_id={user_id}')
                return user_id
        except Exception as e:
            logger.error(f'获取或创建用户失败: {e}')
            self.connect.rollback()
            raise

    def get_user_by_email(self, email):
        """
        根据邮箱获取用户信息
        
        Args:
            email: 用户邮箱
            
        Returns:
            dict: 用户信息字典，包含id和email
        """
        try:
            self.cursor.execute('SELECT id, email, create_at FROM user WHERE email = %s', (email,))
            user = self.cursor.fetchone()
            
            if user:
                return {
                    'id': user[0],
                    'email': user[1],
                    'create_at': user[2]
                }
            return None
        except Exception as e:
            logger.error(f'获取用户信息失败: {e}')
            return None

    # ==================== 会话相关操作 ====================
    
    def create_user_session(self, user_id, session_id):
        """
        创建用户会话
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            
        Returns:
            bool: 创建成功返回True
        """
        try:
            self.cursor.execute(
                'INSERT INTO user_session (user_id, session_id) VALUES (%s, %s)',
                (user_id, session_id)
            )
            self.connect.commit()
            logger.info(f'会话创建成功: user_id={user_id}, session_id={session_id}')
            return True
        except Exception as e:
            logger.error(f'会话创建失败: {e}')
            self.connect.rollback()
            return False

    def get_user_sessions(self, user_id, limit=20):
        """
        获取用户的所有会话（只返回status=1的会话）
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            list: 会话列表
        """
        try:
            query = '''
                SELECT us.session_id, MAX(c.created_at) as last_active
                FROM user_session us
                LEFT JOIN conversations c ON us.session_id = c.session_id
                WHERE us.user_id = %s AND us.status = 1
                GROUP BY us.session_id
                ORDER BY last_active DESC
                LIMIT %s
            '''
            self.cursor.execute(query, (user_id, limit))
            sessions = self.cursor.fetchall()
            logger.info(f'用户会话查询成功: user_id={user_id}')
            return sessions
        except Exception as e:
            logger.error(f'用户会话查询失败: {e}')
            return []
    
    def soft_delete_session(self, session_id, user_id):
        """
        软删除会话（将status设为0）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 删除成功返回True
        """
        try:
            self.cursor.execute(
                'UPDATE user_session SET status = 0 WHERE session_id = %s AND user_id = %s',
                (session_id, user_id)
            )
            self.connect.commit()
            affected_rows = self.cursor.rowcount
            if affected_rows > 0:
                logger.info(f'会话软删除成功: session_id={session_id}')
                return True
            else:
                logger.warning(f'会话软删除失败: 会话不存在或无权限 session_id={session_id}')
                return False
        except Exception as e:
            logger.error(f'会话软删除失败: {e}')
            self.connect.rollback()
            return False

    def verify_session_owner(self, session_id, user_id):
        """
        验证会话是否属于指定用户（只验证status=1的会话）
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            bool: 属于返回True，否则返回False
        """
        try:
            self.cursor.execute(
                'SELECT id FROM user_session WHERE session_id = %s AND user_id = %s AND status = 1',
                (session_id, user_id)
            )
            result = self.cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f'验证会话所有权失败: {e}')
            return False

    # ==================== 对话记录相关操作 ====================
    
    def save_conversation(self, session_id, query, answer):
        try:
            insert_query = """INSERT INTO conversations (session_id, query, answer) VALUES (%s, %s, %s)"""
            self.cursor.execute(insert_query, (session_id, query, answer))
            self.connect.commit()
            logger.info(f'会话保存成功: {session_id}')
            return True
        except Exception as e:
            logger.error(f'会话保存失败: {e}')
            self.connect.rollback()
            return False

    def fetch_conversations(self, session_id, limit=10):
        try:
            select_query = """SELECT query, answer, created_at, status, trace_data, id FROM conversations WHERE session_id = %s ORDER BY created_at DESC LIMIT %s"""
            self.cursor.execute(select_query, (session_id, limit))
            conversations = self.cursor.fetchall()
            logger.info(f'会话查询成功: {session_id}')
            return conversations
        except Exception as e:
            logger.error(f'会话查询失败: {e}')
            return []
    
    def get_conversation_by_id(self, conversation_id):
        """
        根据ID获取对话详情
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            dict: 对话详情
        """
        try:
            self.cursor.execute('''
                SELECT id, session_id, query, answer, trace_data, status, created_at
                FROM conversations 
                WHERE id = %s
            ''', (conversation_id,))
            result = self.cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'session_id': result[1],
                    'query': result[2],
                    'answer': result[3],
                    'trace_data': result[4],
                    'status': result[5],
                    'created_at': str(result[6])
                }
            return None
        except Exception as e:
            logger.error(f'获取对话详情失败: {e}')
            return None
    
    def update_conversation_status(self, conversation_id, status):
        """
        更新对话状态
        
        Args:
            conversation_id: 对话ID
            status: 状态值 (0-默认, 1-GoodCase, 2-BadCase)
            
        Returns:
            bool: 更新成功返回True
        """
        try:
            self.cursor.execute('''
                UPDATE conversations 
                SET status = %s 
                WHERE id = %s
            ''', (status, conversation_id))
            self.connect.commit()
            logger.info(f'对话状态更新成功: conversation_id={conversation_id}, status={status}')
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f'更新对话状态失败: {e}')
            self.connect.rollback()
            return False
    
    def get_conversations_by_status(self, status, limit=50, offset=0):
        """
        根据状态获取对话列表
        
        Args:
            status: 状态值 (1-GoodCase, 2-BadCase)
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            list: 对话列表
        """
        try:
            self.cursor.execute('''
                SELECT id, session_id, query, answer, trace_data, status, created_at
                FROM conversations 
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', (status, limit, offset))
            results = self.cursor.fetchall()
            return [{
                'id': r[0],
                'session_id': r[1],
                'query': r[2],
                'answer': r[3],
                'trace_data': r[4],
                'status': r[5],
                'created_at': str(r[6])
            } for r in results]
        except Exception as e:
            logger.error(f'根据状态获取对话列表失败: {e}')
            return []
    
    def get_conversations_count_by_status(self, status):
        """
        获取指定状态的对话数量
        
        Args:
            status: 状态值
            
        Returns:
            int: 数量
        """
        try:
            self.cursor.execute('SELECT COUNT(*) FROM conversations WHERE status = %s', (status,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f'获取对话数量失败: {e}')
            return 0

    def fetch_all_sessions(self, limit=20):
        """已废弃，请使用 get_user_sessions"""
        try:
            select_query = """
                SELECT DISTINCT session_id, MAX(created_at) as last_active
                FROM conversations
                GROUP BY session_id
                ORDER BY last_active DESC
                LIMIT %s
            """
            self.cursor.execute(select_query, (limit,))
            sessions = self.cursor.fetchall()
            logger.info('所有会话查询成功')
            return sessions
        except Exception as e:
            logger.error(f'所有会话查询失败: {e}')
            return []

    def create_category(self, category_name, base_path):
        """
        创建分类，同时在文件系统中创建对应文件夹
        
        Args:
            category_name: 分类名称
            base_path: 基础路径
            
        Returns:
            dict: 包含category_id和folder_path的字典
        """
        try:
            folder_path = os.path.join(base_path, category_name)
            os.makedirs(folder_path, exist_ok=True)
            
            self.cursor.execute(
                'INSERT INTO category (category) VALUES (%s)',
                (category_name,)
            )
            self.connect.commit()
            category_id = self.cursor.lastrowid
            
            self.cursor.execute(
                'INSERT INTO file_info (file_path, is_dir, category_id) VALUES (%s, %s, %s)',
                (folder_path, 1, category_id)
            )
            self.connect.commit()
            
            logger.info(f'分类创建成功: {category_name}, path={folder_path}')
            return {
                'category_id': category_id,
                'folder_path': folder_path
            }
        except pymysql.IntegrityError as e:
            logger.error(f'分类已存在: {category_name}')
            self.connect.rollback()
            raise ValueError(f'分类名称已存在: {category_name}')
        except Exception as e:
            logger.error(f'创建分类失败: {e}')
            self.connect.rollback()
            raise

    def get_all_categories(self):
        """
        获取所有分类
        
        Returns:
            list: 分类列表
        """
        try:
            self.cursor.execute('SELECT id, category FROM category ORDER BY id')
            categories = self.cursor.fetchall()
            return [{'id': cat[0], 'category': cat[1]} for cat in categories]
        except Exception as e:
            logger.error(f'获取分类列表失败: {e}')
            return []

    def get_category_by_id(self, category_id):
        """
        根据ID获取分类信息
        
        Args:
            category_id: 分类ID
            
        Returns:
            dict: 分类信息
        """
        try:
            self.cursor.execute('SELECT id, category FROM category WHERE id = %s', (category_id,))
            cat = self.cursor.fetchone()
            if cat:
                return {'id': cat[0], 'category': cat[1]}
            return None
        except Exception as e:
            logger.error(f'获取分类信息失败: {e}')
            return None

    def get_files_by_category(self, category_id):
        """
        获取指定分类下的所有文件和文件夹（排除分类文件夹本身）
        
        Args:
            category_id: 分类ID
            
        Returns:
            list: 文件列表
        """
        try:
            category = self.get_category_by_id(category_id)
            if not category:
                return []
            
            self.cursor.execute('''
                SELECT id, file_path, is_dir, is_chunk, category_id 
                FROM file_info 
                WHERE category_id = %s 
                ORDER BY is_dir DESC, file_path ASC
            ''', (category_id,))
            files = self.cursor.fetchall()
            
            category_folder_path = None
            for f in files:
                if f[2] == 1:
                    file_name = os.path.basename(f[1])
                    if file_name == category['category']:
                        category_folder_path = f[1]
                        break
            
            result = []
            for f in files:
                if category_folder_path and f[1] == category_folder_path:
                    continue
                result.append({
                    'id': f[0],
                    'file_path': f[1],
                    'is_dir': bool(f[2]),
                    'is_chunk': bool(f[3]),
                    'category_id': f[4]
                })
            
            return result
        except Exception as e:
            logger.error(f'获取文件列表失败: {e}')
            return []

    def get_all_files(self):
        """
        获取所有文件
        
        Returns:
            list: 文件列表
        """
        try:
            self.cursor.execute('''
                SELECT id, file_path, is_dir, is_chunk, category_id 
                FROM file_info 
                ORDER BY category_id, is_dir DESC, file_path ASC
            ''')
            files = self.cursor.fetchall()
            return [{
                'id': f[0],
                'file_path': f[1],
                'is_dir': bool(f[2]),
                'is_chunk': bool(f[3]),
                'category_id': f[4]
            } for f in files]
        except Exception as e:
            logger.error(f'获取所有文件失败: {e}')
            return []

    def get_file_by_id(self, file_id):
        """
        根据ID获取文件信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            dict: 文件信息
        """
        try:
            self.cursor.execute('''
                SELECT id, file_path, is_dir, is_chunk, category_id 
                FROM file_info 
                WHERE id = %s
            ''', (file_id,))
            f = self.cursor.fetchone()
            if f:
                return {
                    'id': f[0],
                    'file_path': f[1],
                    'is_dir': bool(f[2]),
                    'is_chunk': bool(f[3]),
                    'category_id': f[4]
                }
            return None
        except Exception as e:
            logger.error(f'获取文件信息失败: {e}')
            return None

    def get_files_by_parent_folder(self, folder_id):
        """
        获取文件夹下的所有文件（通过路径前缀匹配）
        
        Args:
            folder_id: 文件夹ID
            
        Returns:
            list: 文件列表
        """
        try:
            folder = self.get_file_by_id(folder_id)
            if not folder or not folder['is_dir']:
                return []
            
            folder_path = folder['file_path']
            
            self.cursor.execute('''
                SELECT id, file_path, is_dir, is_chunk, category_id 
                FROM file_info 
                WHERE file_path LIKE %s AND id != %s
                ORDER BY is_dir DESC, file_path ASC
            ''', (folder_path + '/%', folder_id))
            files = self.cursor.fetchall()
            return [{
                'id': f[0],
                'file_path': f[1],
                'is_dir': bool(f[2]),
                'is_chunk': bool(f[3]),
                'category_id': f[4]
            } for f in files]
        except Exception as e:
            logger.error(f'获取文件夹下文件失败: {e}')
            return []

    def add_file(self, file_path, is_dir, category_id, is_chunk=False):
        """
        添加文件记录
        
        Args:
            file_path: 文件路径
            is_dir: 是否为文件夹
            category_id: 分类ID
            is_chunk: 是否已切片
            
        Returns:
            int: 文件ID
        """
        try:
            self.cursor.execute('''
                INSERT INTO file_info (file_path, is_dir, is_chunk, category_id) 
                VALUES (%s, %s, %s, %s)
            ''', (file_path, 1 if is_dir else 0, 1 if is_chunk else 0, category_id))
            self.connect.commit()
            file_id = self.cursor.lastrowid
            logger.info(f'文件记录添加成功: {file_path}')
            return file_id
        except Exception as e:
            logger.error(f'添加文件记录失败: {e}')
            self.connect.rollback()
            raise

    def update_file_chunk_status(self, file_id, is_chunk):
        """
        更新文件的切片状态
        
        Args:
            file_id: 文件ID
            is_chunk: 是否已切片
            
        Returns:
            bool: 更新成功返回True
        """
        try:
            self.cursor.execute('''
                UPDATE file_info SET is_chunk = %s WHERE id = %s
            ''', (1 if is_chunk else 0, file_id))
            self.connect.commit()
            logger.info(f'文件切片状态更新成功: file_id={file_id}')
            return True
        except Exception as e:
            logger.error(f'更新文件切片状态失败: {e}')
            self.connect.rollback()
            return False

    def delete_file(self, file_id):
        """
        删除文件记录
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 删除成功返回True
        """
        try:
            self.cursor.execute('SELECT file_path, is_dir FROM file_info WHERE id = %s', (file_id,))
            file_info = self.cursor.fetchone()
            
            if not file_info:
                logger.warning(f'文件不存在: file_id={file_id}')
                return False
            
            file_path = file_info[0]
            is_dir = file_info[1]
            
            if os.path.exists(file_path):
                if is_dir:
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            
            self.cursor.execute('DELETE FROM file_info WHERE id = %s', (file_id,))
            self.connect.commit()
            logger.info(f'文件删除成功: {file_path}')
            return True
        except Exception as e:
            logger.error(f'删除文件失败: {e}')
            self.connect.rollback()
            raise

    def delete_category(self, category_id):
        """
        删除分类及其所有文件
        
        Args:
            category_id: 分类ID
            
        Returns:
            bool: 删除成功返回True
        """
        try:
            self.cursor.execute('SELECT category FROM category WHERE id = %s', (category_id,))
            cat = self.cursor.fetchone()
            
            if not cat:
                logger.warning(f'分类不存在: category_id={category_id}')
                return False
            
            self.cursor.execute('SELECT file_path FROM file_info WHERE category_id = %s', (category_id,))
            files = self.cursor.fetchall()
            
            import shutil
            for file_path in files:
                if os.path.exists(file_path[0]):
                    if os.path.isdir(file_path[0]):
                        shutil.rmtree(file_path[0])
                    else:
                        os.remove(file_path[0])
            
            self.cursor.execute('DELETE FROM file_info WHERE category_id = %s', (category_id,))
            self.cursor.execute('DELETE FROM category WHERE id = %s', (category_id,))
            self.connect.commit()
            logger.info(f'分类删除成功: category_id={category_id}')
            return True
        except Exception as e:
            logger.error(f'删除分类失败: {e}')
            self.connect.rollback()
            raise

    def close(self):
        try:
            self.connect.close()
            logger.info('Mysql数据库连接关闭')
        except Exception as e:
            logger.error(f'Mysql数据库连接关闭失败: {e}')

    def create_config_version_table(self):
        """创建配置版本表"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_version (
                    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '版本ID',
                    version VARCHAR(50) NOT NULL COMMENT '版本号',
                    config_content TEXT NOT NULL COMMENT '配置内容(JSON格式)',
                    change_description VARCHAR(500) COMMENT '变更描述',
                    changed_by VARCHAR(100) COMMENT '变更人',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    is_active TINYINT(1) DEFAULT 1 COMMENT '是否为当前活跃版本',
                    INDEX idx_version (version),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配置版本表'
            ''')
            self.connect.commit()
            logger.info('配置版本表创建成功')
        except pymysql.MyQSLLError as e:
            logger.error(f'配置版本表创建失败: {e}')
            raise

    def get_current_config(self):
        """
        获取当前配置内容
        
        Returns:
            dict: 当前配置内容
        """
        try:
            self.cursor.execute('''
                SELECT id, version, config_content, created_at 
                FROM config_version 
                WHERE is_active = 1 
                ORDER BY created_at DESC 
                LIMIT 1
            ''')
            result = self.cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'version': result[1],
                    'config_content': result[2],
                    'created_at': str(result[3])
                }
            return None
        except Exception as e:
            logger.error(f'获取当前配置失败: {e}')
            return None

    def get_config_versions(self, limit=20):
        """
        获取配置版本列表
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list: 版本列表
        """
        try:
            self.cursor.execute('''
                SELECT id, version, change_description, changed_by, created_at, is_active
                FROM config_version 
                ORDER BY created_at DESC 
                LIMIT %s
            ''', (limit,))
            results = self.cursor.fetchall()
            return [{
                'id': r[0],
                'version': r[1],
                'change_description': r[2],
                'changed_by': r[3],
                'created_at': str(r[4]),
                'is_active': bool(r[5])
            } for r in results]
        except Exception as e:
            logger.error(f'获取配置版本列表失败: {e}')
            return []

    def save_config_version(self, version, config_content, change_description='', changed_by='system'):
        """
        保存新的配置版本
        
        Args:
            version: 版本号
            config_content: 配置内容(JSON字符串)
            change_description: 变更描述
            changed_by: 变更人
            
        Returns:
            int: 新版本ID
        """
        try:
            self.cursor.execute('UPDATE config_version SET is_active = 0')
            
            self.cursor.execute('''
                INSERT INTO config_version (version, config_content, change_description, changed_by, is_active)
                VALUES (%s, %s, %s, %s, 1)
            ''', (version, config_content, change_description, changed_by))
            self.connect.commit()
            version_id = self.cursor.lastrowid
            logger.info(f'配置版本保存成功: version={version}')
            return version_id
        except Exception as e:
            logger.error(f'保存配置版本失败: {e}')
            self.connect.rollback()
            raise

    def rollback_config(self, version_id):
        """
        回退到指定配置版本（不创建新版本）
        
        Args:
            version_id: 目标版本ID
            
        Returns:
            dict: 回退后的配置内容
        """
        try:
            self.cursor.execute('''
                SELECT id, version, config_content, change_description
                FROM config_version 
                WHERE id = %s
            ''', (version_id,))
            result = self.cursor.fetchone()
            
            if not result:
                logger.warning(f'配置版本不存在: version_id={version_id}')
                return None
            
            old_version = result[1]
            config_content = result[2]
            
            self.cursor.execute('UPDATE config_version SET is_active = 0')
            self.cursor.execute('UPDATE config_version SET is_active = 1 WHERE id = %s', (version_id,))
            self.connect.commit()
            
            logger.info(f'配置回退成功: 回退到版本 {old_version}')
            return {
                'id': result[0],
                'version': old_version,
                'config_content': config_content,
                'original_version': old_version
            }
        except Exception as e:
            logger.error(f'配置回退失败: {e}')
            self.connect.rollback()
            raise

    def get_config_by_id(self, version_id):
        """
        根据ID获取配置版本详情
        
        Args:
            version_id: 版本ID
            
        Returns:
            dict: 配置详情
        """
        try:
            self.cursor.execute('''
                SELECT id, version, config_content, change_description, changed_by, created_at, is_active
                FROM config_version 
                WHERE id = %s
            ''', (version_id,))
            result = self.cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'version': result[1],
                    'config_content': result[2],
                    'change_description': result[3],
                    'changed_by': result[4],
                    'created_at': str(result[5]),
                    'is_active': bool(result[6])
                }
            return None
        except Exception as e:
            logger.error(f'获取配置版本详情失败: {e}')
            return None

    def get_all_faqs(self, search_keyword=None):
        """获取所有FAQ，支持模糊搜索"""
        try:
            if search_keyword:
                search_pattern = f'%{search_keyword}%'
                self.cursor.execute('''
                    SELECT id, subject_name, question, answer 
                    FROM jpkb 
                    WHERE subject_name LIKE %s OR question LIKE %s
                    ORDER BY id DESC
                ''', (search_pattern, search_pattern))
            else:
                self.cursor.execute('''
                    SELECT id, subject_name, question, answer 
                    FROM jpkb 
                    ORDER BY id DESC
                ''')
            results = self.cursor.fetchall()
            return [{
                'id': row[0],
                'subject_name': row[1],
                'question': row[2],
                'answer': row[3]
            } for row in results]
        except Exception as e:
            logger.error(f'获取FAQ列表失败: {e}')
            return []

    def get_faq_by_id(self, faq_id):
        """根据ID获取FAQ"""
        try:
            self.cursor.execute('''
                SELECT id, subject_name, question, answer 
                FROM jpkb 
                WHERE id = %s
            ''', (faq_id,))
            result = self.cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'subject_name': result[1],
                    'question': result[2],
                    'answer': result[3]
                }
            return None
        except Exception as e:
            logger.error(f'获取FAQ详情失败: {e}')
            return None

    def add_faq(self, subject_name, question, answer):
        """添加FAQ"""
        try:
            self.cursor.execute('''
                INSERT INTO jpkb (subject_name, question, answer) 
                VALUES (%s, %s, %s)
            ''', (subject_name, question, answer))
            self.connect.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f'添加FAQ失败: {e}')
            self.connect.rollback()
            raise

    def update_faq(self, faq_id, subject_name, question, answer):
        """更新FAQ"""
        try:
            self.cursor.execute('''
                UPDATE jpkb 
                SET subject_name = %s, question = %s, answer = %s 
                WHERE id = %s
            ''', (subject_name, question, answer, faq_id))
            self.connect.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f'更新FAQ失败: {e}')
            self.connect.rollback()
            raise

    def delete_faq(self, faq_id):
        """删除FAQ"""
        try:
            self.cursor.execute('DELETE FROM jpkb WHERE id = %s', (faq_id,))
            self.connect.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logger.error(f'删除FAQ失败: {e}')
            self.connect.rollback()
            raise


if __name__ == '__main__':
    mysql_client = MysqlClient()
    # mysql_client.insert_data('../data/JP学科知识问答.csv')
    # questions = mysql_client.fetch_questions()
    # print(len(questions))
    # print(questions[:5])
    # res = mysql_client.fetch_answer_by_question('关联子查询的执行顺序是什么')
    # print(res)
    # mysql_client.close()
    mysql_client.create_conversation_table()