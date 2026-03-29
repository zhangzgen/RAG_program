import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  getAssessmentFileDetail,
  getAssessmentFiles,
  getAssessmentResultDetail,
  getAssessmentResults,
  runAssessment,
  uploadAssessmentFile,
} from '../api';
import './AssessmentPage.css';

const METRIC_LABELS = {
  faithfulness: '忠实度',
  answer_relevancy: '答案相关性',
  context_precision: '上下文精确率',
  context_recall: '上下文召回率',
};

const formatMetric = (value) => (typeof value === 'number' ? value.toFixed(4) : '--');

const AssessmentPage = () => {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [assessmentResults, setAssessmentResults] = useState([]);
  const [selectedFileId, setSelectedFileId] = useState('');
  const [selectedResultId, setSelectedResultId] = useState('');
  const [selectedFileDetail, setSelectedFileDetail] = useState(null);
  const [selectedResultDetail, setSelectedResultDetail] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [loadingResults, setLoadingResults] = useState(false);
  const [running, setRunning] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const [elapsed, setElapsed] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [completedQuestions, setCompletedQuestions] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [latestItemResult, setLatestItemResult] = useState(null);
  const fileInputRef = useRef(null);
  const runControllerRef = useRef(null);

  useEffect(() => {
    loadFiles();
    loadResults();
  }, []);

  useEffect(() => {
    if (!running || !startTime) return undefined;
    const timer = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);
    return () => clearInterval(timer);
  }, [running, startTime]);

  useEffect(() => () => {
    if (runControllerRef.current?.cancel) {
      runControllerRef.current.cancel();
    }
  }, []);

  const loadFiles = async () => {
    try {
      setLoadingFiles(true);
      const data = await getAssessmentFiles();
      setUploadedFiles(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('加载评估文件失败:', err);
      setError(err.message || '加载评估文件失败');
    } finally {
      setLoadingFiles(false);
    }
  };

  const loadResults = async () => {
    try {
      setLoadingResults(true);
      const data = await getAssessmentResults();
      setAssessmentResults(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('加载评估结果失败:', err);
    } finally {
      setLoadingResults(false);
    }
  };

  const selectedFile = useMemo(
    () => uploadedFiles.find((item) => item.file_id === selectedFileId) || null,
    [uploadedFiles, selectedFileId]
  );

  const progressPercent = totalQuestions > 0 ? Math.min((completedQuestions / totalQuestions) * 100, 100) : 0;

  const handleChooseFile = () => {
    if (!running) fileInputRef.current?.click();
  };

  const handleUploadFile = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';

    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.json')) {
      alert('仅支持上传 .json 文件');
      return;
    }

    try {
      setUploading(true);
      setError('');
      const data = await uploadAssessmentFile(file);
      await loadFiles();
      if (data?.file_id) {
        setSelectedFileId(data.file_id);
        await handleViewFile(data.file_id);
      }
    } catch (err) {
      console.error('上传评估文件失败:', err);
      alert(err.message || '上传评估文件失败');
    } finally {
      setUploading(false);
    }
  };

  const handleViewFile = async (fileId) => {
    try {
      setSelectedFileId(fileId);
      const data = await getAssessmentFileDetail(fileId);
      setSelectedFileDetail(data);
    } catch (err) {
      console.error('查看评估文件失败:', err);
      alert(err.message || '查看评估文件失败');
    }
  };

  const handleViewResult = async (resultId) => {
    try {
      setSelectedResultId(resultId);
      const data = await getAssessmentResultDetail(resultId);
      setSelectedResultDetail(data);
      setResult({
        faithfulness: data.faithfulness,
        answer_relevancy: data.answer_relevancy,
        context_precision: data.context_precision,
        context_recall: data.context_recall,
      });
    } catch (err) {
      console.error('查看评估结果失败:', err);
      alert(err.message || '查看评估结果失败');
    }
  };

  const handleRunAssessment = async () => {
    if (!selectedFileId || running) return;

    try {
      setError('');
      setResult(null);
      setSelectedResultId('');
      setSelectedResultDetail(null);
      setLatestItemResult(null);
      setTotalQuestions(0);
      setCompletedQuestions(0);
      setElapsed(0);
      setStartTime(Date.now());
      setRunning(true);

      const controller = await runAssessment(selectedFileId, async (data) => {
        if (data.type === 'start') {
          setTotalQuestions(data.total_questions || 0);
          setCompletedQuestions(data.completed_questions || 0);
          if (data.result_id) {
            setSelectedResultId(data.result_id);
          }
        } else if (data.type === 'progress') {
          setTotalQuestions(data.total_questions || 0);
          setCompletedQuestions(data.completed_questions || 0);
          setLatestItemResult(data.latest_result || null);
        } else if (data.type === 'complete') {
          setResult(data.results || null);
          setCompletedQuestions(data.completed_questions || data.total_questions || 0);
          setRunning(false);
          await loadResults();
          if (data.result_id) {
            await handleViewResult(data.result_id);
          }
        } else if (data.type === 'error') {
          setError(data.message || '评估失败');
          setRunning(false);
          await loadResults();
        }
      });

      runControllerRef.current = controller;
      await controller.promise;
    } catch (err) {
      console.error('执行评估失败:', err);
      setError(err.message || '执行评估失败');
      setRunning(false);
    }
  };

  return (
    <div className="assessment-page">
      <div className="assessment-page-header">
        <h2 className="assessment-page-title">系统评估</h2>
      </div>

      <div className="assessment-layout">
        <div className="assessment-main-column">
          <div className="assessment-card">
            <div className="assessment-section-header">
              <h3>评估文件</h3>
              <button
                className="assessment-action-btn primary"
                onClick={handleChooseFile}
                disabled={uploading || running}
              >
                {uploading ? '上传中...' : '上传评估文件'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,application/json"
                className="hidden-file-input"
                onChange={handleUploadFile}
              />
            </div>

            <div className="assessment-upload-hint">
              支持上传 JSON 格式评估数据，字段需与 rag_evaluate_data.json 一致，可重复查看和重复评估。
            </div>

            <div className="assessment-file-list">
              {loadingFiles ? (
                <div className="assessment-empty-state">加载中...</div>
              ) : uploadedFiles.length === 0 ? (
                <div className="assessment-empty-state">暂无评估文件，请先上传</div>
              ) : (
                uploadedFiles.map((file) => (
                  <div key={file.file_id} className={`assessment-file-item ${selectedFileId === file.file_id ? 'selected' : ''}`}>
                    <button
                      className="assessment-file-select"
                      onClick={() => handleViewFile(file.file_id)}
                      disabled={running}
                    >
                      <div className="assessment-file-main">
                        <span className="assessment-file-radio">{selectedFileId === file.file_id ? '●' : '○'}</span>
                        <span className="assessment-file-name">{file.file_name}</span>
                      </div>
                      <span className="assessment-file-time">{file.uploaded_at}</span>
                    </button>
                    <button
                      className="assessment-inline-btn"
                      onClick={() => handleViewFile(file.file_id)}
                      disabled={running}
                    >
                      查看
                    </button>
                  </div>
                ))
              )}
            </div>

            <div className="assessment-actions">
              <button
                className="assessment-action-btn primary"
                onClick={handleRunAssessment}
                disabled={!selectedFileId || running || uploading}
              >
                {running ? '评估中...' : '开始评估'}
              </button>
              {selectedFile && (
                <span className="assessment-selected-file">当前文件：{selectedFile.file_name}</span>
              )}
            </div>
          </div>

          {(running || result || error) && (
            <div className="assessment-card">
              <div className="assessment-section-header">
                <h3>评估进度</h3>
              </div>

              {running && (
                <div className="assessment-running-panel">
                  <div className="assessment-running-row">
                    <div className="assessment-searching-spinner"></div>
                    <span>评估中...</span>
                  </div>
                  <div className="assessment-progress-meta">
                    <span>总条数：{totalQuestions || '--'}</span>
                    <span>已评估：{completedQuestions}</span>
                    <span>已耗时：{elapsed} 秒</span>
                  </div>
                  <div className="assessment-progress-bar">
                    <div className="assessment-progress-fill" style={{ width: `${progressPercent}%` }}></div>
                  </div>
                  <div className="assessment-progress-text">{completedQuestions} / {totalQuestions || '--'}</div>
                  {latestItemResult && (
                    <div className="assessment-latest-item">
                      <div className="assessment-latest-title">当前累计结果</div>
                      <div className="assessment-mini-grid">
                        {Object.entries(METRIC_LABELS).map(([key, label]) => (
                          <div key={key} className="assessment-mini-item">
                            <span>{label}</span>
                            <strong>{formatMetric(latestItemResult[key])}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {error && <div className="assessment-error">{error}</div>}

              {result && (
                <div className="assessment-result-section">
                  <div className="assessment-result-header">评估结果</div>
                  <div className="assessment-result-table">
                    {Object.entries(METRIC_LABELS).map(([key, label]) => (
                      <div className="assessment-result-row" key={key}>
                        <span className="assessment-metric-label">{label}</span>
                        <span className="assessment-metric-value">{formatMetric(result[key])}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {selectedFileDetail && (
            <div className="assessment-card">
              <div className="assessment-section-header">
                <h3>文件详情</h3>
              </div>
              <div className="assessment-detail-meta">
                <span>文件名：{selectedFileDetail.file_name}</span>
                <span>上传时间：{selectedFileDetail.uploaded_at}</span>
              </div>
              <pre className="assessment-json-preview">{selectedFileDetail.raw_content || JSON.stringify(selectedFileDetail.content || [], null, 2)}</pre>
            </div>
          )}
        </div>

        <div className="assessment-side-column">
          <div className="assessment-card sticky-card">
            <div className="assessment-section-header">
              <h3>评估历史</h3>
            </div>
            <div className="assessment-history-list">
              {loadingResults ? (
                <div className="assessment-empty-state">加载中...</div>
              ) : assessmentResults.length === 0 ? (
                <div className="assessment-empty-state">暂无评估记录</div>
              ) : (
                assessmentResults.map((item) => (
                  <button
                    key={item.result_id}
                    className={`assessment-history-item ${selectedResultId === item.result_id ? 'selected' : ''}`}
                    onClick={() => handleViewResult(item.result_id)}
                  >
                    <div className="assessment-history-title">{item.file_name}</div>
                    <div className="assessment-history-meta">
                      <span>{item.status}</span>
                      <span>{item.completed_questions}/{item.total_questions}</span>
                    </div>
                    <div className="assessment-history-time">{item.created_at}</div>
                  </button>
                ))
              )}
            </div>
          </div>

          {selectedResultDetail && (
            <div className="assessment-card sticky-card-secondary">
              <div className="assessment-section-header">
                <h3>历史结果详情</h3>
              </div>
              <div className="assessment-detail-meta column">
                <span>文件：{selectedResultDetail.file_name}</span>
                <span>状态：{selectedResultDetail.status}</span>
                <span>时间：{selectedResultDetail.created_at}</span>
              </div>
              <div className="assessment-result-table compact">
                {Object.entries(METRIC_LABELS).map(([key, label]) => (
                  <div className="assessment-result-row" key={key}>
                    <span className="assessment-metric-label">{label}</span>
                    <span className="assessment-metric-value">{formatMetric(selectedResultDetail[key])}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AssessmentPage;
