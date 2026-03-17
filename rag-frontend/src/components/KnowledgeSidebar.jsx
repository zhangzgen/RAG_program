import React, { useState, useEffect } from 'react';
import { getCategories, createCategory, deleteCategory, getCategoryFiles, uploadFile, deleteFile, previewFile } from '../api';
import './KnowledgeSidebar.css';

const FILE_ICONS = {
  '.pdf': '📄',
  '.doc': '📝',
  '.docx': '📝',
  '.xls': '📊',
  '.xlsx': '📊',
  '.ppt': '📽',
  '.pptx': '📽',
  '.txt': '📃',
  '.md': '📝',
  '.py': '🐍',
  '.js': '📜',
  '.jsx': '⚛️',
  '.ts': '📘',
  '.tsx': '⚛️',
  '.json': '📋',
  '.html': '🌐',
  '.css': '🎨',
  '.jpg': '🖼',
  '.jpeg': '🖼',
  '.png': '🖼',
  '.gif': '🖼',
  '.svg': '🎨',
  '.zip': '📦',
  '.rar': '📦',
  '.mp4': '🎬',
  '.mp3': '🎵',
  default: '📄'
};

const getFileIcon = (fileType, isDir) => {
  if (isDir) return '📁';
  return FILE_ICONS[fileType] || FILE_ICONS.default;
};

const KnowledgeSidebar = ({ onFilePreview }) => {
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      setLoading(true);
      const data = await getCategories();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('加载分类失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCategoryClick = async (category) => {
    if (selectedCategory?.id === category.id) {
      setSelectedCategory(null);
      setFiles([]);
      return;
    }
    
    setSelectedCategory(category);
    try {
      setLoading(true);
      const data = await getCategoryFiles(category.id);
      setFiles(data.files || []);
    } catch (error) {
      console.error('加载文件失败:', error);
      setFiles([]);
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
    } catch (error) {
      alert(error.message || '创建分类失败');
    }
  };

  const handleDeleteCategory = async (categoryId, e) => {
    e.stopPropagation();
    if (!window.confirm('确定要删除此分类吗？这将删除分类下的所有文件。')) return;
    
    try {
      await deleteCategory(categoryId);
      if (selectedCategory?.id === categoryId) {
        setSelectedCategory(null);
        setFiles([]);
      }
      await loadCategories();
    } catch (error) {
      alert(error.message || '删除分类失败');
    }
  };

  const handleFileClick = async (file) => {
    if (file.is_dir) {
      return;
    }
    
    try {
      setLoading(true);
      const data = await previewFile(file.id);
      setPreviewContent(data);
      setShowPreview(true);
      if (onFilePreview) {
        onFilePreview(data);
      }
    } catch (error) {
      alert(error.message || '预览文件失败');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadFile = async () => {
    if (!uploadingFile) {
      alert('请选择文件');
      return;
    }

    try {
      setLoading(true);
      await uploadFile(selectedCategory.id, uploadingFile);
      setShowUploadModal(false);
      setUploadingFile(null);
      const data = await getCategoryFiles(selectedCategory.id);
      setFiles(data.files || []);
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
      const data = await getCategoryFiles(selectedCategory.id);
      setFiles(data.files || []);
    } catch (error) {
      alert(error.message || '删除文件失败');
    }
  };

  const closePreview = () => {
    setShowPreview(false);
    setPreviewContent(null);
  };

  return (
    <div className="knowledge-sidebar">
      <div className="knowledge-header">
        <h3>知识库</h3>
        <button 
          className="create-category-btn"
          onClick={() => setShowCreateModal(true)}
          title="创建分类"
        >
          +
        </button>
      </div>

      <div className="categories-list">
        {loading && categories.length === 0 ? (
          <div className="loading-state">加载中...</div>
        ) : categories.length === 0 ? (
          <div className="empty-state">暂无分类，点击上方按钮创建</div>
        ) : (
          categories.map((category) => (
            <div key={category.id} className="category-section">
              <div 
                className={`category-item ${selectedCategory?.id === category.id ? 'active' : ''}`}
                onClick={() => handleCategoryClick(category)}
              >
                <span className="category-icon">📁</span>
                <span className="category-name">{category.category}</span>
                <button 
                  className="delete-category-btn"
                  onClick={(e) => handleDeleteCategory(category.id, e)}
                  title="删除分类"
                >
                  ×
                </button>
              </div>
              
              {selectedCategory?.id === category.id && (
                <div className="files-section">
                  <div className="files-header">
                    <span>文件列表</span>
                    <button 
                      className="upload-btn"
                      onClick={() => setShowUploadModal(true)}
                    >
                      上传文件
                    </button>
                  </div>
                  
                  {loading ? (
                    <div className="loading-state">加载中...</div>
                  ) : files.length === 0 ? (
                    <div className="empty-files">暂无文件</div>
                  ) : (
                    <div className="files-list">
                      {files.map((file) => (
                        <div 
                          key={file.id} 
                          className="file-item"
                          onClick={() => handleFileClick(file)}
                        >
                          <span className="file-icon">{getFileIcon(file.file_type, file.is_dir)}</span>
                          <span className="file-name">{file.name}</span>
                          {file.is_chunk && <span className="chunk-badge">已切片</span>}
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
              )}
            </div>
          ))
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

export default KnowledgeSidebar;
