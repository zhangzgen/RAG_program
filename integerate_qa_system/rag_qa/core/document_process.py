import os, sys
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import MarkdownTextSplitter
from datetime import datetime

module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(module_path)
sys.path.insert(0, module_path)
sys.path.insert(0, project_root)
from edu_text_spliter import AliTextSplitter, ChineseRecursiveTextSplitter
from edu_document_loaders import OCRPDFLoader, OCRDOCLoader, OCRPPTLoader, OCRIMGLoader
from base import logger, Config
from rich import print

config = Config()

SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.ppt', '.pptx', '.jpg', '.png', '.md']

document_loaders = {
    ".txt": TextLoader,
    ".pdf": OCRPDFLoader,
    ".docx": OCRDOCLoader,
    ".ppt": OCRPPTLoader,
    ".pptx": OCRPPTLoader,
    ".jpg": OCRIMGLoader,
    ".png": OCRIMGLoader,
    ".md": TextLoader
}

loader_kwargs = {
    ".txt": {"param_name": "file_path", "encoding": "utf-8"},
    ".pdf": {"param_name": "file_path"},
    ".docx": {"param_name": "filepath"},
    ".ppt": {"param_name": "filepath"},
    ".pptx": {"param_name": "filepath"},
    ".jpg": {"param_name": "img_path"},
    ".png": {"param_name": "img_path"},
    ".md": {"param_name": "file_path", "encoding": "utf-8"}
}


def load_single_file(file_path):
    """
    加载单个文件并返回文档列表
    
    Args:
        file_path: 文件完整路径
        
    Returns:
        list: 加载的文档列表，失败返回None
    """
    if not os.path.exists(file_path):
        logger.error(f'文件不存在: {file_path}')
        return None
        
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension not in document_loaders:
        logger.warning(f'不支持的文件类型: {file_extension}')
        return None
    
    try:
        loader_class = document_loaders.get(file_extension)
        kwargs_config = loader_kwargs.get(file_extension, {})
        param_name = kwargs_config.get("param_name", "file_path")
        
        kwargs = {param_name: file_path}
        if file_extension in ['.txt', '.md']:
            kwargs['encoding'] = 'utf-8'
            
        loader = loader_class(**kwargs)
        loaded_doc = loader.load()
        
        for doc in loaded_doc:
            doc.metadata['file_path'] = file_path
            doc.metadata['timestamp'] = datetime.now().isoformat()
            
        logger.info(f'成功加载文件: {file_path}, 文档数: {len(loaded_doc)}')
        return loaded_doc
        
    except Exception as e:
        logger.error(f'加载文件失败 {file_path}: {e}')
        return None


def process_single_file(file_path, source='unknown', parent_chunk_size=None, 
                        child_chunk_size=None, chunk_overlap=None):
    """
    处理单个文件并进行切分
    
    Args:
        file_path: 文件完整路径
        source: 来源标识
        parent_chunk_size: 父块大小
        child_chunk_size: 子块大小
        chunk_overlap: 重叠大小
        
    Returns:
        list: 切分后的子块列表，失败返回None
    """
    parent_chunk_size = parent_chunk_size or config.PARENT_CHUNK_SIZE
    child_chunk_size = child_chunk_size or config.CHILD_CHUNK_SIZE
    chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
    
    documents = load_single_file(file_path)
    
    if documents is None or len(documents) == 0:
        return None
    
    parent_splitter = ChineseRecursiveTextSplitter(chunk_size=parent_chunk_size, chunk_overlap=chunk_overlap)
    child_splitter = ChineseRecursiveTextSplitter(chunk_size=child_chunk_size, chunk_overlap=chunk_overlap)
    markdown_parent_splitter = MarkdownTextSplitter(chunk_size=parent_chunk_size, chunk_overlap=chunk_overlap)
    markdown_child_splitter = MarkdownTextSplitter(chunk_size=child_chunk_size, chunk_overlap=chunk_overlap)
    
    child_chunks = []
    
    for i, doc in enumerate(documents):
        file_extension = os.path.splitext(doc.metadata.get('file_path', ''))[1].lower()
        
        is_markdown = (file_extension == '.md')
        parent_splitter_to_use = markdown_parent_splitter if is_markdown else parent_splitter
        child_splitter_to_use = markdown_child_splitter if is_markdown else child_splitter
        
        logger.info(f'处理文档: {doc.metadata.get("file_path", "")}, 使用切分器: {"Markdown" if is_markdown else "ChineseRecursive"}')
        
        parent_docs = parent_splitter_to_use.split_documents([doc])
        
        for j, parent_doc in enumerate(parent_docs):
            parent_id = f'doc_{i}_parent_{j}'
            
            child_docs = child_splitter_to_use.split_documents([parent_doc])
            
            for k, child_chunk in enumerate(child_docs):
                child_chunk.metadata['parent_id'] = parent_id
                child_chunk.metadata['parent_content'] = parent_doc.page_content
                child_chunk.metadata['id'] = f'{parent_id}_child_{k}'
                child_chunk.metadata['source'] = source
                child_chunks.append(child_chunk)
    
    logger.info(f'文件 {file_path} 生成子块数量: {len(child_chunks)}')
    return child_chunks


# 定义函数, 从指定文件夹加载多种类型文件并添加元数据
def load_documents_from_directory(directory_path):
    # 初始化空列表, 用于存储加载的文档
    documents = []
    # 获取支持的文件扩展名集合
    supported_extensions = document_loaders.keys()
    # 从目录名提取学科类别(如 "ai" ->  "ai")
    source = os.path.basename(directory_path)

    # 遍历指定目录, 及其子目录
    for root, _, files in os.walk(directory_path):
        print(files)
        # 遍历当前目录下的所有文件
        for file_name in files:
            # 构建文件的完整路径
            file_path = os.path.join(root, file_name)
            # 获取文件的扩展名(小写) -> (.pdf, .txt)
            file_extension_name = os.path.splitext(file_path)[1].lower()

            # 判断是否支持当前文件扩展名
            if file_extension_name in supported_extensions:
                try:
                    # 根据扩展名 获取对应的文件加载器类
                    loader_class = document_loaders.get(file_extension_name)
                    # 实例化加载器对象
                    if file_extension_name == '.txt':
                        loader = loader_class(file_path=file_path, encoding='utf-8')
                    else:
                        loader = loader_class(file_path=file_path)
                    # 调用加载器加载文档内容, 返回文档列表
                    loaded_doc = loader.load()
                    # 遍历加载的文件
                    for doc in loaded_doc:
                        # 为文档添加学科类元数据
                        doc.metadata['source'] = source
                        # 文档添加文件路径元数据
                        doc.metadata['file_path'] = file_path
                        # 为文档添加当前时间戳元数据
                        doc.metadata['timestamp'] = datetime.now().isoformat()
                    # 将加载的文档添加到总列表中
                    documents.extend(loaded_doc)
                    # 记录成功加载文件的日志
                    logger.info(f'成功加载文件: {file_path}')
                except Exception as e:
                    logger.error(f"文件加载异常: {e}")
            else:
                logger.warning(f'不支持: {file_extension_name} 结尾的文件')

    # 返回所有加载的文档列表
    return documents


# 定义函数,处理文档并进行分层切分, 返回子快结果
def process_documents(directory_path, parent_chunk_size=config.PARENT_CHUNK_SIZE,
                      child_chunk_size=config.CHILD_CHUNK_SIZE, chunck_overlap=config.CHUNK_OVERLAP):
    # 从指定目录加载所有文档
    documents = load_documents_from_directory(directory_path)
    # 记录加载的文档数目
    logger.info(f'加载的文档数量: {len(documents)}')

    # 初始化父块子块分词器(通用)
    parent_splitter = ChineseRecursiveTextSplitter(chunk_size=parent_chunk_size, chunk_overlap=chunck_overlap)
    child_splitter = ChineseRecursiveTextSplitter(chunk_size=child_chunk_size, chunk_overlap=chunck_overlap)
    # 初始化Markdown专用分词器
    markdown_parent_splitter = MarkdownTextSplitter(chunk_size=parent_chunk_size, chunk_overlap=chunck_overlap)
    markdown_child_splitter = MarkdownTextSplitter(chunk_size=child_chunk_size, chunk_overlap=chunck_overlap)

    # 初始化空列表用于存储所以子块
    child_chunks = []
    # 遍历每个原文档, 带上索引i
    for i, doc in enumerate(documents):
        # 获取文件扩展名
        file_extension = os.path.splitext(doc.metadata.get('file_path', ''))[1].lower()

        # 选择分割器
        is_markdown = (file_extension == '.md')
        parent_splitter_to_use = markdown_parent_splitter if is_markdown else parent_splitter
        child_splitter_to_use = markdown_child_splitter if is_markdown else child_splitter

        logger.info(
            f'处理文档: {doc.metadata["file_path"]}, 使用切分器: {"Markdown" if is_markdown else "ChineseRecursive"}')

        # 使用父块分词器将文档切分为父块
        parent_docs = parent_splitter_to_use.split_documents([doc])
        # 遍历每个父块带上索引j
        for j, parent_doc in enumerate(parent_docs):
            # 为父块生成唯一的id, 格式 -> doc_i_parent_j
            parent_id = f'doc_{i}_parent_{j}'

            # 使用子块分词器将父块切分为子块
            child_docs = child_splitter_to_use.split_documents([parent_doc])
            # 遍历每个子块带上索引k
            for k, child_chunk in enumerate(child_docs):
                # 为子块添加父块 ID 到原数据
                child_chunk.metadata['parent_id'] = parent_id
                # 为子块添加父块内容到元数据
                child_chunk.metadata['parent_content'] = parent_doc.page_content
                # 为子块生成唯一 ID, 格式为 parent_id_child_k
                child_chunk.metadata['id'] = f'{parent_id}_child_{k}'
                # 将子块添加到子块列表中
                child_chunks.append(child_chunk)
    # 记录子块总数日志
    logger.info(f'子块数量: {len(child_chunks)}')
    # 返回所有子块列表
    return child_chunks


if __name__ == '__main__':
    # load_documents_from_directory(
    #     r"D:\Document\PythonProjects\Edu_RAG_QA\integerate_qa_system\data\ai")
    cc = process_documents(r"D:\WorkSpace\RAG_program\integerate_qa_system\data")
    print(cc[:2])

