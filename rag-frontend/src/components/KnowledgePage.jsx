import React, { useState, useEffect } from 'react';
import { 
  getKnowledgeFiles, 
  previewFileByPath,
  uploadFileToCategory,
  getCategories,
  createCategory,
  deleteCategory,
  vectorSearch,
  getKnowledgeSources,
  chunkFilesPost,
  getSupportedFileTypes,
  getFileChunks
} from '../api';
import FilePreview from './FilePreview';
import './KnowledgePage.css';

const FILE_ICONS = {
  '.pdf': '📄', '.doc': '📝', '.docx': '📝', '.xls': '📊', '.xlsx': '📊',
  '.ppt': '📽', '.pptx': '📽', '.txt': '📃', '.md': '📝', '.py': '🐍',
  '.js': '📜', '.jsx': '⚛️', '.ts': '📘', '.tsx': '⚛️', '.json': '📋',
  '.html': '🌐', '.css': '🎨', '.jpg': '🖼', '.jpeg': '🖼', '.png': '🖼',
  '.gif': '🖼', '.svg': '🎨', '.zip': '📦', '.rar': '📦', default: '📄'
};

const DEFAULT_SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.docx', '.ppt', '.pptx', '.jpg', '.png', '.md'];

const getFileIcon = (fileType, isDir) => {
  if (isDir) return '📁';
  return FILE_ICONS[fileType] || FILE_ICONS.default;
};

const KnowledgePage = () => {
  const [files, setFiles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentCategoryId, setCurrentCategoryId] = useState(null);
  const [currentCategoryName, setCurrentCategoryName] = useState(null);
  const [previewFile, setPreviewFile] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(null);
  const [newCategoryName, setNewCategoryName] = useState('');
  
  const [vectorQuery, setVectorQuery] = useState('');
  const [vectorResults, setVectorResults] = useState([]);
  const [vectorSearching, setVectorSearching] = useState(false);
  const [selectedSource, setSelectedSource] = useState('');
  const [sources, setSources] = useState([]);
  const [expandedResult, setExpandedResult] = useState(null);
  
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [chunking, setChunking] = useState(false);
  const [chunkProgress, setChunkProgress] = useState(null);
  const [chunkResults, setChunkResults] = useState([]);
  const [chunkComplete, setChunkComplete] = useState(false);
  const [supportedExtensions, setSupportedExtensions] = useState(DEFAULT_SUPPORTED_EXTENSIONS);
  
  const [showChunksModal, setShowChunksModal] = useState(false);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [fileChunks, setFileChunks] = useState([]);
  const [chunksFileName, setChunksFileName] = useState('');
  const [expandedChunk, setExpandedChunk] = useState(null);

  useEffect(() => {
    loadCategories();
    loadFiles(null);
    loadSources();
    loadSupportedTypes();
  }, []);

  const loadSupportedTypes = async () => {
    try {
      const data = await getSupportedFileTypes();
      if (data.supported_extensions) {
        setSupportedExtensions(data.supported_extensions);
      }
    } catch (error) {
      console.error('获取支持的文件类型失败:', error);
    }
  };

  const loadCategories = async () => {
    try {
      const data = await getCategories();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('加载分类失败:', error);
    }
  };

  const loadSources = async () => {
    try {
      const data = await getKnowledgeSources();
      setSources(data.sources || []);
    } catch (error) {
      console.error('加载来源失败:', error);
    }
  };

  const loadFiles = async (categoryId) => {
    try {
      setLoading(true);
      const data = await getKnowledgeFiles(categoryId);
      setFiles(data.files || []);
      setCurrentCategoryId(data.category_id);
      setCurrentCategoryName(data.category_name);
    } catch (error) {
      console.error('加载文件失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleItemClick = (item) => {
    if (item.is_dir && item.category_id) {
      loadFiles(item.category_id);
    } else if (!item.is_dir) {
      handleFilePreview(item);
    }
  };

  const handleFilePreview = async (file) => {
    try {
      setLoading(true);
      const data = await previewFileByPath(file.path);
      setPreviewFile({
        ...file,
        file_name: data.file_name || file.name,
        content: data.content,
        file_type: data.file_type,
        file_ext: data.file_ext,
        mime_type: data.mime_type,
        file_size: data.file_size
      });
      setShowPreview(true);
    } catch (error) {
      alert(error.message || '预览文件失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTraceSource = async (filePath) => {
    if (!filePath) {
      alert('文件路径不存在');
      return;
    }
    try {
      setLoading(true);
      const data = await previewFileByPath(filePath);
      setPreviewFile({
        file_name: data.file_name || filePath.split('/').pop().split('\\').pop(),
        content: data.content,
        file_type: data.file_type,
        file_ext: data.file_ext,
        mime_type: data.mime_type,
        file_size: data.file_size,
        path: filePath
      });
      setShowPreview(true);
    } catch (error) {
      alert(error.message || '溯源文件预览失败');
    } finally {
      setLoading(false);
    }
  };

  const handleViewChunks = async (file) => {
    if (!file.is_chunk) {
      alert('该文件尚未切片');
      return;
    }
    try {
      setChunksLoading(true);
      setChunksFileName(file.name);
      setExpandedChunk(null);
      setShowChunksModal(true);
      const data = await getFileChunks(file.id);
      setFileChunks(data.chunks || []);
    } catch (error) {
      alert(error.message || '获取切片失败');
      setShowChunksModal(false);
    } finally {
      setChunksLoading(false);
    }
  };

  const handleUploadFile = async () => {
    if (!uploadingFile || !currentCategoryId) {
      alert('请选择文件');
      return;
    }
    
    const fileExt = '.' + uploadingFile.name.split('.').pop().toLowerCase();
    if (!supportedExtensions.includes(fileExt)) {
      alert(`不支持的文件类型: ${fileExt}\n支持的类型: ${supportedExtensions.join(', ')}`);
      return;
    }
    
    try {
      setLoading(true);
      await uploadFileToCategory(currentCategoryId, uploadingFile);
      setShowUploadModal(false);
      setUploadingFile(null);
      await loadFiles(currentCategoryId);
    } catch (error) {
      alert(error.message || '上传文件失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCategory = async () => {
    if (!newCategoryName.trim()) {
      alert('请输入分类名称');
      return;
    }
    try {
      await createCategory(newCategoryName.trim());
      setShowCreateModal(false);
      setNewCategoryName('');
      await loadCategories();
      await loadSources();
      await loadFiles(null);
    } catch (error) {
      alert(error.message || '创建分类失败');
    }
  };

  const handleDeleteCategory = async (categoryId, e) => {
    e.stopPropagation();
    if (!window.confirm('确定要删除此分类吗？这将删除分类下的所有文件。')) return;
    try {
      await deleteCategory(categoryId);
      if (currentCategoryId === categoryId) {
        loadFiles(null);
      }
      await loadCategories();
      await loadSources();
    } catch (error) {
      alert(error.message || '删除分类失败');
    }
  };

  const handleVectorSearch = async () => {
    if (!vectorQuery.trim()) {
      alert('请输入查询内容');
      return;
    }
    
    setVectorSearching(true);
    setExpandedResult(null);
    
    try {
      const data = await vectorSearch(
        vectorQuery.trim(),
        selectedSource || null,
        10
      );
      setVectorResults(data.results || []);
    } catch (error) {
      alert(error.message || '向量检索失败');
      setVectorResults([]);
    } finally {
      setVectorSearching(false);
    }
  };

  const handleResultClick = (result) => {
    if (expandedResult === result.id) {
      setExpandedResult(null);
    } else {
      setExpandedResult(result.id);
    }
  };

  const handleSelectFile = (fileId, e) => {
    e.stopPropagation();
    setSelectedFiles(prev => {
      if (prev.includes(fileId)) {
        return prev.filter(id => id !== fileId);
      } else {
        return [...prev, fileId];
      }
    });
  };

  const handleSelectAll = () => {
    if (currentCategoryId === null) {
      const selectableItems = files.filter(f => f.is_dir && f.id.toString().startsWith('cat_'));
      if (selectedFiles.length === selectableItems.length) {
        setSelectedFiles([]);
      } else {
        setSelectedFiles(selectableItems.map(f => f.id));
      }
    } else {
      const selectableFiles = files.filter(f => 
        !f.is_chunk && 
        typeof f.id === 'number' && 
        supportedExtensions.includes(f.file_type)
      );
      if (selectedFiles.length === selectableFiles.length) {
        setSelectedFiles([]);
      } else {
        setSelectedFiles(selectableFiles.map(f => f.id));
      }
    }
  };

  const handleChunkSelected = async () => {
    if (selectedFiles.length === 0) {
      alert('请选择要切片的文件或文件夹');
      return;
    }
    
    setChunking(true);
    setChunkProgress({ current: 0, total: 0 });
    setChunkResults([]);
    setChunkComplete(false);
    
    try {
      const categoryIds = [];
      const fileIds = [];
      
      for (const id of selectedFiles) {
        if (typeof id === 'string' && id.startsWith('cat_')) {
          categoryIds.push(parseInt(id.replace('cat_', ''), 10));
        } else if (typeof id === 'number') {
          fileIds.push(id);
        }
      }
      
      let totalCompleted = 0;
      let totalFiles = 0;
      let totalResults = [];
      
      const processChunk = (data) => {
        if (data.type === 'start') {
          totalFiles += data.total;
          setChunkProgress({ current: totalCompleted, total: totalFiles });
        } else if (data.type === 'result') {
          totalCompleted += 1;
          totalResults.push({
            file_id: data.file_id,
            file_name: data.file_name,
            status: data.status,
            chunks: data.chunks,
            error: data.error
          });
          setChunkProgress({ current: totalCompleted, total: totalFiles });
          setChunkResults([...totalResults]);
        } else if (data.type === 'complete') {
          setChunkProgress({ current: totalCompleted, total: totalFiles });
        }
      };
      
      if (categoryIds.length > 0) {
        for (const catId of categoryIds) {
          await chunkFilesPost([], catId, processChunk);
        }
      }
      
      if (fileIds.length > 0) {
        await chunkFilesPost(fileIds, null, processChunk);
      }
      
      setChunkProgress({ current: totalFiles, total: totalFiles });
      setChunkComplete(true);
    } catch (error) {
      console.error('切片失败:', error);
      alert(error.message || '切片失败');
      setChunking(false);
      setChunkProgress(null);
    }
  };

  const closeChunkModal = () => {
    setChunking(false);
    setChunkProgress(null);
    setChunkResults([]);
    setChunkComplete(false);
    setSelectedFiles([]);
    loadFiles(currentCategoryId);
  };

  const closePreview = () => {
    setShowPreview(false);
    setPreviewFile(null);
  };

  return (
    <div className="knowledge-page">
      <div className="knowledge-page-header">
        <h2 className="page-title">知识库管理</h2>
      </div>

      <div className={`vector-search-section ${vectorResults.length > 0 ? 'has-results' : ''}`}>
        {vectorResults.length === 0 ? (
          <>
            <div className="vector-search-header">
              <h3>向量检索</h3>
              <span className="vector-hint">基于BGE-M3混合检索 + BGE-Reranker重排序</span>
            </div>
            <div className="vector-search-controls">
              <input
                type="text"
                className="vector-search-input"
                placeholder="输入查询内容，按回车搜索..."
                value={vectorQuery}
                onChange={(e) => setVectorQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleVectorSearch()}
              />
              <select 
                className="source-select"
                value={selectedSource}
                onChange={(e) => setSelectedSource(e.target.value)}
              >
                <option value="">全部来源</option>
                {sources.map(source => (
                  <option key={source.id} value={source.name}>{source.name}</option>
                ))}
              </select>
              <button 
                className="vector-search-btn"
                onClick={handleVectorSearch}
                disabled={vectorSearching}
              >
                {vectorSearching ? '检索中...' : '检索'}
              </button>
            </div>
            {vectorSearching && (
              <div className="vector-searching">
                <div className="searching-spinner"></div>
                <span>正在检索向量数据库...</span>
              </div>
            )}
            {!vectorSearching && vectorQuery && vectorResults.length === 0 && (
              <div className="no-results">
                <span>未找到相关内容</span>
              </div>
            )}
          </>
        ) : (
          <div className="vector-search-layout">
            <div className="vector-search-left">
              <div className="vector-search-header">
                <h3>向量检索</h3>
                <span className="vector-hint">BGE-M3 + Reranker</span>
              </div>
              <div className="vector-search-controls">
                <input
                  type="text"
                  className="vector-search-input"
                  placeholder="输入查询内容..."
                  value={vectorQuery}
                  onChange={(e) => setVectorQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleVectorSearch()}
                />
                <select 
                  className="source-select"
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                >
                  <option value="">全部来源</option>
                  {sources.map(source => (
                    <option key={source.id} value={source.name}>{source.name}</option>
                  ))}
                </select>
                <button 
                  className="vector-search-btn"
                  onClick={handleVectorSearch}
                  disabled={vectorSearching}
                >
                  {vectorSearching ? '检索中...' : '检索'}
                </button>
              </div>
              {vectorSearching && (
                <div className="vector-searching">
                  <div className="searching-spinner"></div>
                  <span>检索中...</span>
                </div>
              )}
            </div>
            <div className="vector-search-right">
              <div className="results-header">
                <span className="results-count">{vectorResults.length} 条结果</span>
              </div>
              <div className="results-list">
                {vectorResults.map((result, index) => (
                  <div 
                    key={result.id} 
                    className={`vector-result-item ${expandedResult === result.id ? 'expanded' : ''}`}
                    onClick={() => handleResultClick(result)}
                  >
                    <div className="result-header">
                      <span className="result-index">#{index + 1}</span>
                      <span className="result-source">{result.source}</span>
                    </div>
                    <div className="result-content">
                      {expandedResult === result.id 
                        ? result.content 
                        : result.content.length > 100 
                          ? result.content.substring(0, 100) + '...' 
                          : result.content
                      }
                    </div>
                    {expandedResult === result.id && (
                      <>
                        {result.parent_content && (
                          <div className="result-parent">
                            <div className="parent-label">父文档：</div>
                            <div className="parent-content">{result.parent_content}</div>
                          </div>
                        )}
                        {result.file_path && (
                          <div className="result-trace">
                            <button 
                              className="trace-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleTraceSource(result.file_path);
                              }}
                            >
                              📂 查看源文件
                            </button>
                            <span className="file-path-hint" title={result.file_path}>
                              {result.file_path.split('/').pop().split('\\').pop()}
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="knowledge-content-section">
        <div className="section-header">
          <h3>知识库文件</h3>
          <div className="section-actions">
            {selectedFiles.length > 0 && (
              <button 
                className="action-btn chunk-btn" 
                onClick={handleChunkSelected}
                disabled={chunking}
              >
                {chunking ? '切片中...' : `切片选中 (${selectedFiles.length})`}
              </button>
            )}
            {!currentCategoryId && (
              <button className="action-btn" onClick={() => setShowCreateModal(true)}>
                + 新建分类
              </button>
            )}
            {currentCategoryId && (
              <button className="action-btn primary" onClick={() => setShowUploadModal(true)}>
                上传文件
              </button>
            )}
          </div>
        </div>

        <div className="file-browser">
          <div className="path-tabs">
            <button 
              className={`path-tab ${currentCategoryId === null ? 'active' : ''}`}
              onClick={() => loadFiles(null)}
            >
              全部
            </button>
            {currentCategoryName && (
              <>
                <span className="path-separator">/</span>
                <button className="path-tab active">
                  {currentCategoryName}
                </button>
              </>
            )}
          </div>
        </div>

        <div className="files-section">
          {loading ? (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>加载中...</p>
            </div>
          ) : files.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">📁</div>
              <p>{currentCategoryId ? '该分类下暂无文件' : '暂无分类，请新建分类'}</p>
              {!currentCategoryId && (
                <button className="action-btn primary" onClick={() => setShowCreateModal(true)}>
                  新建分类
                </button>
              )}
            </div>
          ) : (
            <div className="files-table">
              <div className="files-table-header">
                <div className="file-col checkbox">
                  <input
                    type="checkbox"
                    checked={(() => {
                      if (currentCategoryId === null) {
                        const selectableItems = files.filter(f => f.is_dir && f.id.toString().startsWith('cat_'));
                        return selectableItems.length > 0 && selectedFiles.length === selectableItems.length;
                      } else {
                        const selectableFiles = files.filter(f => 
                          !f.is_chunk && 
                          typeof f.id === 'number' && 
                          supportedExtensions.includes(f.file_type)
                        );
                        return selectableFiles.length > 0 && selectedFiles.length === selectableFiles.length;
                      }
                    })()}
                    onChange={handleSelectAll}
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
                <div className="file-col name">名称</div>
                <div className="file-col type">类型</div>
                <div className="file-col status">状态</div>
                <div className="file-col actions">操作</div>
              </div>
              <div className="files-table-body">
                {files.map((file) => {
                  const canSelect = currentCategoryId === null 
                    ? (file.is_dir && file.id.toString().startsWith('cat_'))
                    : (!file.is_chunk && typeof file.id === 'number' && supportedExtensions.includes(file.file_type));
                  
                  return (
                    <div 
                      key={file.id} 
                      className={`files-table-row ${selectedFiles.includes(file.id) ? 'selected' : ''}`}
                      onClick={() => handleItemClick(file)}
                    >
                      <div className="file-col checkbox" onClick={(e) => e.stopPropagation()}>
                        {canSelect && (
                          <input
                            type="checkbox"
                            checked={selectedFiles.includes(file.id)}
                            onChange={(e) => handleSelectFile(file.id, e)}
                        />
                      )}
                    </div>
                    <div className="file-col name">
                      <span className="file-icon">{getFileIcon(file.file_type, file.is_dir)}</span>
                      <span className="file-name">{file.name}</span>
                    </div>
                    <div className="file-col type">
                      {file.is_dir ? '文件夹' : (file.file_type || '文件')}
                    </div>
                    <div className="file-col status">
                      {file.is_dir ? (
                        <span className="status-badge folder">文件夹</span>
                      ) : !supportedExtensions.includes(file.file_type) ? (
                        <span className="status-badge unsupported">不支持</span>
                      ) : file.is_chunk ? (
                        <span className="status-badge success">已切片</span>
                      ) : (
                        <span className="status-badge pending">未处理</span>
                      )}
                    </div>
                    <div className="file-col actions">
                      {!file.is_dir && !file.is_chunk && supportedExtensions.includes(file.file_type) && (
                        <button 
                          className="chunk-action-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFilePreview(file);
                          }}
                          title="预览文件"
                        >
                          👁️
                        </button>
                      )}
                      {!file.is_dir && file.is_chunk && (
                        <button 
                          className="chunk-action-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleViewChunks(file);
                          }}
                          title="查看切片"
                        >
                          📄
                        </button>
                      )}
                      {file.is_dir && file.category_id && (
                        <span className="action-hint">点击进入</span>
                      )}
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h4>创建分类</h4>
            <input
              type="text"
              value={newCategoryName}
              onChange={(e) => setNewCategoryName(e.target.value)}
              placeholder="请输入分类名称"
              autoFocus
            />
            <div className="modal-actions">
              <button onClick={() => setShowCreateModal(false)}>取消</button>
              <button onClick={handleCreateCategory} className="primary">创建</button>
            </div>
          </div>
        </div>
      )}

      {showUploadModal && (
        <div className="modal-overlay" onClick={() => setShowUploadModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h4>上传文件到 {currentCategoryName}</h4>
            <p className="upload-hint">支持的文件类型: {supportedExtensions.join(', ')}</p>
            <input
              type="file"
              accept={supportedExtensions.join(',')}
              onChange={(e) => setUploadingFile(e.target.files[0])}
            />
            {uploadingFile && <p className="selected-file">已选择: {uploadingFile.name}</p>}
            <div className="modal-actions">
              <button onClick={() => setShowUploadModal(false)}>取消</button>
              <button onClick={handleUploadFile} className="primary">上传</button>
            </div>
          </div>
        </div>
      )}

      {showPreview && previewFile && (
        <FilePreview 
          file={previewFile} 
          onClose={closePreview} 
        />
      )}

      {chunking && (
        <div className="modal-overlay">
          <div className="modal-content chunk-progress-modal">
            <h4>{chunkComplete ? '切片处理完成' : '文件切片处理中...'}</h4>
            <div className="chunk-progress-container">
              <div className="chunk-progress-bar">
                <div 
                  className="chunk-progress-fill"
                  style={{ width: chunkProgress ? `${(chunkProgress.current / chunkProgress.total) * 100}%` : '0%' }}
                ></div>
              </div>
              <div className="chunk-progress-text">
                {chunkProgress && `${chunkProgress.current} / ${chunkProgress.total}`}
              </div>
            </div>
            {chunkResults.length > 0 && (
              <div className="chunk-results">
                {chunkResults.map((result, index) => (
                  <div key={index} className={`chunk-result-item ${result.status}`}>
                    <span className="result-name">{result.file_name}</span>
                    <span className="result-status">
                      {result.status === 'success' ? `✓ ${result.chunks} 个切片` : `✗ ${result.error}`}
                    </span>
                  </div>
                ))}
              </div>
            )}
            {chunkComplete && (
              <div className="chunk-complete-actions">
                <button className="chunk-complete-btn" onClick={closeChunkModal}>
                  完成
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {showChunksModal && (
        <div className="modal-overlay" onClick={() => setShowChunksModal(false)}>
          <div className="modal-content chunks-modal" onClick={(e) => e.stopPropagation()}>
            <div className="chunks-modal-header">
              <h4>📄 {chunksFileName} - 切片列表</h4>
              <button className="close-btn" onClick={() => setShowChunksModal(false)}>×</button>
            </div>
            <div className="chunks-modal-body">
              {chunksLoading ? (
                <div className="chunks-loading">加载中...</div>
              ) : fileChunks.length === 0 ? (
                <div className="chunks-empty">暂无切片数据</div>
              ) : (
                <div className="chunks-results-list">
                  <div className="results-header">
                    <span className="results-count">{fileChunks.length} 个切片</span>
                  </div>
                  <div className="results-list">
                    {fileChunks.map((chunk, index) => (
                      <div 
                        key={index} 
                        className={`vector-result-item ${expandedChunk === index ? 'expanded' : ''}`}
                        onClick={() => setExpandedChunk(expandedChunk === index ? null : index)}
                      >
                        <div className="result-header">
                          <span className="result-index">#{index + 1}</span>
                          <span className="result-source">{chunk.source || '未知来源'}</span>
                        </div>
                        <div className="result-content">
                          {expandedChunk === index 
                            ? chunk.text 
                            : chunk.text.length > 100 
                              ? chunk.text.substring(0, 100) + '...' 
                              : chunk.text
                          }
                        </div>
                        {expandedChunk === index && (
                          <>
                            {chunk.parent_content && (
                              <div className="result-parent">
                                <div className="parent-label">父文档：</div>
                                <div className="parent-content">{chunk.parent_content}</div>
                              </div>
                            )}
                            {chunk.file_path && (
                              <div className="result-trace">
                                <button 
                                  className="trace-btn"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleTraceSource(chunk.file_path);
                                  }}
                                >
                                  📂 查看源文件
                                </button>
                                <span className="file-path-hint" title={chunk.file_path}>
                                  {chunk.file_path.split('/').pop().split('\\').pop()}
                                </span>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            <div className="chunks-modal-footer">
              <span className="chunks-count">共 {fileChunks.length} 个切片</span>
              <button className="primary" onClick={() => setShowChunksModal(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgePage;
