import React, { useState, useEffect, useRef } from 'react';
import SidebarModern from './components/SidebarModern';
import ChatAreaModern from './components/ChatAreaModern';
import KnowledgePage from './components/KnowledgePage';
import ConfigPage from './components/ConfigPage';
import FqaPage from './components/FqaPage';
import CasePage from './components/CasePage';
import Login from './components/Login';
import { verifyToken } from './api';
import './AppModern.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [currentSessionId, setCurrentSessionId] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isSidebarHidden, setIsSidebarHidden] = useState(false);
  const [sessionData, setSessionData] = useState(null);
  const chatAreaRef = useRef(null);
  const sidebarRef = useRef(null);
  
  const [mode, setMode] = useState('qa');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [professionalTab, setProfessionalTab] = useState('knowledge');

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      const userStr = localStorage.getItem('user');

      if (token && userStr) {
        try {
          const result = await verifyToken();
          if (result.valid) {
            setIsAuthenticated(true);
            setCurrentUser(JSON.parse(userStr));
          } else {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
          }
        } catch (error) {
          console.error('Token验证失败:', error);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      setAuthChecking(false);
    };

    checkAuth();
  }, []);

  useEffect(() => {
    const savedCollapsed = localStorage.getItem('sidebarCollapsed');
    if (savedCollapsed !== null) {
      setIsSidebarCollapsed(JSON.parse(savedCollapsed));
    }
    
    const savedHidden = localStorage.getItem('sidebarHidden');
    if (savedHidden !== null) {
      setIsSidebarHidden(JSON.parse(savedHidden));
    }
    
    const savedMode = localStorage.getItem('appMode');
    if (savedMode) {
      setMode(savedMode);
    }
  }, []);

  const handleToggleCollapse = () => {
    const newState = !isSidebarCollapsed;
    setIsSidebarCollapsed(newState);
    localStorage.setItem('sidebarCollapsed', JSON.stringify(newState));
  };

  const handleToggleHide = () => {
    const newState = !isSidebarHidden;
    setIsSidebarHidden(newState);
    localStorage.setItem('sidebarHidden', JSON.stringify(newState));
  };

  const handleNewChat = () => {
    setCurrentSessionId('');
    setSessionData(null);
    if (chatAreaRef.current && chatAreaRef.current.clearMessages) {
      chatAreaRef.current.clearMessages();
    }
  };

  const handleSessionSelect = (sessionId) => {
    setCurrentSessionId(sessionId);
  };

  const handleLoadSession = (data) => {
    setSessionData(data);
  };

  const handleLoginSuccess = (response) => {
    setIsAuthenticated(true);
    setCurrentUser({
      user_id: response.user_id,
      email: response.email
    });
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    setCurrentUser(null);
    setCurrentSessionId('');
    setSessionData(null);
  };

  const handleModeChange = (newMode) => {
    setMode(newMode);
    localStorage.setItem('appMode', newMode);
    setIsSidebarCollapsed(false);
    setIsSidebarHidden(false);
    if (newMode === 'professional') {
      setSelectedCategory(null);
      setProfessionalTab('knowledge');
    }
  };

  const handleCategorySelect = (category) => {
    setSelectedCategory(category);
  };

  const handleProfessionalTabChange = (tab) => {
    setProfessionalTab(tab);
    if (tab !== 'knowledge') {
      setSelectedCategory(null);
    }
  };

  const handleSessionCreated = async (sessionId) => {
    setCurrentSessionId(sessionId);
    if (sidebarRef.current && sidebarRef.current.loadSessions) {
      await sidebarRef.current.loadSessions();
    }
  };

  if (authChecking) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>加载中...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className={`app-modern-container ${isSidebarHidden ? 'sidebar-hidden' : ''}`}>
      <SidebarModern
        ref={sidebarRef}
        currentSessionId={currentSessionId}
        onSessionSelect={handleSessionSelect}
        onNewChat={handleNewChat}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={handleToggleCollapse}
        onLoadSession={handleLoadSession}
        currentUser={currentUser}
        onLogout={handleLogout}
        mode={mode}
        onModeChange={handleModeChange}
        isHidden={isSidebarHidden}
        onToggleHide={handleToggleHide}
        selectedCategory={selectedCategory}
        onCategorySelect={handleCategorySelect}
        professionalTab={professionalTab}
        onProfessionalTabChange={handleProfessionalTabChange}
      />
      
      <div className="main-modern-area">
        {mode === 'qa' ? (
          <ChatAreaModern
            ref={chatAreaRef}
            sessionData={sessionData}
            onSessionCreated={handleSessionCreated}
          />
        ) : (
          professionalTab === 'knowledge' ? (
            <KnowledgePage />
          ) : professionalTab === 'config' ? (
            <ConfigPage />
          ) : professionalTab === 'fqa' ? (
            <FqaPage />
          ) : (
            <CasePage />
          )
        )}
      </div>
    </div>
  );
}

export default App;
