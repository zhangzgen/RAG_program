import React, { useState, useEffect } from 'react';
import { getCases, deleteCase } from '../api';
import './CasePage.css';

const CasePage = () => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [totalCount, setTotalCount] = useState(0);
  const [goodCount, setGoodCount] = useState(0);
  const [badCount, setBadCount] = useState(0);
  const [selectedCase, setSelectedCase] = useState(null);

  const loadCases = async () => {
    try {
      setLoading(true);
      const status = filter === 'all' ? null : (filter === 'good' ? 1 : 0);
      const data = await getCases(status, 100, 0);
      setCases(data.cases || []);
      setTotalCount(data.total || 0);
      setGoodCount(data.good_count || 0);
      setBadCount(data.bad_count || 0);
    } catch (error) {
      console.error('加载Case列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, [filter]);

  const handleDelete = async (caseId) => {
    if (window.confirm('确定要删除这条Case记录吗？')) {
      try {
        await deleteCase(caseId);
        loadCases();
        if (selectedCase?.id === caseId) {
          setSelectedCase(null);
        }
      } catch (error) {
        console.error('删除Case失败:', error);
        alert('删除失败');
      }
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const parseTraceData = (traceDataStr) => {
    if (!traceDataStr) return null;
    try {
      return JSON.parse(traceDataStr);
    } catch {
      return null;
    }
  };

  return (
    <div className="case-page">
      <div className="case-header">
        <h2 className="case-title">Case分析</h2>
        <div className="case-stats">
          <div className="stat-item total">
            <span className="stat-value">{totalCount}</span>
            <span className="stat-label">总计</span>
          </div>
          <div className="stat-item good">
            <span className="stat-value">{goodCount}</span>
            <span className="stat-label">GoodCase</span>
          </div>
          <div className="stat-item bad">
            <span className="stat-value">{badCount}</span>
            <span className="stat-label">BadCase</span>
          </div>
        </div>
      </div>

      <div className="case-filter">
        <button 
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          全部
        </button>
        <button 
          className={`filter-btn ${filter === 'good' ? 'active' : ''}`}
          onClick={() => setFilter('good')}
        >
          GoodCase
        </button>
        <button 
          className={`filter-btn ${filter === 'bad' ? 'active' : ''}`}
          onClick={() => setFilter('bad')}
        >
          BadCase
        </button>
      </div>

      <div className="case-content">
        <div className="case-list">
          {loading ? (
            <div className="loading-state">加载中...</div>
          ) : cases.length === 0 ? (
            <div className="empty-state">暂无Case记录</div>
          ) : (
            cases.map((caseItem) => (
              <div 
                key={caseItem.id}
                className={`case-card ${selectedCase?.id === caseItem.id ? 'selected' : ''}`}
                onClick={() => setSelectedCase(caseItem)}
              >
                <div className={`case-status-badge ${caseItem.status === 1 ? 'good' : 'bad'}`}>
                  {caseItem.status === 1 ? '👍 Good' : '👎 Bad'}
                </div>
                <div className="case-query">
                  <strong>问题:</strong> {caseItem.query.length > 100 ? caseItem.query.slice(0, 100) + '...' : caseItem.query}
                </div>
                <div className="case-answer">
                  <strong>回答:</strong> {caseItem.answer.length > 150 ? caseItem.answer.slice(0, 150) + '...' : caseItem.answer}
                </div>
                <div className="case-meta">
                  <span className="case-time">{formatDate(caseItem.created_at)}</span>
                  <button 
                    className="delete-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(caseItem.id);
                    }}
                  >
                    删除
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {selectedCase && (
          <div className="case-detail">
            <div className="detail-header">
              <h3>Case详情</h3>
              <button className="close-btn" onClick={() => setSelectedCase(null)}>×</button>
            </div>
            
            <div className="detail-section">
              <div className="detail-label">状态</div>
              <div className={`status-tag ${selectedCase.status === 1 ? 'good' : 'bad'}`}>
                {selectedCase.status === 1 ? 'GoodCase' : 'BadCase'}
              </div>
            </div>

            <div className="detail-section">
              <div className="detail-label">用户问题</div>
              <div className="detail-content query">{selectedCase.query}</div>
            </div>

            <div className="detail-section">
              <div className="detail-label">模型回答</div>
              <div className="detail-content answer">{selectedCase.answer}</div>
            </div>

            {selectedCase.session_id && (
              <div className="detail-section">
                <div className="detail-label">会话ID</div>
                <div className="detail-content">{selectedCase.session_id}</div>
              </div>
            )}

            <div className="detail-section">
              <div className="detail-label">创建时间</div>
              <div className="detail-content">{formatDate(selectedCase.created_at)}</div>
            </div>

            {selectedCase.trace_data && (
              <div className="detail-section">
                <div className="detail-label">执行链路</div>
                <div className="trace-data">
                  {(() => {
                    const trace = parseTraceData(selectedCase.trace_data);
                    if (!trace) return <div className="error">无法解析trace数据</div>;
                    
                    return (
                      <div className="trace-info">
                        {trace.fqa && trace.fqa.executed && (
                          <div className="trace-item">
                            <span className="trace-name">FQA搜索</span>
                            <span className={`trace-status ${trace.fqa.status}`}>{trace.fqa.status}</span>
                            <span className="trace-time">{trace.fqa.duration_ms}ms</span>
                          </div>
                        )}
                        {trace.query_classify && trace.query_classify.executed && (
                          <div className="trace-item">
                            <span className="trace-name">查询分类</span>
                            <span className={`trace-status ${trace.query_classify.status}`}>{trace.query_classify.status}</span>
                            <span className="trace-time">{trace.query_classify.duration_ms}ms</span>
                            {trace.query_classify.output && (
                              <span className="trace-output">→ {trace.query_classify.output}</span>
                            )}
                          </div>
                        )}
                        {trace.strategy_select && trace.strategy_select.executed && (
                          <div className="trace-item">
                            <span className="trace-name">策略选择</span>
                            <span className={`trace-status ${trace.strategy_select.status}`}>{trace.strategy_select.status}</span>
                            <span className="trace-time">{trace.strategy_select.duration_ms}ms</span>
                          </div>
                        )}
                        {trace.vector_retrieval && trace.vector_retrieval.executed && (
                          <div className="trace-item">
                            <span className="trace-name">向量检索</span>
                            <span className={`trace-status ${trace.vector_retrieval.status}`}>{trace.vector_retrieval.status}</span>
                            <span className="trace-time">{trace.vector_retrieval.duration_ms}ms</span>
                            {trace.vector_retrieval.output && (
                              <span className="trace-output">→ {trace.vector_retrieval.output}条结果</span>
                            )}
                          </div>
                        )}
                        {trace.llm && trace.llm.executed && (
                          <div className="trace-item">
                            <span className="trace-name">LLM生成</span>
                            <span className={`trace-status ${trace.llm.status}`}>{trace.llm.status}</span>
                            <span className="trace-time">{trace.llm.duration_ms}ms</span>
                          </div>
                        )}
                        {trace.total_duration_ms && (
                          <div className="trace-total">
                            总耗时: {trace.total_duration_ms}ms
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CasePage;
