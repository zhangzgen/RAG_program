import React, { useState, useRef, useEffect } from 'react';
import { getSessions, deleteSession } from '../api';
import './Sidebar.css';

const Sidebar = ({ currentSessionId, onSessionSelect, onNewChat, isCollapsed, onToggleCollapse }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [width, setWidth] = useState(280);
  const [isResizing, setIsResizing] = useState(false);
  const [hoveredSession, setHoveredSession] = useState(null);
  const sidebarRef = useRef(null);
  const resizerRef = useRef(null);

  const minWidth = 200;
  const maxWidth = 500;

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await getSessions();
      setSessions(data);
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMouseDown = (e) => {
    setIsResizing(true);
    e.preventDefault();
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;

      const newWidth = e.clientX - sidebarRef.current.getBoundingClientRect().left;
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        setWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    if (window.confirm('确定要删除这个对话吗？')) {
      try {
        await deleteSession(sessionId);
        await loadSessions();
      } catch (error) {
        console.error('Error deleting session:', error);
        alert('删除对话失败');
      }
    }
  };

  const getSessionTitle = (session) => {
    const sessionId = session.session_id;
    return `对话 ${sessionId.slice(0, 8)}`;
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) {
      return '刚刚';
    } else if (diff < 3600000) {
      return `${Math.floor(diff / 60000)}分钟前`;
    } else if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)}小时前`;
    } else if (diff < 604800000) {
      return `${Math.floor(diff / 86400000)}天前`;
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }
  };

  return (
    <div
      ref={sidebarRef}
      className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}
      style={{ width: isCollapsed ? '60px' : `${width}px` }}
    >
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          <span className="new-chat-icon">+</span>
          {!isCollapsed && <span className="new-chat-text">新建对话</span>}
        </button>
        <button className="collapse-btn" onClick={onToggleCollapse}>
          {isCollapsed ? '→' : '←'}
        </button>
      </div>

      <div className="sidebar-content">
        <div className="sidebar-section">
          <div className="section-header">
            {!isCollapsed && <span className="section-title">历史对话</span>}
            {!isCollapsed && (
              <button className="refresh-btn" onClick={loadSessions} disabled={loading}>
                {loading ? '...' : '↻'}
              </button>
            )}
          </div>

          <div className="sessions-list">
            {loading ? (
              <div className="loading-state">
                <div className="loading-spinner"></div>
              </div>
            ) : sessions.length === 0 ? (
              <div className="empty-state">
                {!isCollapsed && <p>暂无历史对话</p>}
              </div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`session-item ${currentSessionId === session.session_id ? 'active' : ''}`}
                  onClick={() => onSessionSelect(session.session_id)}
                  onMouseEnter={() => setHoveredSession(session.session_id)}
                  onMouseLeave={() => setHoveredSession(null)}
                >
                  <div className="session-main">
                    <div className="session-icon">
                      {currentSessionId === session.session_id ? '💬' : '💭'}
                    </div>
                    {!isCollapsed && (
                      <div className="session-info">
                        <div className="session-title">{getSessionTitle(session)}</div>
                        <div className="session-time">{formatTime(session.last_active)}</div>
                      </div>
                    )}
                  </div>
                  {hoveredSession === session.session_id && !isCollapsed && (
                    <button
                      className="delete-btn"
                      onClick={(e) => handleDeleteSession(session.session_id, e)}
                      title="删除对话"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {!isCollapsed && (
        <div className="sidebar-footer">
          <div className="footer-info">
            <span className="footer-text">智能问答系统</span>
          </div>
        </div>
      )}

      <div
        ref={resizerRef}
        className={`resizer ${isResizing ? 'resizing' : ''}`}
        onMouseDown={handleMouseDown}
        style={{ display: isCollapsed ? 'none' : 'block' }}
      >
        <div className="resizer-handle"></div>
      </div>
    </div>
  );
};

export default Sidebar;
