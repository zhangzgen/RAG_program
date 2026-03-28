import React, { useState, useEffect, useCallback } from 'react';
import { getCases, getCaseDetail, getVectorDetail, downloadCases } from '../api';
import './CasePage.css';

const CasePage = () => {
  const [activeTab, setActiveTab] = useState('good');
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [selectedCase, setSelectedCase] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const [expandedSections, setExpandedSections] = useState({});
  const [expandedResult, setExpandedResult] = useState(null);
  const [vectorDetails, setVectorDetails] = useState({});

  const loadCases = useCallback(async () => {
    try {
      setLoading(true);
      const status = activeTab === 'good' ? 1 : 2;
      const data = await getCases(status, page, pageSize);
      setCases(data.cases || []);
      setTotal(data.total || 0);
    } catch (error) {
      console.error('加载Case列表失败:', error);
    } finally {
      setLoading(false);
    }
  }, [activeTab, page, pageSize]);

  useEffect(() => {
    loadCases();
  }, [loadCases]);

  const handleCaseClick = async (caseItem) => {
    try {
      const detail = await getCaseDetail(caseItem.id);
      setSelectedCase(detail);
      setExpandedSections({});
    } catch (error) {
      console.error('获取Case详情失败:', error);
    }
  };

  const handleDownloadCases = async () => {
    try {
      setDownloading(true);
      const status = activeTab === 'good' ? 1 : 2;
      await downloadCases(status);
    } catch (error) {
      console.error('下载Case数据失败:', error);
    } finally {
      setDownloading(false);
    }
  };

  const toggleSection = (sectionName) => {
    setExpandedSections(prev => ({
      ...prev,
      [sectionName]: !prev[sectionName]
    }));
  };

  const parseTraceData = (traceDataStr) => {
    if (!traceDataStr) return null;
    try {
      return JSON.parse(traceDataStr);
    } catch {
      return null;
    }
  };

  const renderTraceSection = (name, data, icon) => {
    if (!data || !data.executed) return null;
    
    const isExpanded = expandedSections[name];
    
    return (
      <div className="trace-section" key={name}>
        <div 
          className={`trace-section-header ${isExpanded ? 'expanded' : ''}`}
          onClick={() => toggleSection(name)}
        >
          <span className="trace-section-icon">{icon}</span>
          <span className="trace-section-name">{getSectionLabel(name)}</span>
          <span className="trace-section-status">
            {data.status === 'success' ? (
              <span className="status-success">✓ 成功</span>
            ) : data.status === 'failed' ? (
              <span className="status-failed">✗ 失败</span>
            ) : (
              <span className="status-other">{data.status}</span>
            )}
          </span>
          <span className="trace-section-duration">{data.duration_ms?.toFixed(2) || 0}ms</span>
          <span className="trace-section-toggle">{isExpanded ? '▼' : '▶'}</span>
        </div>
        {isExpanded && (
          <div className="trace-section-content">
            {renderTraceDetails(data)}
          </div>
        )}
      </div>
    );
  };

  const getSectionLabel = (name) => {
    const labels = {
      'fqa': 'FQA搜索',
      'query_classify': '查询分类',
      'strategy_select': '策略选择',
      'vector_retrieval': '向量检索',
      'llm': 'LLM生成'
    };
    return labels[name] || name;
  };

  const handleResultExpand = async (result, index) => {
    const resultKey = `trace-result-${index}`;
    
    if (expandedResult === resultKey) {
      setExpandedResult(null);
      return;
    }
    
    setExpandedResult(resultKey);
    
    if (result.id && !vectorDetails[result.id]) {
      try {
        const response = await getVectorDetail(result.id);
        if (response.success && response.data) {
          setVectorDetails(prev => ({
            ...prev,
            [result.id]: response.data
          }));
        }
      } catch (error) {
        console.error('获取向量详情失败:', error);
      }
    }
  };

  const renderRetrievalResults = (results) => {
    if (!results || !Array.isArray(results) || results.length === 0) {
      return null;
    }
    
    return (
      <div className="retrieval-results-container">
        <div className="retrieval-results-header">
          <span className="retrieval-results-count">{results.length} 条检索结果</span>
        </div>
        <div className="retrieval-results-list">
          {results.map((result, index) => {
            const vectorDetail = result.id ? vectorDetails[result.id] : null;
            const parentContent = vectorDetail?.parent_content || result.parent_content;
            const fullContent = vectorDetail?.text || result.full_content || result.content;
            
            return (
              <div 
                key={index} 
                className={`retrieval-result-item ${expandedResult === `trace-result-${index}` ? 'expanded' : ''}`}
                onClick={() => handleResultExpand(result, index)}
              >
                <div className="retrieval-result-header">
                  <span className="retrieval-result-index">#{index + 1}</span>
                  <span className="retrieval-result-source">{result.source || '未知来源'}</span>
                  {result.score !== null && result.score !== undefined && (
                    <span className="retrieval-result-score">置信度: {typeof result.score === 'number' ? result.score.toFixed(4) : result.score}</span>
                  )}
                  <span className="retrieval-expand-hint">{expandedResult === `trace-result-${index}` ? '▼ 收起' : '▶ 展开'}</span>
                </div>
                <div className="retrieval-result-content">
                  {expandedResult === `trace-result-${index}` 
                    ? fullContent
                    : result.content && result.content.length > 100 
                      ? result.content.substring(0, 100) + '...' 
                      : result.content || ''
                  }
                </div>
                {expandedResult === `trace-result-${index}` && (
                  <>
                    {parentContent && (
                      <div className="retrieval-result-parent">
                        <div className="parent-label">父文档：</div>
                        <div className="parent-content">{parentContent}</div>
                      </div>
                    )}
                    {(vectorDetail?.file_path || result.file_path) && (
                      <div className="retrieval-result-trace">
                        <span className="retrieval-file-path" title={vectorDetail?.file_path || result.file_path}>
                          📂 {(vectorDetail?.file_path || result.file_path).split('/').pop().split('\\').pop()}
                        </span>
                      </div>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderTraceDetails = (data) => {
    const fields = [
      { key: 'input', label: '输入' },
      { key: 'output', label: '输出' },
      { key: 'error', label: '错误信息' },
      { key: 'category', label: '分类' },
      { key: 'confidence', label: '置信度' },
      { key: 'strategy', label: '策略' },
      { key: 'score', label: '分数' },
      { key: 'matched', label: '是否匹配' },
      { key: 'model', label: '模型' },
      { key: 'total_results', label: '结果数量' }
    ];

    return (
      <div className="trace-details">
        {fields.map(({ key, label }) => {
          const value = data[key];
          if (value === undefined || value === null) return null;
          
          return (
            <div className="trace-detail-item" key={key}>
              <span className="trace-detail-label">{label}:</span>
              <span className="trace-detail-value">
                {typeof value === 'object' ? (
                  <pre>{JSON.stringify(value, null, 2)}</pre>
                ) : (
                  String(value)
                )}
              </span>
            </div>
          );
        })}
        {data.results && Array.isArray(data.results) && data.results.length > 0 && (
          <div className="trace-detail-item">
            <span className="trace-detail-label">检索结果:</span>
            {renderRetrievalResults(data.results)}
          </div>
        )}
      </div>
    );
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="case-page">
      <div className="case-header">
        <h2>Case分析</h2>
        <div className="case-tabs">
          <button
            className={`case-tab ${activeTab === 'good' ? 'active' : ''}`}
            onClick={() => { setActiveTab('good'); setPage(1); }}
          >
            <span className="tab-icon">👍</span>
            GoodCase
            <span className="tab-count">{activeTab === 'good' ? total : ''}</span>
          </button>
          <button
            className={`case-tab ${activeTab === 'bad' ? 'active' : ''}`}
            onClick={() => { setActiveTab('bad'); setPage(1); }}
          >
            <span className="tab-icon">👎</span>
            BadCase
            <span className="tab-count">{activeTab === 'bad' ? total : ''}</span>
          </button>
          <button
            className="pagination-btn"
            onClick={handleDownloadCases}
            disabled={downloading}
          >
            {downloading ? '下载中...' : '下载 JSON'}
          </button>
        </div>
      </div>

      <div className="case-content">
        <div className="case-list">
          {loading ? (
            <div className="case-loading">加载中...</div>
          ) : cases.length === 0 ? (
            <div className="case-empty">暂无{activeTab === 'good' ? 'GoodCase' : 'BadCase'}数据</div>
          ) : (
            <>
              {cases.map((caseItem) => (
                <div 
                  key={caseItem.id} 
                  className={`case-item ${selectedCase?.id === caseItem.id ? 'selected' : ''}`}
                  onClick={() => handleCaseClick(caseItem)}
                >
                  <div className="case-item-header">
                    <span className="case-item-id">#{caseItem.id}</span>
                    <span className="case-item-time">{caseItem.created_at}</span>
                  </div>
                  <div className="case-item-query">{caseItem.query}</div>
                  <div className="case-item-answer">{caseItem.answer?.substring(0, 100)}...</div>
                </div>
              ))}
              
              {totalPages > 1 && (
                <div className="case-pagination">
                  <button 
                    className="pagination-btn"
                    disabled={page <= 1}
                    onClick={() => setPage(p => p - 1)}
                  >
                    上一页
                  </button>
                  <span className="pagination-info">{page} / {totalPages}</span>
                  <button 
                    className="pagination-btn"
                    disabled={page >= totalPages}
                    onClick={() => setPage(p => p + 1)}
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {selectedCase && (
          <div className="case-detail">
            <div className="case-detail-header">
              <h3>Case详情</h3>
              <button className="close-btn" onClick={() => setSelectedCase(null)}>✕</button>
            </div>
            
            <div className="case-detail-section">
              <h4>问题</h4>
              <p>{selectedCase.query}</p>
            </div>
            
            <div className="case-detail-section">
              <h4>回答</h4>
              <p>{selectedCase.answer}</p>
            </div>
            
            <div className="case-detail-section">
              <h4>执行链路</h4>
              {(() => {
                const traceData = parseTraceData(selectedCase.trace_data);
                if (!traceData) {
                  return <p className="no-trace">无执行链路数据</p>;
                }
                
                return (
                  <div className="trace-container">
                    <div className="trace-overview">
                      <span>总耗时: {traceData.total_duration_ms?.toFixed(2) || 0}ms</span>
                    </div>
                    
                    {renderTraceSection('fqa', traceData.fqa, '🔍')}
                    {renderTraceSection('query_classify', traceData.query_classify, '📊')}
                    {renderTraceSection('strategy_select', traceData.strategy_select, '⚙️')}
                    {renderTraceSection('vector_retrieval', traceData.vector_retrieval, '📚')}
                    {renderTraceSection('llm', traceData.llm, '🤖')}
                  </div>
                );
              })()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CasePage;
