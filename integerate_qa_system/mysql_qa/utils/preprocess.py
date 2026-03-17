import jieba
import sys, os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)
from base import logger


def process_text(text: str):
    try:
        logger.info('开始文本预处理')
        return jieba.lcut(text.lower())
    except Exception as e:
        logger.error(f'文本预处理失败: {e}')
        return []
if __name__ == '__main__':
    print(process_text('黑马程序员'))