import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { queryAPI } from '../api';
import './ChatArea.css';

const ChatArea = ({ sessionId: propSessionId, onNewChat }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [sourceFilter, setSourceFilter] = useState('');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (propSessionId) {
      setSessionId(propSessionId);
    } else {
      setSessionId(generateSessionId());
    }
  }, [propSessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const generateSessionId = () => {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const stream = await queryAPI(userMessage, sourceFilter || null, sessionId);
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = { role: 'assistant', content: '' };
      setMessages(prev => [...prev, assistantMessage]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.error) {
                throw new Error(data.error);
              }
              if (data.token) {
                setMessages(prev => {
                  const newMessages = [...prev];
                  const lastMessage = newMessages[newMessages.length - 1];
                  lastMessage.content += data.token;
                  return newMessages;
                });
              }
              if (data.is_complete) {
                setIsLoading(false);
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                lastMessage.content += `\n[数据解析错误: ${e.message}]`;
                return newMessages;
              });
              setIsLoading(false);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `错误: ${error.message}` 
      }]);
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-area">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-container">
            <div className="welcome-content">
              <div className="welcome-icon">🤖</div>
              <h2 className="welcome-title">欢迎使用智能问答系统</h2>
              <p className="welcome-subtitle">基于 RAG + MySQL + Redis 的专业问答平台</p>
              <div className="welcome-features">
                <div className="feature-item">
                  <span className="feature-icon">💡</span>
                  <span className="feature-text">智能检索</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">⚡</span>
                  <span className="feature-text">实时响应</span>
                </div>
                <div className="feature-item">
                  <span className="feature-icon">📚</span>
                  <span className="feature-text">多学科支持</span>
                </div>
              </div>
            </div>
          </div>
        )}
        {messages.map((message, index) => {
          const isLastMessage = index === messages.length - 1;
          const isStreaming = isLoading && isLastMessage && message.role === 'assistant' && !message.content;
          const isStreamingContent = isLoading && isLastMessage && message.role === 'assistant' && message.content;
          
          return (
            <div
              key={index}
              className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'} ${isStreaming ? 'loading' : ''}`}
            >
              <div className="message-avatar">
                {message.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-content">
                <div className="message-header">
                  <span className="message-role">
                    {message.role === 'user' ? '您' : 'AI 助手'}
                  </span>
                </div>
                {isStreaming ? (
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                ) : message.role === 'assistant' ? (
                  <div className={`message-text markdown-content ${isStreamingContent ? 'streaming' : ''}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                    {isStreamingContent && <span className="streaming-cursor"></span>}
                  </div>
                ) : (
                  <div className="message-text">
                    {message.content}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form onSubmit={handleSubmit} className="chat-input-form">
          <div className="input-wrapper">
            <div className="input-actions-left">
              <button
                type="button"
                className="action-btn"
                onClick={onNewChat}
                title="新建对话"
              >
                <span className="action-icon">➕</span>
              </button>
            </div>
            
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的问题..."
              className="chat-input"
              disabled={isLoading}
            />
            
            <div className="input-actions-right">
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value)}
                className="source-filter"
                disabled={isLoading}
              >
                <option value="">全部学科</option>
                <option value="ai">人工智能</option>
                <option value="java">Java</option>
              </select>
              <button
                type="submit"
                className="send-btn"
                disabled={isLoading || !input.trim()}
              >
                <span className="send-icon">➤</span>
              </button>
            </div>
          </div>
          <div className="input-hint">
            <span>按 Enter 发送，Shift + Enter 换行</span>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ChatArea;
