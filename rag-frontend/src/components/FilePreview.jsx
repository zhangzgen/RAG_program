import React, { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './FilePreview.css';

pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const EXT_TO_LANGUAGE = {
  '.js': 'javascript',
  '.jsx': 'jsx',
  '.ts': 'typescript',
  '.tsx': 'tsx',
  '.py': 'python',
  '.java': 'java',
  '.c': 'c',
  '.cpp': 'cpp',
  '.h': 'c',
  '.hpp': 'cpp',
  '.cs': 'csharp',
  '.go': 'go',
  '.rs': 'rust',
  '.rb': 'ruby',
  '.php': 'php',
  '.swift': 'swift',
  '.kt': 'kotlin',
  '.scala': 'scala',
  '.r': 'r',
  '.sql': 'sql',
  '.sh': 'bash',
  '.bash': 'bash',
  '.zsh': 'bash',
  '.ps1': 'powershell',
  '.json': 'json',
  '.xml': 'xml',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.toml': 'toml',
  '.ini': 'ini',
  '.css': 'css',
  '.scss': 'scss',
  '.less': 'less',
  '.html': 'html',
  '.vue': 'vue',
  '.svelte': 'svelte',
};

const FilePreview = ({ file, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [content, setContent] = useState(null);
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(0.8);
  const [copySuccess, setCopySuccess] = useState(false);

  const fileType = file?.file_type || 'unknown';
  const fileExt = file?.file_ext || file?.file_type || '';
  const fileName = file?.file_name || file?.name || '未知文件';
  const fileSize = file?.file_size;

  const isImage = fileType === 'image';
  const isPdf = fileType === 'pdf';
  const isMarkdown = fileType === 'markdown';
  const isCode = fileType === 'code';
  const isText = fileType === 'text';
  const isWord = fileType === 'word';
  const isUnsupported = ['excel', 'ppt', 'unknown'].includes(fileType);

  useEffect(() => {
    if (!file) return;

    const loadContent = async () => {
      setLoading(true);
      setError(null);

      try {
        if (isImage) {
          if (file.content) {
            setContent(`data:${file.mime_type || 'image/png'};base64,${file.content}`);
          } else {
            setError('图片内容为空');
          }
        } else if (isPdf) {
          if (file.content) {
            const binaryString = atob(file.content);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            setContent(new Blob([bytes], { type: 'application/pdf' }));
          } else {
            setError('PDF内容为空');
          }
        } else if (isWord) {
          if (file.content) {
            setContent(file.content);
          } else if (file.message) {
            setError(file.message);
          } else {
            setError('Word内容为空');
          }
        } else if (isMarkdown || isCode || isText) {
          if (file.content !== undefined && file.content !== null) {
            setContent(file.content);
          } else {
            setError('文件内容为空');
          }
        }
      } catch (err) {
        setError(err.message || '加载文件失败');
      } finally {
        setLoading(false);
      }
    };

    loadContent();
  }, [file, isImage, isPdf, isWord, isMarkdown, isCode, isText]);

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
    setPageNumber(1);
  };

  const handlePrevPage = () => {
    setPageNumber(prev => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setPageNumber(prev => Math.min(prev + 1, numPages || 1));
  };

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.2, 3.0));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.2, 0.5));
  };

  const handleCopy = async () => {
    if (content) {
      await navigator.clipboard.writeText(content);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      onClose();
    } else if (isPdf) {
      if (e.key === 'ArrowLeft') handlePrevPage();
      else if (e.key === 'ArrowRight') handleNextPage();
      else if (e.key === '+' || e.key === '=') handleZoomIn();
      else if (e.key === '-') handleZoomOut();
    }
  }, [onClose, isPdf]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const getLanguage = () => {
    return EXT_TO_LANGUAGE[fileExt.toLowerCase()] || 'text';
  };

  const getFileIcon = () => {
    if (isPdf) return '📄';
    if (isImage) return '🖼️';
    if (isMarkdown) return '📝';
    if (isCode) return '💻';
    if (isText) return '📃';
    if (fileType === 'word') return '📝';
    if (fileType === 'excel') return '📊';
    if (fileType === 'ppt') return '📽';
    return '📄';
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="preview-loading">
          <div className="preview-spinner"></div>
          <span>加载中...</span>
        </div>
      );
    }

    if (error) {
      return (
        <div className="preview-error">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      );
    }

    if (isUnsupported) {
      return (
        <div className="unsupported-preview">
          <span className="unsupported-icon">📁</span>
          <p>{file.message || '不支持预览此文件类型'}</p>
          <span className="file-type-hint">文件类型: {fileExt || fileType}</span>
        </div>
      );
    }

    if (isImage) {
      return (
        <div className="image-container">
          <img src={content} alt={fileName} className="preview-image" />
        </div>
      );
    }

    if (isPdf) {
      return (
        <div className="pdf-container">
          <div className="pdf-viewer">
            <Document
              file={content}
              onLoadSuccess={onDocumentLoadSuccess}
              loading={<div className="pdf-loading">加载PDF...</div>}
              error={<div className="pdf-error">PDF加载失败</div>}
            >
              <Page 
                pageNumber={pageNumber} 
                scale={scale}
                renderTextLayer={false}
                renderAnnotationLayer={false}
              />
            </Document>
          </div>
          <div className="pdf-controls">
            <div className="pdf-nav">
              <button onClick={handlePrevPage} disabled={pageNumber <= 1} className="pdf-btn">
                ◀
              </button>
              <span className="pdf-page-info">
                {pageNumber} / {numPages || '-'}
              </span>
              <button onClick={handleNextPage} disabled={pageNumber >= (numPages || 1)} className="pdf-btn">
                ▶
              </button>
            </div>
            <div className="pdf-zoom">
              <button onClick={handleZoomOut} className="pdf-btn" title="缩小">−</button>
              <span className="zoom-level">{Math.round(scale * 100)}%</span>
              <button onClick={handleZoomIn} className="pdf-btn" title="放大">+</button>
            </div>
          </div>
        </div>
      );
    }

    if (isWord) {
      return (
        <div className="word-container">
          <div className="content-toolbar">
            <button className="copy-btn" onClick={handleCopy}>
              {copySuccess ? '✓ 已复制' : '复制内容'}
            </button>
          </div>
          <div 
            className="word-content"
            dangerouslySetInnerHTML={{ __html: content }}
          />
        </div>
      );
    }

    if (isMarkdown) {
      return (
        <div className="markdown-container">
          <div className="content-toolbar">
            <button className="copy-btn" onClick={handleCopy}>
              {copySuccess ? '✓ 已复制' : '复制内容'}
            </button>
          </div>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      );
    }

    if (isCode) {
      return (
        <div className="code-container">
          <div className="code-header">
            <span className="code-language">{getLanguage()}</span>
            <button className="copy-btn" onClick={handleCopy}>
              {copySuccess ? '✓ 已复制' : '复制代码'}
            </button>
          </div>
          <SyntaxHighlighter
            language={getLanguage()}
            style={oneLight}
            showLineNumbers
            wrapLines
            customStyle={{
              margin: 0,
              borderRadius: '0 0 6px 6px',
              fontSize: '12px',
              maxHeight: '60vh',
            }}
          >
            {content}
          </SyntaxHighlighter>
        </div>
      );
    }

    if (isText) {
      return (
        <div className="text-container">
          <div className="content-toolbar">
            <button className="copy-btn" onClick={handleCopy}>
              {copySuccess ? '✓ 已复制' : '复制内容'}
            </button>
          </div>
          <pre className="text-content">{content}</pre>
        </div>
      );
    }

    return (
      <div className="unsupported-preview">
        <p>无法预览此文件</p>
      </div>
    );
  };

  if (!file) return null;

  return (
    <div className="file-preview-overlay" onClick={onClose}>
      <div className="file-preview-modal" onClick={(e) => e.stopPropagation()}>
        <div className="file-preview-header">
          <div className="file-info">
            <span className="file-icon">{getFileIcon()}</span>
            <span className="file-name">{fileName}</span>
            {fileSize && (
              <span className="file-size">{formatFileSize(fileSize)}</span>
            )}
          </div>
          <div className="file-actions">
            <button className="close-btn" onClick={onClose} title="关闭 (Esc)">
              ✕
            </button>
          </div>
        </div>
        <div className="file-preview-body">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};

export default FilePreview;
