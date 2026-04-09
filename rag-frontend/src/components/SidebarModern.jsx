import React, { useState, useEffect, forwardRef, useImperativeHandle, useMemo } from 'react';
import { getSessions, deleteSession, getSessionConversations, getCategories } from '../api';
import './SidebarModern.css';
import { sidebarIcon } from '../assets/icons';

const PROFESSIONAL_MENU_ITEMS = [
  { id: 'config', label: '配置中心' },
  { id: 'knowledge', label: '知识库' },
  { id: 'fqa', label: 'FQA 管理' },
  { id: 'case', label: 'Case 分析' },
  { id: 'assessment', label: '系统评估' },
];

const SidebarModern = forwardRef(({
  currentSessionId,
  onSessionSelect,
  onNewChat,
  isCollapsed,
  onLoadSession,
  currentUser,
  isAdmin,
  onLogout,
  mode,
  onModeChange,
  isHidden,
  onToggleHide,
  selectedCategory,
  onCategorySelect,
  professionalTab,
  onProfessionalTabChange,
}, ref) => {
  const [sessions, setSessions] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hoveredSession, setHoveredSession] = useState(null);
  const loadingSessionRef = React.useRef(null);

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

  const loadCategories = async () => {
    try {
      setLoading(true);
      const data = await getCategories();
      setCategories(data.categories || []);
    } catch (error) {
      console.error('Error loading categories:', error);
      setCategories([]);
    } finally {
      setLoading(false);
    }
  };

  useImperativeHandle(ref, () => ({
    loadSessions,
    loadCategories,
  }));

  useEffect(() => {
    if (mode === 'qa') {
      loadSessions();
      return;
    }

    if (isAdmin) {
      loadCategories();
      return;
    }

    setCategories([]);
  }, [mode, isAdmin]);

  useEffect(() => {
    return () => {
      loadingSessionRef.current = null;
    };
  }, []);

  const handleDeleteSession = async (sessionId, event) => {
    event.stopPropagation();
    if (!window.confirm('确定要删除这条对话吗？')) {
      return;
    }

    try {
      await deleteSession(sessionId);
      await loadSessions();
      if (currentSessionId === sessionId) {
        onNewChat();
      }
    } catch (error) {
      console.error('Error deleting session:', error);
      alert('删除对话失败');
    }
  };

  const handleSessionClick = async (sessionId) => {
    if (loadingSessionRef.current === sessionId) {
      return;
    }

    loadingSessionRef.current = sessionId;
    onSessionSelect(sessionId);

    try {
      setLoading(true);
      const sessionData = await getSessionConversations(sessionId);

      if (loadingSessionRef.current !== sessionId) {
        return;
      }

      onLoadSession(sessionData);
    } catch (error) {
      if (loadingSessionRef.current === sessionId) {
        console.error('Error loading session:', error);
        alert('加载对话失败');
      }
    } finally {
      if (loadingSessionRef.current === sessionId) {
        setLoading(false);
      }
    }
  };

  const handleCategoryClick = (category) => {
    if (selectedCategory?.id === category.id) {
      onCategorySelect(null);
      return;
    }

    onCategorySelect(category);
  };

  const getSessionTitle = (session) => {
    const firstQuery = String(session.first_query || '').trim();
    if (!firstQuery) {
      return '新对话';
    }

    return firstQuery.length > 24 ? `${firstQuery.slice(0, 24)}...` : firstQuery;
  };

  const sortedSessions = useMemo(() => {
    if (!sessions || sessions.length === 0) {
      return [];
    }

    return [...sessions].sort((a, b) => {
      const timeA = a.last_active ? new Date(a.last_active).getTime() : 0;
      const timeB = b.last_active ? new Date(b.last_active).getTime() : 0;
      return timeB - timeA;
    });
  }, [sessions]);

  const formatTime = (timestamp) => {
    if (!timestamp) {
      return '刚刚';
    }

    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (Number.isNaN(date.getTime()) || diff < 60000) {
      return '刚刚';
    }
    if (diff < 3600000) {
      return `${Math.floor(diff / 60000)} 分钟前`;
    }
    if (diff < 86400000) {
      return `${Math.floor(diff / 3600000)} 小时前`;
    }
    if (diff < 604800000) {
      return `${Math.floor(diff / 86400000)} 天前`;
    }

    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  const handleLogout = () => {
    if (window.confirm('确定要退出登录吗？')) {
      onLogout();
    }
  };

  if (isHidden) {
    return (
      <div className="sidebar-hidden-toggle">
        <button className="toggle-btn-visible" onClick={onToggleHide} title="展开侧边栏">
          <img src={sidebarIcon} alt="Toggle sidebar" className="toggle-icon" />
        </button>
      </div>
    );
  }

  return (
    <div className={`sidebar-modern ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header-modern">
        <div className="mode-switch-sidebar">
          <button
            className={`mode-btn-sidebar ${mode === 'qa' ? 'active' : ''}`}
            onClick={() => onModeChange('qa')}
          >
            {!isCollapsed && '问答模式'}
          </button>
          {isAdmin && (
            <button
              className={`mode-btn-sidebar ${mode === 'professional' ? 'active' : ''}`}
              onClick={() => onModeChange('professional')}
            >
              {!isCollapsed && '专业模式'}
            </button>
          )}
        </div>
        <button className="toggle-btn" onClick={onToggleHide} title="隐藏侧边栏">
          <img src={sidebarIcon} alt="Toggle sidebar" className="toggle-icon" />
        </button>
      </div>

      {mode === 'qa' && (
        <div className="new-chat-section">
          <button className="new-chat-btn-modern" onClick={onNewChat}>
            <svg width="9" height="9" viewBox="0 0 18 18" fill="none">
              <path d="M9 3.75V14.25M3.75 9H14.25" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            {!isCollapsed && <span>开启新对话</span>}
          </button>
        </div>
      )}

      <div className="sessions-section-modern">
        {!isCollapsed && mode === 'qa' && (
          <div className="sessions-header">
            <span className="sessions-title">历史对话</span>
          </div>
        )}

        {!isCollapsed && mode === 'professional' && isAdmin && (
          <div className="professional-menu">
            {PROFESSIONAL_MENU_ITEMS.map((item) => (
              <div
                key={item.id}
                className={`professional-menu-item ${professionalTab === item.id ? 'active' : ''}`}
                onClick={() => onProfessionalTabChange(item.id)}
              >
                <span className="menu-label">{item.label}</span>
              </div>
            ))}
          </div>
        )}

        {mode === 'professional' && professionalTab === 'knowledge' && isAdmin && !isCollapsed && (
          <div className="knowledge-subsection">
            <div className="sessions-header">
              <span className="sessions-title">知识库分类</span>
            </div>
          </div>
        )}

        <div className="sessions-list-modern">
          {loading ? (
            <div className="loading-state-modern">
              <div className="loading-spinner-modern"></div>
            </div>
          ) : mode === 'qa' ? (
            sortedSessions.length === 0 ? (
              !isCollapsed && <div className="empty-state-modern">暂无历史对话</div>
            ) : (
              sortedSessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`session-item-modern ${currentSessionId === session.session_id ? 'active' : ''}`}
                  onClick={() => handleSessionClick(session.session_id)}
                  onMouseEnter={() => setHoveredSession(session.session_id)}
                  onMouseLeave={() => setHoveredSession(null)}
                >
                  <div className="session-icon-modern">
                    {currentSessionId === session.session_id ? '💬' : '🗨️'}
                  </div>
                  {!isCollapsed && (
                    <div className="session-content-modern">
                      <div className="session-title-modern">{getSessionTitle(session)}</div>
                      <div className="session-time-modern">{formatTime(session.last_active)}</div>
                    </div>
                  )}
                  {hoveredSession === session.session_id && !isCollapsed && (
                    <button
                      className="delete-btn-modern"
                      onClick={(event) => handleDeleteSession(session.session_id, event)}
                      title="删除对话"
                    >
                      <svg width="7" height="7" viewBox="0 0 14 14" fill="none">
                        <path d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                      </svg>
                    </button>
                  )}
                </div>
              ))
            )
          ) : professionalTab === 'knowledge' && isAdmin ? (
            categories.length === 0 ? (
              !isCollapsed && <div className="empty-state-modern">暂无分类</div>
            ) : (
              categories.map((category) => (
                <div
                  key={category.id}
                  className={`session-item-modern ${selectedCategory?.id === category.id ? 'active' : ''}`}
                  onClick={() => handleCategoryClick(category)}
                >
                  <div className="session-icon-modern">
                    {selectedCategory?.id === category.id ? '📂' : '📁'}
                  </div>
                  {!isCollapsed && (
                    <div className="session-content-modern">
                      <div className="session-title-modern">{category.category}</div>
                    </div>
                  )}
                </div>
              ))
            )
          ) : (
            !isCollapsed && <div className="empty-state-modern">请选择左侧菜单项</div>
          )}
        </div>
      </div>

      <div className="sidebar-footer-modern">
        {!isCollapsed && currentUser && (
          <div className="user-section">
            <div className="user-avatar">👤</div>
            <div className="user-info">
              <div className="user-name">{currentUser.email}</div>
              <button className="logout-btn" onClick={handleLogout}>退出登录</button>
            </div>
          </div>
        )}
        {isCollapsed && currentUser && (
          <button className="logout-btn-collapsed" onClick={handleLogout} title="退出登录">⎋</button>
        )}
      </div>
    </div>
  );
});

export default SidebarModern;
