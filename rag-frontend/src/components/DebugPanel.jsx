import React, { useState } from 'react';
import './DebugPanel.css';

const DebugPanel = ({ isVisible }) => {
  const [logs, setLogs] = useState([
    { type: 'info', message: '系统初始化完成', timestamp: new Date() },
    { type: 'info', message: '知识库加载成功', timestamp: new Date() },
  ]);
  const [queryInfo, setQueryInfo] = useState({
    query: '',
    retrievalTime: 0,
    generationTime: 0,
    totalTokens: 0,
    sources: [],
  });

  const clearLogs = () => {
    setLogs([]);
  };

  const addLog = (type, message) => {
    setLogs(prev => [...prev, { type, message, timestamp: new Date() }]);
  };

  if (!isVisible) return null;

  return (
    <div className="debug-panel">
      <div className="debug-header">
        <h4>调试面板</h4>
        <button className="clear-logs-btn" onClick={clearLogs}>
          清空日志
        </button>
      </div>

      <div className="debug-section">
        <div className="section-title">查询信息</div>
        <div className="query-info">
          <div className="info-row">
            <span className="info-label">检索耗时:</span>
            <span className="info-value">{queryInfo.retrievalTime}ms</span>
          </div>
          <div className="info-row">
            <span className="info-label">生成耗时:</span>
            <span className="info-value">{queryInfo.generationTime}ms</span>
          </div>
          <div className="info-row">
            <span className="info-label">Token数量:</span>
            <span className="info-value">{queryInfo.totalTokens}</span>
          </div>
        </div>
      </div>

      <div className="debug-section">
        <div className="section-title">检索来源</div>
        <div className="sources-list">
          {queryInfo.sources.length === 0 ? (
            <div className="empty-sources">暂无检索来源</div>
          ) : (
            queryInfo.sources.map((source, index) => (
              <div key={index} className="source-item">
                <span className="source-index">{index + 1}</span>
                <span className="source-name">{source.name}</span>
                <span className="source-score">{(source.score * 100).toFixed(1)}%</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="debug-section">
        <div className="section-title">系统日志</div>
        <div className="logs-container">
          {logs.length === 0 ? (
            <div className="empty-logs">暂无日志</div>
          ) : (
            logs.map((log, index) => (
              <div key={index} className={`log-item log-${log.type}`}>
                <span className="log-time">
                  {log.timestamp.toLocaleTimeString()}
                </span>
                <span className="log-message">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default DebugPanel;
