import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { queryAPI, createSession, updateConversationStatus } from '../api';
import './ChatAreaModern.css';

let messageIdCounter = 0;
const generateMessageId = () => `msg_${Date.now()}_${++messageIdCounter}`;

const ChatAreaModern = forwardRef(({ sessionData, onSessionCreated }, ref) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [hasStarted, setHasStarted] = useState(false);
  const [sessionCreated, setSessionCreated] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [messageStatus, setMessageStatus] = useState({});
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  const streamingContentRef = useRef('');
  const streamingMessageIndexRef = useRef(-1);

  const copyToClipboard = async (text, index) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleStatusUpdate = async (conversationId, status) => {
    try {
      await updateConversationStatus(conversationId, status);
      setMessageStatus(prev => ({
        ...prev,
        [conversationId]: status
      }));
    } catch (err) {
      console.error('更新状态失败:', err);
    }
  };

  useImperativeHandle(ref, () => ({
    clearMessages: () => {
      setMessages([]);
      setHasStarted(false);
      setSessionCreated(false);
      streamingContentRef.current = '';
      streamingMessageIndexRef.current = -1;
    }
  }));

  useEffect(() => {
    if (sessionData === null) {
      setMessages([]);
      setHasStarted(false);
      setSessionCreated(false);
      setSessionId('');
      setMessageStatus({});
      return;
    }
    
    if (!sessionData || !sessionData.session_id) {
      return;
    }
    
    if (sessionData.conversations && Array.isArray(sessionData.conversations) && sessionData.conversations.length > 0) {
      const formattedMessages = [];
      const statusMap = {};
      sessionData.conversations.forEach(conv => {
        formattedMessages.push({ 
          id: generateMessageId(),
          role: 'user', 
          content: conv.query,
          conversationId: conv.id
        });
        formattedMessages.push({ 
          id: generateMessageId(),
          role: 'assistant', 
          content: conv.answer,
          conversationId: conv.id
        });
        if (conv.id && conv.status !== undefined) {
          statusMap[conv.id] = conv.status;
        }
      });
      setMessages(formattedMessages);
      setMessageStatus(statusMap);
      setHasStarted(true);
      setSessionCreated(true);
      setSessionId(sessionData.session_id);
    } else {
      setMessages([]);
      setHasStarted(true);
      setSessionCreated(true);
      setSessionId(sessionData.session_id);
    }
  }, [sessionData]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 优化的流式数据处理函数
  const processStreamData = useCallback((data, messageIndex) => {
    if (data.token) {
      // 使用函数式更新确保数据一致性
      setMessages(prev => {
        const newMessages = [...prev];
        if (newMessages[messageIndex]) {
          // 数据去重：检查是否已经包含该token
          const currentContent = newMessages[messageIndex].content;
          if (!currentContent.endsWith(data.token)) {
            newMessages[messageIndex] = {
              ...newMessages[messageIndex],
              content: currentContent + data.token
            };
          }
        }
        return newMessages;
      });
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setHasStarted(true);
    
    const userMsgIndex = messages.length;
    const userMsgId = generateMessageId();
    setMessages(prev => [...prev, { id: userMsgId, role: 'user', content: userMessage }]);
    setIsLoading(true);
    
    let isNewSession = false;

    try {
      let currentSessionId = sessionId;
      if (!sessionCreated) {
        const sessionResponse = await createSession();
        currentSessionId = sessionResponse.session_id;
        setSessionId(currentSessionId);
        setSessionCreated(true);
        isNewSession = true;
      }

      const assistantMsgIndex = userMsgIndex + 1;
      const assistantMsgId = generateMessageId();
      setMessages(prev => [...prev, { id: assistantMsgId, role: 'assistant', content: '' }]);
      streamingMessageIndexRef.current = assistantMsgIndex;
      streamingContentRef.current = '';

      const stream = await queryAPI(userMessage, null, currentSessionId);
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      
      let buffer = '';
      let streamComplete = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.error) {
                throw new Error(data.error);
              }
              if (data.token) {
                processStreamData(data, assistantMsgIndex);
              }
              if (data.is_complete) {
                setIsLoading(false);
                if (data.conversation_id) {
                  setMessages(prev => {
                    const newMessages = [...prev];
                    if (newMessages[assistantMsgIndex]) {
                      newMessages[assistantMsgIndex] = {
                        ...newMessages[assistantMsgIndex],
                        conversationId: data.conversation_id
                      };
                    }
                    return newMessages;
                  });
                }
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
              setMessages(prev => {
                const newMessages = [...prev];
                if (newMessages[assistantMsgIndex]) {
                  newMessages[assistantMsgIndex] = {
                    ...newMessages[assistantMsgIndex],
                    content: newMessages[assistantMsgIndex].content + `\n[数据解析错误: ${e.message}]`
                  };
                }
                return newMessages;
              });
              setIsLoading(false);
            }
          }
        }
      }
      
      if (buffer.trim().startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.trim().slice(6));
          if (data.token) {
            processStreamData(data, assistantMsgIndex);
          }
          if (data.is_complete) {
            setIsLoading(false);
            streamComplete = true;
            if (data.conversation_id) {
              setMessages(prev => {
                const newMessages = [...prev];
                if (newMessages[assistantMsgIndex]) {
                  newMessages[assistantMsgIndex] = {
                    ...newMessages[assistantMsgIndex],
                    conversationId: data.conversation_id
                  };
                }
                return newMessages;
              });
            }
          }
        } catch (e) {
          console.error('Error parsing remaining buffer:', e);
        }
      }
      
      if (streamComplete && onSessionCreated) {
        onSessionCreated(currentSessionId);
      }
      
    } catch (error) {
      console.error('Error:', error);
      const errorMsgId = generateMessageId();
      setMessages(prev => [...prev, { 
        id: errorMsgId,
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
    <div className="chat-area-modern">
      <div className="chat-messages-modern">
        {!hasStarted && messages.length === 0 && (
          <div className="welcome-container-modern">
            <div className="welcome-content-modern">
              <div className="welcome-icon-modern">
                <svg width="24" height="24" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M24 4L4 14L24 24L44 14L24 4Z" fill="#5534DA" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round"/>
                  <path d="M4 34L24 44L44 34" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round"/>
                  <path d="M4 24L24 34L44 24" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round"/>
                </svg>
              </div>
              <h2 className="welcome-title-modern">今天有什么可以帮到你？</h2>
            </div>
          </div>
        )}

        {messages.map((message, index) => {
          const isLastMessage = index === messages.length - 1;
          const isStreaming = isLoading && isLastMessage && message.role === 'assistant' && !message.content;
          const isStreamingContent = isLoading && isLastMessage && message.role === 'assistant' && message.content;
          const messageKey = message.id || `msg_${index}`;
          
          return (
            <div
              key={messageKey}
              className={`message-modern ${message.role === 'user' ? 'user-message-modern' : 'assistant-message-modern'} ${isStreaming ? 'loading-modern' : ''}`}
            >
              <div className="message-avatar-modern">
                {message.role === 'user' ? (
                  <div className="user-avatar-modern">👤</div>
                ) : (
                  <div className="ai-avatar-modern">
                    <svg width="10" height="10" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M24 4L4 14L24 24L44 14L24 4Z" fill="#5534DA" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round"/>
                      <path d="M4 34L24 44L44 34" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round"/>
                      <path d="M4 24L24 34L44 24" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round"/>
                    </svg>
                  </div>
                )}
              </div>
              <div className="message-content-modern">
                {isStreaming ? (
                  <div className="typing-indicator-modern">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                ) : (
                  <>
                    <div className="message-text-wrapper">
                      {message.role === 'assistant' ? (
                        <div className={`message-text-modern markdown-content ${isStreamingContent ? 'streaming' : ''}`}>
                          <ReactMarkdown 
                            key={`${messageKey}_md`}
                            remarkPlugins={[remarkGfm]}
                            skipHtml={true}
                          >
                            {message.content || ''}
                          </ReactMarkdown>
                          {isStreamingContent && <span className="streaming-cursor"></span>}
                        </div>
                      ) : (
                        <div className="message-text-modern">
                          {message.content}
                        </div>
                      )}
                      {!isStreamingContent && message.content && (
                        <button 
                          className="copy-btn-modern"
                          onClick={() => copyToClipboard(message.content, messageKey)}
                          title="复制消息"
                        >
                          {copiedIndex === messageKey ? (
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                          ) : (
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                          )}
                        </button>
                      )}
                    </div>
                    {!isStreamingContent && message.content && message.role === 'assistant' && message.conversationId && (
                      <div className="message-footer-modern">
                        <div className="feedback-buttons-modern">
                          <button 
                            className={`feedback-btn-modern like-btn ${messageStatus[message.conversationId] === 1 ? 'active' : ''}`}
                            onClick={() => handleStatusUpdate(message.conversationId, messageStatus[message.conversationId] === 1 ? 0 : 1)}
                            title="赞"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill={messageStatus[message.conversationId] === 1 ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                            </svg>
                            <span>赞</span>
                          </button>
                          <button 
                            className={`feedback-btn-modern dislike-btn ${messageStatus[message.conversationId] === 2 ? 'active' : ''}`}
                            onClick={() => handleStatusUpdate(message.conversationId, messageStatus[message.conversationId] === 2 ? 0 : 2)}
                            title="踩"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill={messageStatus[message.conversationId] === 2 ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                              <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                            </svg>
                            <span>踩</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      <div className={`input-container-modern ${!hasStarted && messages.length === 0 ? 'input-centered' : ''}`}>
        <form onSubmit={handleSubmit} className="input-form-modern">
          <div className="input-wrapper-modern">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="给DeepSeek发送消息"
              className="chat-input-modern"
              disabled={isLoading}
            />
            <div className="input-actions-modern">
              <button
                type="button"
                className="action-btn-modern"
                title="附件"
              >
                <svg width="10" height="10" viewBox="0 0 20 20" fill="none">
                  <path d="M10 1.6665L2.5 6.6665V13.3332L10 18.3332L17.5 13.3332V6.6665L10 1.6665Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M10 10.8332C10.6904 10.8332 11.25 10.2736 11.25 9.58317C11.25 8.89275 10.6904 8.33317 10 8.33317C9.30958 8.33317 8.75 8.89275 8.75 9.58317C8.75 10.2736 9.30958 10.8332 10 10.8332Z" stroke="currentColor" strokeWidth="1.5"/>
                  <path d="M5 7.49983V12.4998" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  <path d="M15 7.49983V12.4998" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
              </button>
              <button
                type="submit"
                className="send-btn-modern"
                disabled={isLoading || !input.trim()}
              >
                <svg width="10" height="10" viewBox="0 0 20 20" fill="none">
                  <path d="M3.33301 10L16.6663 3.33337L10 16.6667L9.16634 10.8333L3.33301 10Z" fill="currentColor"/>
                </svg>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
});

export default ChatAreaModern;
