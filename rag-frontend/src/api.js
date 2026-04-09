import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

const ADMIN_API_PATTERNS = [
  /^\/knowledge(?:\/|$)/,
  /^\/config(?:\/|$)/,
  /^\/faq(?:\/|$)/,
  /^\/cases(?:\/|$)/,
  /^\/assessment(?:\/|$)/,
  /^\/conversations\/\d+\/status$/,
];

const getStoredUser = () => {
  try {
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    if (!user || typeof user !== 'object') {
      return null;
    }
    return user;
  } catch (error) {
    return null;
  }
};

const hasAdminAccess = () => Number(getStoredUser()?.is_admin || 0) === 1;

const ensureAdminAccess = () => {
  if (!hasAdminAccess()) {
    throw new Error('仅管理员可访问专业模式相关功能');
  }
};

const isAdminApiRequest = (url = '') => {
  return ADMIN_API_PATTERNS.some((pattern) => pattern.test(url));
};

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (isAdminApiRequest(config.url || '')) {
      ensureAdminAccess();
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  response => response,
  error => {
    if (error.code === 'ECONNABORTED') {
      error.message = '请求超时，请检查网络连接';
    } else if (error.response) {
      switch (error.response.status) {
        case 400:
          error.message = error.response.data.detail || '请求参数错误';
          break;
        case 401:
          error.message = '未授权，请重新登录';
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          window.location.href = '/';
          break;
        case 403:
          error.message = '无权访问此资源';
          break;
        case 404:
          error.message = '请求的资源不存在';
          break;
        case 500:
          error.message = '服务器内部错误';
          break;
        default:
          error.message = `请求失败: ${error.response.status}`;
      }
    } else if (error.request) {
      error.message = '网络连接失败，请检查网络设置';
    }
    return Promise.reject(error);
  }
);

export const sendVerificationCode = async (email) => {
  const response = await api.post('/send-verification-code', { email });
  return response.data;
};

export const login = async (email, verificationCode) => {
  const response = await api.post('/login', {
    email,
    verification_code: verificationCode,
  });
  return response.data;
};

export const verifyToken = async () => {
  const response = await api.get('/verify-token');
  return response.data;
};

export const createSession = async () => {
  const response = await api.post('/sessions/create');
  return response.data;
};

export const queryAPI = async (query, sourceFilter = null, sessionId = null) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  try {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        query,
        source_filter: sourceFilter,
        session_id: sessionId,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/';
        throw new Error('未授权，请重新登录');
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.body;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new Error('请求超时，请稍后重试');
    }
    throw error;
  }
};

export const getSessions = async (limit = 20) => {
  const response = await api.get('/sessions', { params: { limit } });
  return response.data;
};

export const getSessionConversations = async (sessionId, limit = 10) => {
  const response = await api.get(`/sessions/${sessionId}`, { params: { limit } });
  return response.data;
};

export const deleteSession = async (sessionId) => {
  const response = await api.delete(`/sessions/${sessionId}`);
  return response.data;
};

export const getCategories = async () => {
  const response = await api.get('/knowledge/categories');
  return response.data;
};

export const createCategory = async (categoryName) => {
  const response = await api.post('/knowledge/categories', { category_name: categoryName });
  return response.data;
};

export const deleteCategory = async (categoryId) => {
  const response = await api.delete(`/knowledge/categories/${categoryId}`);
  return response.data;
};

export const getCategoryFiles = async (categoryId) => {
  const response = await api.get(`/knowledge/categories/${categoryId}/files`);
  return response.data;
};

export const getFileInfo = async (fileId) => {
  const response = await api.get(`/knowledge/files/${fileId}`);
  return response.data;
};

export const previewFile = async (fileId) => {
  const response = await api.get(`/knowledge/files/${fileId}/preview`);
  return response.data;
};

export const uploadFile = async (categoryId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post(`/knowledge/categories/${categoryId}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const deleteFile = async (fileId) => {
  const response = await api.delete(`/knowledge/files/${fileId}`);
  return response.data;
};

export const getKnowledgeFiles = async (categoryId = null) => {
  const params = categoryId ? { category_id: categoryId } : {};
  const response = await api.get('/knowledge/files', { params });
  return response.data;
};

export const previewFileByPath = async (path) => {
  const response = await api.get('/knowledge/preview', { params: { path } });
  return response.data;
};

export const uploadFileToCategory = async (categoryId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post(`/knowledge/categories/${categoryId}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const vectorSearch = async (query, sourceFilter = null, topK = 5) => {
  const response = await api.post('/knowledge/search', {
    query,
    source_filter: sourceFilter,
    top_k: topK,
  });
  return response.data;
};

export const getVectorDetail = async (vectorId) => {
  const response = await api.post('/knowledge/vector/detail', {
    vector_id: vectorId,
  });
  return response.data;
};

export const getKnowledgeSources = async () => {
  const response = await api.get('/knowledge/sources');
  return response.data;
};

export const chunkFiles = async (fileIds = [], categoryId = null, onProgress, onComplete, onError) => {
  ensureAdminAccess();
  const token = localStorage.getItem('token');
  
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource(
      `${API_BASE_URL}/knowledge/chunk/stream?file_ids=${fileIds.join(',')}&category_id=${categoryId || ''}&token=${token}`,
      { withCredentials: true }
    );
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'progress' && onProgress) {
          onProgress(data);
        } else if (data.type === 'result' && onProgress) {
          onProgress(data);
        } else if (data.type === 'complete') {
          eventSource.close();
          if (onComplete) onComplete(data);
          resolve(data);
        }
      } catch (e) {
        console.error('解析SSE数据失败:', e);
      }
    };
    
    eventSource.onerror = (error) => {
      eventSource.close();
      if (onError) onError(error);
      reject(error);
    };
  });
};

export const chunkFilesPost = async (fileIds = [], categoryId = null, onMessage) => {
  ensureAdminAccess();
  const token = localStorage.getItem('token');
  
  const response = await fetch(`${API_BASE_URL}/knowledge/chunk`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      file_ids: fileIds,
      category_id: categoryId,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let result;
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          if (onMessage) onMessage(data);
          result = data;
        } catch (e) {
          console.error('解析SSE数据失败:', e);
        }
      }
    }
  }
  
  return result;
};

export const getUnchunkedFiles = async (categoryId = null) => {
  const params = categoryId ? { category_id: categoryId } : {};
  const response = await api.get('/knowledge/files/unchunked', { params });
  return response.data;
};

export const getSupportedFileTypes = async () => {
  const response = await api.get('/knowledge/supported-types');
  return response.data;
};

export const getFileChunks = async (fileId) => {
  const response = await api.get(`/knowledge/files/${fileId}/chunks`);
  return response.data;
};

export const getConfig = async () => {
  const response = await api.get('/config');
  return response.data;
};

export const getRawConfig = async () => {
  const response = await api.get('/config/raw');
  return response.data;
};

export const updateConfig = async (data) => {
  const response = await api.post('/config', data);
  return response.data;
};

export const getConfigVersions = async (limit = 20) => {
  const response = await api.get('/config/versions', { params: { limit } });
  return response.data;
};

export const getConfigVersionDetail = async (versionId) => {
  const response = await api.get(`/config/versions/${versionId}`);
  return response.data;
};

export const rollbackConfig = async (versionId) => {
  const response = await api.post(`/config/rollback/${versionId}`);
  return response.data;
};

export const getFaqs = async (search = null) => {
  const params = search ? { search } : {};
  const response = await api.get('/faq', { params });
  return response.data;
};

export const getFaq = async (faqId) => {
  const response = await api.get(`/faq/${faqId}`);
  return response.data;
};

export const createFaq = async (data) => {
  const response = await api.post('/faq', data);
  return response.data;
};

export const updateFaq = async (faqId, data) => {
  const response = await api.put(`/faq/${faqId}`, data);
  return response.data;
};

export const deleteFaq = async (faqId) => {
  const response = await api.delete(`/faq/${faqId}`);
  return response.data;
};

export const updateConversationStatus = async (conversationId, status) => {
  const response = await api.patch(`/conversations/${conversationId}/status`, { status });
  return response.data;
};

export const overwriteRegeneratedConversation = async (conversationId, answer, traceData = null) => {
  const response = await api.patch(`/conversations/${conversationId}/regenerate`, {
    answer,
    trace_data: traceData,
  });
  return response.data;
};

export const getCases = async (status, page = 1, pageSize = 20) => {
  const response = await api.get('/cases', { params: { status, page, page_size: pageSize } });
  return response.data;
};

export const getCaseDetail = async (conversationId) => {
  const response = await api.get(`/cases/${conversationId}`);
  return response.data;
};

export const downloadCases = async (status) => {
  const response = await api.get('/cases/download', {
    params: { status },
    responseType: 'blob',
  });

  const blob = new Blob([response.data], { type: 'application/json' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = status === 1 ? 'good_cases.json' : 'bad_cases.json';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);

  return true;
};

export const uploadAssessmentFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/assessment/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getAssessmentFiles = async () => {
  const response = await api.get('/assessment/files');
  return response.data;
};

export const getAssessmentFileDetail = async (fileId) => {
  const response = await api.get(`/assessment/files/${fileId}`);
  return response.data;
};

export const getAssessmentResults = async (limit = 50) => {
  const response = await api.get('/assessment/results', { params: { limit } });
  return response.data;
};

export const getAssessmentResultDetail = async (resultId) => {
  const response = await api.get(`/assessment/results/${resultId}`);
  return response.data;
};

export const runAssessment = async (fileId, onEvent) => {
  ensureAdminAccess();
  const token = localStorage.getItem('token');
  const controller = new AbortController();

  const response = await fetch(`${API_BASE_URL}/assessment/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ file_id: fileId }),
    signal: controller.signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  const pump = async () => {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const messages = buffer.split('\n\n');
      buffer = messages.pop() || '';

      for (const message of messages) {
        const lines = message.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (onEvent) onEvent(data);
            } catch (e) {
              console.error('解析评估SSE数据失败:', e);
            }
          }
        }
      }
    }
  };

  const promise = pump();

  return {
    promise,
    cancel: () => controller.abort(),
  };
};
