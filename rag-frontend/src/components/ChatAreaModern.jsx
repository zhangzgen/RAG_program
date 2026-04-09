import React, {
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  forwardRef,
} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { arrowDownIcon, arrowRightIcon, thinkingIcon } from '../assets/icons';
import {
  createSession,
  queryAPI,
  regenerateConversationStream,
  updateConversationStatus,
} from '../api';
import './ChatAreaModern.css';

let messageIdCounter = 0;
const generateMessageId = () => `msg_${Date.now()}_${++messageIdCounter}`;

const normalizeMarkdownForRender = (rawContent = '') => {
  let content = String(rawContent).replace(/\r\n?/g, '\n');

  const lineBreakCount = (content.match(/\n/g) || []).length;
  const escapedLineBreakCount = (content.match(/\\n/g) || []).length;
  if (escapedLineBreakCount > 0 && lineBreakCount === 0) {
    content = content.replace(/\\n/g, '\n');
  }
  content = content.replace(/\\t/g, '\t');

  // Normalize common malformed model output: "**1.xxx" (no closing "**")
  content = content.replace(/^\s*\*\*(\d+\.[^*\n]+)\s*$/gm, '### $1');

  return content;
};

const readSSEStream = async (stream, onMessage) => {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) {
        continue;
      }
      onMessage(JSON.parse(line.slice(6)));
    }
  }

  const finalLine = buffer.trim();
  if (finalLine.startsWith('data: ')) {
    onMessage(JSON.parse(finalLine.slice(6)));
  }
};

const ChatAreaModern = forwardRef(({ sessionData, onSessionCreated, isAdmin }, ref) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [hasStarted, setHasStarted] = useState(false);
  const [sessionCreated, setSessionCreated] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [copiedCodeIndex, setCopiedCodeIndex] = useState(null);
  const [messageStatus, setMessageStatus] = useState({});
  const [expandedThinking, setExpandedThinking] = useState({});

  const messagesEndRef = useRef(null);
  const thinkingEndRef = useRef(null);
  const inputRef = useRef(null);
  const messagesRef = useRef([]);
  const prevMsgCountRef = useRef(0);
  const mountedRef = useRef(true);
  const activeStreamRunRef = useRef(0);
  const streamingIdRef = useRef(null);
  const thinkingBufRef = useRef('');
  const contentBufRef = useRef('');
  const rafIdRef = useRef(null);

  const resetStreamingState = useCallback(() => {
    activeStreamRunRef.current += 1;
    streamingIdRef.current = null;
    thinkingBufRef.current = '';
    contentBufRef.current = '';
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }
  }, []);

  const scrollMessagesToBottom = useCallback((behavior = 'smooth') => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior });
    });
  }, []);

  const scrollThinkingToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      thinkingEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    });
  }, []);

  const copyToClipboard = async (text, key) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(key);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (error) {
      console.error('复制失败:', error);
    }
  };

  const handleStatusUpdate = async (conversationId, status) => {
    try {
      await updateConversationStatus(conversationId, status);
      setMessageStatus((prev) => ({
        ...prev,
        [conversationId]: status,
      }));
    } catch (error) {
      console.error('更新状态失败:', error);
    }
  };

  const scheduleFlush = useCallback((messageId, runId) => {
    if (rafIdRef.current) {
      return;
    }

    rafIdRef.current = requestAnimationFrame(() => {
      rafIdRef.current = null;
      if (!mountedRef.current || activeStreamRunRef.current !== runId) {
        return;
      }

      const thinking = thinkingBufRef.current;
      const content = contentBufRef.current;

      setMessages((prev) => prev.map((message) => (
        message.id === messageId
          ? { ...message, thinking, content }
          : message
      )));

      if (thinking && !content) {
        scrollThinkingToBottom();
      } else {
        scrollMessagesToBottom();
      }
    });
  }, [scrollMessagesToBottom, scrollThinkingToBottom]);

  const startStreamRun = useCallback((messageId) => {
    const runId = activeStreamRunRef.current + 1;
    activeStreamRunRef.current = runId;
    streamingIdRef.current = messageId;
    thinkingBufRef.current = '';
    contentBufRef.current = '';
    setIsLoading(true);
    return runId;
  }, []);

  const finalizeStreamRun = useCallback((messageId, runId, conversationId = null) => {
    if (!mountedRef.current || activeStreamRunRef.current !== runId) {
      return;
    }

    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }

    streamingIdRef.current = null;
    setIsLoading(false);
    setMessages((prev) => prev.map((message) => (
      message.id === messageId
        ? {
            ...message,
            thinking: thinkingBufRef.current,
            content: contentBufRef.current,
            showThinking: false,
            conversationId: conversationId || message.conversationId,
          }
        : message
    )));
  }, []);

  const failStreamRun = useCallback((messageId, runId, error) => {
    if (!mountedRef.current || activeStreamRunRef.current !== runId) {
      return;
    }

    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;
    }

    streamingIdRef.current = null;
    setIsLoading(false);
    setMessages((prev) => prev.map((message) => (
      message.id === messageId
        ? {
            ...message,
            thinking: '',
            content: `错误: ${error.message}`,
            showThinking: false,
          }
        : message
    )));
  }, []);

  const runAssistantStream = useCallback(async ({
    streamFactory,
    messageId,
    onComplete,
  }) => {
    const runId = startStreamRun(messageId);
    let streamCompleted = false;

    try {
      const stream = await streamFactory();
      await readSSEStream(stream, (data) => {
        if (activeStreamRunRef.current !== runId) {
          return;
        }

        if (data.error) {
          throw new Error(data.error);
        }

        if (data.token) {
          if (data.token_type === 'thinking') {
            thinkingBufRef.current += data.token;
          } else if (data.token_type === 'answer') {
            contentBufRef.current += data.token;
          }
          scheduleFlush(messageId, runId);
        }

        if (data.is_complete) {
          streamCompleted = true;
          finalizeStreamRun(messageId, runId, data.conversation_id);
          if (onComplete) {
            onComplete(data);
          }
        }
      });

      if (!streamCompleted) {
        finalizeStreamRun(messageId, runId);
      }
    } catch (error) {
      console.error('Streaming error:', error);
      failStreamRun(messageId, runId, error);
    }
  }, [failStreamRun, finalizeStreamRun, scheduleFlush, startStreamRun]);

  const handleRegenerate = async (messageId) => {
    if (isLoading) {
      return;
    }

    const currentMessages = messagesRef.current;
    const targetMessage = currentMessages.find((message) => message.id === messageId);
    if (!targetMessage?.conversationId) {
      return;
    }

    setMessages((prev) => prev.map((message) => (
      message.id === messageId
        ? { ...message, content: '', thinking: '', showThinking: true }
        : message
    )));

    await runAssistantStream({
      messageId,
      streamFactory: () => regenerateConversationStream(targetMessage.conversationId),
    });
  };

  useImperativeHandle(ref, () => ({
    clearMessages: () => {
      resetStreamingState();
      setMessages([]);
      setHasStarted(false);
      setSessionCreated(false);
      setSessionId('');
      setIsLoading(false);
    },
  }), [resetStreamingState]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      resetStreamingState();
    };
  }, [resetStreamingState]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    const newCount = messages.length;
    if (newCount > prevMsgCountRef.current) {
      scrollMessagesToBottom();
    }
    prevMsgCountRef.current = newCount;
  }, [messages.length, scrollMessagesToBottom]);

  useEffect(() => {
    resetStreamingState();
    setIsLoading(false);

    if (sessionData === null) {
      setMessages([]);
      setHasStarted(false);
      setSessionCreated(false);
      setSessionId('');
      setMessageStatus({});
      return;
    }

    if (!sessionData?.session_id) {
      return;
    }

    if (Array.isArray(sessionData.conversations) && sessionData.conversations.length > 0) {
      const nextMessages = [];
      const nextStatusMap = {};

      sessionData.conversations.forEach((conversation) => {
        nextMessages.push({
          id: generateMessageId(),
          role: 'user',
          content: conversation.query,
          conversationId: conversation.id,
        });
        nextMessages.push({
          id: generateMessageId(),
          role: 'assistant',
          content: conversation.answer,
          conversationId: conversation.id,
          thinking: (() => {
            try {
              if (!conversation.trace_data) {
                return '';
              }
              const trace = JSON.parse(conversation.trace_data);
              return trace?.llm?.thinking_content || '';
            } catch {
              return '';
            }
          })(),
        });

        if (conversation.id && conversation.status !== undefined) {
          nextStatusMap[conversation.id] = conversation.status;
        }
      });

      setMessages(nextMessages);
      setMessageStatus(nextStatusMap);
      setHasStarted(true);
      setSessionCreated(true);
      setSessionId(sessionData.session_id);
      return;
    }

    setMessages([]);
    setHasStarted(true);
    setSessionCreated(true);
    setSessionId(sessionData.session_id);
  }, [resetStreamingState, sessionData]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!input.trim() || isLoading) {
      return;
    }

    const userMessage = input.trim().replace(/\n/g, '');
    setInput('');
    setHasStarted(true);

    const userMsgId = generateMessageId();
    const assistantMsgId = generateMessageId();

    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: 'user', content: userMessage },
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        thinking: '',
        showThinking: true,
      },
    ]);

    try {
      let currentSessionId = sessionId;
      if (!sessionCreated) {
        const sessionResponse = await createSession();
        currentSessionId = sessionResponse.session_id;
        setSessionId(currentSessionId);
        setSessionCreated(true);
      }

      await runAssistantStream({
        messageId: assistantMsgId,
        streamFactory: () => queryAPI(userMessage, null, currentSessionId),
        onComplete: () => {
          if (onSessionCreated) {
            onSessionCreated(currentSessionId);
          }
        },
      });
    } catch (error) {
      console.error('Submit error:', error);
      setIsLoading(false);
      setMessages((prev) => prev.map((message) => (
        message.id === assistantMsgId
          ? { ...message, content: `错误: ${error.message}`, showThinking: false }
          : message
      )));
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && event.shiftKey) {
      event.preventDefault();
      const { selectionStart, selectionEnd } = event.target;
      const currentValue = input;
      const nextValue = currentValue.slice(0, selectionStart) + '\n' + currentValue.slice(selectionEnd);
      setInput(nextValue);
      requestAnimationFrame(() => {
        if (inputRef.current) {
          inputRef.current.selectionStart = selectionStart + 1;
          inputRef.current.selectionEnd = selectionStart + 1;
        }
      });
      return;
    }

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
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
                  <path d="M24 4L4 14L24 24L44 14L24 4Z" fill="#5534DA" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round" />
                  <path d="M4 34L24 44L44 34" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round" />
                  <path d="M4 24L24 34L44 24" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round" />
                </svg>
              </div>
              <h2 className="welcome-title-modern">今天有什么可以帮到你？</h2>
            </div>
          </div>
        )}

        {messages.map((message, index) => {
          const isLastMessage = index === messages.length - 1;
          const isCurrentStreamingMessage = isLoading && message.id === streamingIdRef.current;
          const isStreaming = isCurrentStreamingMessage && message.role === 'assistant' && !message.content && !message.thinking;
          const shouldRenderMarkdown = message.role === 'assistant' && !isCurrentStreamingMessage;
          const normalizedMessageContent = normalizeMarkdownForRender(message.content || '');
          const messageKey = message.id || `msg_${index}`;

          return (
            <div
              key={messageKey}
              className={`message-modern ${message.role === 'user' ? 'user-message-modern' : 'assistant-message-modern'} ${isStreaming ? 'loading-modern' : ''}`}
            >
              <div className="message-avatar-modern">
                {message.role === 'user' ? (
                  <div className="user-avatar-modern">U</div>
                ) : (
                  <div className="ai-avatar-modern">
                    <svg width="10" height="10" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M24 4L4 14L24 24L44 14L24 4Z" fill="#5534DA" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round" />
                      <path d="M4 34L24 44L44 34" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round" />
                      <path d="M4 24L24 34L44 24" stroke="#5534DA" strokeWidth="2" strokeLinejoin="round" />
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
                    {message.role === 'assistant' && message.thinking && (
                      <div className="thinking-panel-modern">
                        <button
                          type="button"
                          className={`thinking-toggle-modern ${(expandedThinking[message.id] ?? !!message.showThinking) ? 'expanded' : ''}`}
                          onClick={() => setExpandedThinking((prev) => ({
                            ...prev,
                            [message.id]: !(prev[message.id] ?? !!message.showThinking),
                          }))}
                        >
                          <img src={thinkingIcon} className="thinking-icon-modern" alt="" />
                          <span className="thinking-badge-modern">思考过程</span>
                          <img
                            src={(expandedThinking[message.id] ?? !!message.showThinking) ? arrowDownIcon : arrowRightIcon}
                            className="thinking-arrow-modern"
                            alt=""
                          />
                        </button>
                        {(expandedThinking[message.id] ?? !!message.showThinking) && (
                          <div className="thinking-content-modern">
                            <span style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{message.thinking}</span>
                            {isCurrentStreamingMessage && isLastMessage && !message.content && <span className="streaming-cursor"></span>}
                            {isCurrentStreamingMessage && isLastMessage && !message.content && <div ref={thinkingEndRef} />}
                          </div>
                        )}
                      </div>
                    )}

                    <div className="message-text-wrapper">
                      {shouldRenderMarkdown ? (
                        <div className="message-text-modern markdown-content">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            skipHtml={true}
                            components={{
                              pre({ children, ...props }) {
                                const extractText = (node) => {
                                  if (typeof node === 'string') return node;
                                  if (Array.isArray(node)) return node.map(extractText).join('');
                                  if (node?.props?.children) return extractText(node.props.children);
                                  return '';
                                };
                                const codeText = extractText(children).replace(/\n$/, '');
                                const codeKey = `code_${message.id}_${codeText.slice(0, 20)}`;
                                return (
                                  <div className="code-block-wrapper">
                                    <pre {...props}>{children}</pre>
                                    <button
                                      className="code-copy-btn"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        navigator.clipboard.writeText(codeText);
                                        setCopiedCodeIndex(codeKey);
                                        setTimeout(() => setCopiedCodeIndex(null), 2000);
                                      }}
                                      title="复制代码"
                                    >
                                      {copiedCodeIndex === codeKey ? (
                                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                                      ) : (
                                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                      )}
                                    </button>
                                  </div>
                                );
                              },
                            }}
                          >
                            {normalizedMessageContent}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <div className={`message-text-modern ${message.role === 'assistant' ? 'markdown-content streaming' : ''}`}>
                          <span style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{normalizedMessageContent}</span>
                          {isCurrentStreamingMessage && <span className="streaming-cursor"></span>}
                        </div>
                      )}
                    </div>

                    {message.role === 'assistant' && message.content && !isCurrentStreamingMessage && (
                      <div className="message-footer-modern">
                        <div className="feedback-buttons-modern">
                          <button
                            className="feedback-btn-modern copy-inline-btn"
                            onClick={() => copyToClipboard(message.content, messageKey)}
                            title="复制"
                          >
                            {copiedIndex === messageKey ? (
                              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                            ) : (
                              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                            )}
                          </button>

                          <button
                            className="feedback-btn-modern regen-btn"
                            onClick={() => handleRegenerate(message.id)}
                            disabled={isLoading}
                            title="重新生成"
                          >
                            <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="1 4 1 10 7 10"></polyline><path d="M3.51 15a9 9 0 1 0 .49-3.85"></path></svg>
                          </button>

                          {isAdmin && message.conversationId && (
                            <>
                              <button
                                className={`feedback-btn-modern like-btn ${messageStatus[message.conversationId] === 1 ? 'active' : ''}`}
                                onClick={() => handleStatusUpdate(message.conversationId, messageStatus[message.conversationId] === 1 ? 0 : 1)}
                                title="点赞"
                              >
                                <svg width="8" height="8" viewBox="0 0 24 24" fill={messageStatus[message.conversationId] === 1 ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                                  <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path>
                                </svg>
                                <span>点赞</span>
                              </button>

                              <button
                                className={`feedback-btn-modern dislike-btn ${messageStatus[message.conversationId] === 2 ? 'active' : ''}`}
                                onClick={() => handleStatusUpdate(message.conversationId, messageStatus[message.conversationId] === 2 ? 0 : 2)}
                                title="点踩"
                              >
                                <svg width="8" height="8" viewBox="0 0 24 24" fill={messageStatus[message.conversationId] === 2 ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                                  <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"></path>
                                </svg>
                                <span>点踩</span>
                              </button>
                            </>
                          )}
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
            <textarea
              ref={inputRef}
              value={input}
              onChange={(event) => {
                setInput(event.target.value);
                event.target.style.height = 'auto';
                event.target.style.height = `${Math.min(event.target.scrollHeight, 120)}px`;
              }}
              onKeyDown={handleKeyDown}
              placeholder="给 DeepSeek 发送消息"
              className="chat-input-modern"
              disabled={isLoading}
              rows={1}
            />
            <div className="input-actions-modern">
              <button
                type="button"
                className="action-btn-modern"
                title="附件"
              >
                <svg width="10" height="10" viewBox="0 0 20 20" fill="none">
                  <path d="M10 1.6665L2.5 6.6665V13.3332L10 18.3332L17.5 13.3332V6.6665L10 1.6665Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M10 10.8332C10.6904 10.8332 11.25 10.2736 11.25 9.58317C11.25 8.89275 10.6904 8.33317 10 8.33317C9.30958 8.33317 8.75 8.89275 8.75 9.58317C8.75 10.2736 9.30958 10.8332 10 10.8332Z" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M5 7.49983V12.4998" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M15 7.49983V12.4998" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
              </button>
              <button
                type="submit"
                className="send-btn-modern"
                disabled={isLoading || !input.trim()}
              >
                <svg width="10" height="10" viewBox="0 0 20 20" fill="none">
                  <path d="M3.33301 10L16.6663 3.33337L10 16.6667L9.16634 10.8333L3.33301 10Z" fill="currentColor" />
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
