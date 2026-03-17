import React, { useState, useEffect } from 'react';
import { getCategoryFiles, createCategory, uploadFile, deleteFile, deleteCategory, previewFile } from '../api';
import './KnowledgeFileArea.css';

const FILE_ICONS = {
  '.pdf': '📄', '.doc': '📝', '.docx': '📝', '.xls': '📊', '.xlsx': '📊',
  '.ppt': '📽', '.pptx': '📽', '.txt': '📃', '.md': '📝', '.py': '🐍',
  '.js': '📜', '.jsx': '⚛️', '.ts': '📘', '.tsx': '⚛️', '.json': '📋',
  '.html': '🌐', '.css': '🎨', '.jpg': '🖼', '.jpeg': '🖼', '.png': '🖼',
  '.gif': '🖼', '.svg': '🎨', '.zip': '📦', '.rar': '📦', default: '📄'
};

const getFileIcon = (fileType, isDir) => {
  if (isDir) return '📁';
  return FILE_ICONS[fileType] || FILE_ICONS.default;
};

const KnowledgeFileArea = ({ selectedCategory }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [uploadingFile, setUploadingFile] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    if (selectedCategory) {
      loadFiles();
    } else {
      setFiles([]);
    }
  }, [selectedCategory]);

  const loadFiles = async () => {
    if (!selectedCategory) return;
    try {
      setLoading(true);
      const data = await getCategoryFiles(selectedCategory.id);
      setFiles(data.files || []);
    } catch (error) {
      console.error('加载文件失败:', error);
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
    } catch (error) {
      alert(error.message || '创建分类失败');
    }
  };

  const handleUploadFile = async () => {
    if (!uploadingFile || !selectedCategory) {
      alert('请选择文件');
      return;
    }
    try {
      setLoading(true);
      await uploadFile(selectedCategory.id, uploadingFile);
      setShowUploadModal(false);
      setUploadingFile(null);
      await loadFiles();
    } catch (error) {
      alert(error.message || '上传文件失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteFile = async (fileId, e) => {
    e.stopPropagation();
    if (!window.confirm('确定要删除此文件吗？')) return;
    try {
      await deleteFile(fileId);
      await loadFiles();
    } catch (error) {
      alert(error.message || '删除文件失败');
    }
  };

  const handleFileClick = async (file) => {
    if (file.is_dir) return;
    try {
      setLoading(true);
      const data = await previewFile(file.id);
      setPreviewContent(data);
      setShowPreview(true);
    } catch (error) {
      alert(error.message || '预览文件失败');
    } finally {
      setLoading(false);
    }
  };

  const closePreview = () => {
    setShowPreview(false);
    setPreviewContent(null);
  };

  return (
    <div className="knowledge-file-area">
      <div className="file-area-header">
        <h3>{selectedCategory ? selectedCategory.category : '知识库'}</h3>
        <div className="header-actions">
          <button className="action-btn" onClick={() => setShowCreateModal(true)}>
            + 新建分类
          </button>
          {selectedCategory && (
            <button className="action-btn primary" onClick={() => setShowUploadModal(true)}>
              上传文件
            </button>
          )}
        </div>
      </div>

      <div className="file-area-content">
        {!selectedCategory ? (
          <div className="empty-state">
            <div className="empty-icon">📚</div>
            <p>请从左侧选择一个分类查看文件</p>
          </div>
        ) : loading ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>加载中...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📁</div>
            <p>该分类下暂无文件</p>
            <button className="action-btn primary" onClick={() => setShowUploadModal(true)}>
              上传文件
            </button>
          </div>
        ) : (
          <div className="file-grid">
            {files.map((file) => (
              <div 
                key={file.id} 
                className="file-card"
                onClick={() => handleFileClick(file)}
              >
                <div className="file-icon">{getFileIcon(file.file_type, file.is_dir)}</div>
                <div className="file-info">
                  <div className="file-name">{file.name}</div>
                  <div className="file-meta">
                    {file.is_chunk && <span className="chunk-badge">已切片</span>}
                  </div>
                </div>
                {!file.is_dir && (
                  <button 
                    className="delete-file-btn"
                    onClick={(e) => handleDeleteFile(file.id, e)}
                    title="删除文件"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
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
            <h4>上传文件</h4>
            <input
              type="file"
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

      {showPreview && previewContent && (
        <div className="preview-overlay" onClick={closePreview}>
          <div className="preview-content" onClick={(e) => e.stopPropagation()}>
            <div className="preview-header">
              <h4>{previewContent.file_name}</h4>
              <button onClick={closePreview}>×</button>
            </div>
            <div className="preview-body">
              {previewContent.file_type === 'text' && (
                <pre className="text-preview">{previewContent.content}</pre>
              )}
              {previewContent.file_type === 'image' && (
                <img 
                  src={`data:${previewContent.mime_type};base64,${previewContent.content}`} 
                  alt={previewContent.file_name}
                  className="image-preview"
                />
              )}
              {previewContent.file_type !== 'text' && previewContent.file_type !== 'image' && (
                <div className="unsupported-preview">
                  <p>{previewContent.message || '不支持预览此文件类型'}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeFileArea;
