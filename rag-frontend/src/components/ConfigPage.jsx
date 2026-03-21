import React, { useState, useEffect } from 'react';
import { 
  getConfig, 
  getRawConfig, 
  updateConfig, 
  getConfigVersions, 
  getConfigVersionDetail, 
  rollbackConfig 
} from '../api';
import './ConfigPage.css';

const ConfigPage = () => {
  const [config, setConfig] = useState(null);
  const [rawContent, setRawContent] = useState('');
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('view');
  const [formData, setFormData] = useState({});
  const [changeDescription, setChangeDescription] = useState('');
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [showVersionModal, setShowVersionModal] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  useEffect(() => {
    loadConfig();
    loadVersions();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await getConfig();
      setConfig(data.config);
      
      const rawData = await getRawConfig();
      setRawContent(rawData.content);
      setFormData(parseIniToForm(rawData.content));
    } catch (error) {
      showMessage('error', '加载配置失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadVersions = async () => {
    try {
      const data = await getConfigVersions();
      setVersions(data.versions || []);
    } catch (error) {
      console.error('加载版本列表失败:', error);
    }
  };

  const parseIniToForm = (content) => {
    const result = {};
    let currentSection = '';
    
    content.split('\n').forEach(line => {
      line = line.trim();
      if (!line || line.startsWith('#')) return;
      
      const sectionMatch = line.match(/^\[(\w+)\]$/);
      if (sectionMatch) {
        currentSection = sectionMatch[1];
        result[currentSection] = {};
        return;
      }
      
      const keyValueMatch = line.match(/^(.+?)\s*=\s*(.*)$/);
      if (keyValueMatch && currentSection) {
        const key = keyValueMatch[1].trim();
        let value = keyValueMatch[2].trim();
        result[currentSection][key] = value;
      }
    });
    
    return result;
  };

  const formToIni = (data) => {
    let content = '';
    
    Object.entries(data).forEach(([section, values]) => {
      content += `# ${getSectionComment(section)}\n`;
      content += `[${section}]\n`;
      
      Object.entries(values).forEach(([key, value]) => {
        content += `${key} = ${value}\n`;
      });
      
      content += '\n';
    });
    
    return content.trim();
  };

  const getSectionComment = (section) => {
    const comments = {
      mysql: 'MySQL 配置',
      redis: 'Redis 配置',
      milvus: 'Milvus 配置',
      llm: 'LLM 配置',
      retrieval: '检索参数配置',
      logger: '日志配置',
      app: '应用配置',
      email: '邮箱配置',
      jwt: 'JWT 配置'
    };
    return comments[section] || section;
  };

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleFieldChange = (section, key, value) => {
    setFormData(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value
      }
    }));
  };

  const handleSaveConfig = async () => {
    if (!changeDescription.trim()) {
      showMessage('error', '请填写变更描述');
      return;
    }
    
    try {
      setLoading(true);
      const newContent = formToIni(formData);
      
      await updateConfig({
        config_content: newContent,
        change_description: changeDescription,
        changed_by: 'admin'
      });
      showMessage('success', '配置保存成功');
      setChangeDescription('');
      loadVersions();
      loadConfig();
    } catch (error) {
      showMessage('error', '保存配置失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewVersion = async (versionId) => {
    try {
      const data = await getConfigVersionDetail(versionId);
      setSelectedVersion(data.version);
      setShowVersionModal(true);
    } catch (error) {
      showMessage('error', '获取版本详情失败: ' + error.message);
    }
  };

  const handleRollback = async (versionId) => {
    if (!window.confirm('确定要回退到此版本吗？')) {
      return;
    }
    
    try {
      setLoading(true);
      await rollbackConfig(versionId);
      showMessage('success', '配置回退成功');
      loadConfig();
      loadVersions();
      setShowVersionModal(false);
    } catch (error) {
      showMessage('error', '配置回退失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const renderConfigSection = (title, data, icon) => (
    <div className="config-section">
      <div className="section-title">
        <span className="section-icon">{icon}</span>
        {title}
      </div>
      <div className="section-content">
        {Object.entries(data).map(([key, value]) => (
          <div key={key} className="config-item">
            <span className="config-key">{key}</span>
            <span className={`config-value ${value === '******' ? 'masked' : ''}`}>
              {Array.isArray(value) ? JSON.stringify(value) : String(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );

  const renderFormSection = (section, title, icon, fields) => {
    if (!formData[section]) return null;
    
    return (
      <div className="form-section">
        <div className="section-title">
          <span className="section-icon">{icon}</span>
          {title}
        </div>
        <div className="form-fields">
          {fields.map(field => (
            <div key={field.key} className="form-field">
              <label className="field-label">
                {field.label}
                {field.required && <span className="required">*</span>}
              </label>
              {field.type === 'number' ? (
                <input
                  type="number"
                  className="field-input"
                  value={formData[section][field.key] || ''}
                  onChange={(e) => handleFieldChange(section, field.key, e.target.value)}
                  placeholder={field.placeholder}
                />
              ) : field.type === 'select' ? (
                <select
                  className="field-select"
                  value={formData[section][field.key] || ''}
                  onChange={(e) => handleFieldChange(section, field.key, e.target.value)}
                >
                  {field.options.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  className="field-textarea"
                  value={formData[section][field.key] || ''}
                  onChange={(e) => handleFieldChange(section, field.key, e.target.value)}
                  placeholder={field.placeholder}
                  rows={3}
                />
              ) : (
                <input
                  type={field.type === 'password' ? 'password' : 'text'}
                  className="field-input"
                  value={formData[section][field.key] || ''}
                  onChange={(e) => handleFieldChange(section, field.key, e.target.value)}
                  placeholder={field.placeholder}
                />
              )}
              {field.hint && <span className="field-hint">{field.hint}</span>}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const formSections = [
    {
      section: 'mysql',
      title: 'MySQL 配置',
      icon: '🗄️',
      fields: [
        { key: 'host', label: '主机地址', type: 'text', required: true, placeholder: 'localhost' },
        { key: 'user', label: '用户名', type: 'text', required: true, placeholder: 'root' },
        { key: 'password', label: '密码', type: 'password', required: true },
        { key: 'database', label: '数据库名', type: 'text', required: true, placeholder: 'subjects_kg' }
      ]
    },
    {
      section: 'redis',
      title: 'Redis 配置',
      icon: '⚡',
      fields: [
        { key: 'host', label: '主机地址', type: 'text', required: true, placeholder: 'localhost' },
        { key: 'port', label: '端口', type: 'number', required: true, placeholder: '6379' },
        { key: 'password', label: '密码', type: 'password', required: true },
        { key: 'db', label: '数据库编号', type: 'number', required: true, placeholder: '0' }
      ]
    },
    {
      section: 'milvus',
      title: 'Milvus 配置',
      icon: '🔍',
      fields: [
        { key: 'host', label: '主机地址', type: 'text', required: true, placeholder: 'localhost' },
        { key: 'port', label: '端口', type: 'text', required: true, placeholder: '19530' },
        { key: 'database_name', label: '数据库名', type: 'text', required: true, placeholder: 'itcast' },
        { key: 'collection_name', label: '集合名', type: 'text', required: true, placeholder: 'edurag_final' }
      ]
    },
    {
      section: 'llm',
      title: 'LLM 配置',
      icon: '🤖',
      fields: [
        { key: 'model', label: '模型名称', type: 'text', required: true, placeholder: 'qwen-plus' },
        { key: 'dashscope_api_key', label: 'API Key', type: 'password', required: true },
        { key: 'dashscope_base_url', label: 'API 地址', type: 'text', required: true, placeholder: 'https://dashscope.aliyuncs.com/compatible-mode/v1' }
      ]
    },
    {
      section: 'retrieval',
      title: '检索参数配置',
      icon: '📊',
      fields: [
        { key: 'parent_chunk_size', label: '父块大小', type: 'number', required: true, placeholder: '1200', hint: '父文档切片的字符数' },
        { key: 'child_chunk_size', label: '子块大小', type: 'number', required: true, placeholder: '300', hint: '子文档切片的字符数' },
        { key: 'chunk_overlap', label: '切片重叠', type: 'number', required: true, placeholder: '50', hint: '切片之间的重叠字符数' },
        { key: 'retrieval_k', label: '检索数量', type: 'number', required: true, placeholder: '5', hint: '检索返回的文档数量' },
        { key: 'candidate_m', label: '候选数量', type: 'number', required: true, placeholder: '2', hint: '最终返回的候选文档数量' }
      ]
    },
    {
      section: 'logger',
      title: '日志配置',
      icon: '📝',
      fields: [
        { key: 'log_file', label: '日志文件路径', type: 'text', required: true, placeholder: 'logs/app.log' }
      ]
    },
    {
      section: 'app',
      title: '应用配置',
      icon: '⚙️',
      fields: [
        { key: 'valid_sources', label: '有效来源列表', type: 'textarea', required: true, placeholder: '["ai", "java", "test", "ops", "bigdata"]', hint: 'JSON数组格式' },
        { key: 'customer_service_phone', label: '客服电话', type: 'text', required: false, placeholder: '12345678' }
      ]
    },
    {
      section: 'email',
      title: '邮箱配置',
      icon: '📧',
      fields: [
        { key: 'qq_email', label: 'QQ邮箱', type: 'text', required: true, placeholder: 'your_qq_email@qq.com' },
        { key: 'qq_auth_code', label: '授权码', type: 'password', required: true },
        { key: 'smtp_server', label: 'SMTP服务器', type: 'text', required: true, placeholder: 'smtp.qq.com' },
        { key: 'smtp_port', label: 'SMTP端口', type: 'number', required: true, placeholder: '465' }
      ]
    },
    {
      section: 'jwt',
      title: 'JWT 配置',
      icon: '🔐',
      fields: [
        { key: 'secret_key', label: '密钥', type: 'password', required: true, hint: '生产环境请使用强密钥' },
        { key: 'algorithm', label: '算法', type: 'text', required: true, placeholder: 'HS256' },
        { key: 'expire_days', label: '过期天数', type: 'number', required: true, placeholder: '30' }
      ]
    }
  ];

  return (
    <div className="config-page">
      <div className="config-header">
        <h2>系统配置管理</h2>
        <div className="config-tabs">
          <button 
            className={`tab-btn ${activeTab === 'view' ? 'active' : ''}`}
            onClick={() => setActiveTab('view')}
          >
            配置查看
          </button>
          <button 
            className={`tab-btn ${activeTab === 'edit' ? 'active' : ''}`}
            onClick={() => setActiveTab('edit')}
          >
            配置编辑
          </button>
          <button 
            className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            版本历史
          </button>
        </div>
      </div>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      {loading && !config ? (
        <div className="loading">加载中...</div>
      ) : (
        <>
          {activeTab === 'view' && config && (
            <div className="config-view">
              {renderConfigSection('MySQL 配置', config.mysql, '🗄️')}
              {renderConfigSection('Redis 配置', config.redis, '⚡')}
              {renderConfigSection('Milvus 配置', config.milvus, '🔍')}
              {renderConfigSection('LLM 配置', config.llm, '🤖')}
              {renderConfigSection('检索参数', config.retrieval, '📊')}
              {renderConfigSection('日志配置', config.logger, '📝')}
              {renderConfigSection('应用配置', config.app, '⚙️')}
              {renderConfigSection('邮箱配置', config.email, '📧')}
              {renderConfigSection('JWT 配置', config.jwt, '🔐')}
            </div>
          )}

          {activeTab === 'edit' && (
            <div className="config-edit">
              <div className="edit-header">
                <h3>编辑配置</h3>
                <span className="edit-hint">修改后请填写变更描述并保存</span>
              </div>
              
              <div className="form-container">
                {formSections.map(s => renderFormSection(s.section, s.title, s.icon, s.fields))}
              </div>
              
              <div className="edit-actions">
                <input
                  type="text"
                  className="change-description"
                  placeholder="请输入变更描述（必填）..."
                  value={changeDescription}
                  onChange={(e) => setChangeDescription(e.target.value)}
                />
                <button 
                  className="save-btn"
                  onClick={handleSaveConfig}
                  disabled={loading}
                >
                  {loading ? '保存中...' : '保存配置'}
                </button>
              </div>
            </div>
          )}

          {activeTab === 'history' && (
            <div className="config-history">
              <h3>版本历史</h3>
              {versions.length === 0 ? (
                <div className="no-versions">暂无历史版本</div>
              ) : (
                <div className="version-list">
                  {versions.map((version) => (
                    <div 
                      key={version.id} 
                      className={`version-item ${version.is_active ? 'active' : ''}`}
                    >
                      <div className="version-info">
                        <span className="version-number">v{version.version}</span>
                        <span className="version-time">{version.created_at}</span>
                        {version.is_active && <span className="active-badge">当前版本</span>}
                      </div>
                      <div className="version-desc">
                        {version.change_description || '无描述'}
                      </div>
                      <div className="version-actions">
                        <button 
                          className="view-btn"
                          onClick={() => handleViewVersion(version.id)}
                        >
                          查看
                        </button>
                        {!version.is_active && (
                          <button 
                            className="rollback-btn"
                            onClick={() => handleRollback(version.id)}
                          >
                            回退
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {showVersionModal && selectedVersion && (
        <div className="modal-overlay" onClick={() => setShowVersionModal(false)}>
          <div className="version-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4>版本详情 - v{selectedVersion.version}</h4>
              <button className="close-btn" onClick={() => setShowVersionModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="version-meta">
                <p><strong>变更描述:</strong> {selectedVersion.change_description || '无'}</p>
                <p><strong>变更人:</strong> {selectedVersion.changed_by}</p>
                <p><strong>创建时间:</strong> {selectedVersion.created_at}</p>
              </div>
              <div className="version-content">
                <h5>配置内容:</h5>
                <pre>{selectedVersion.config_content}</pre>
              </div>
            </div>
            <div className="modal-footer">
              {!selectedVersion.is_active && (
                <button 
                  className="rollback-btn"
                  onClick={() => handleRollback(selectedVersion.id)}
                >
                  回退到此版本
                </button>
              )}
              <button className="close-modal-btn" onClick={() => setShowVersionModal(false)}>
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfigPage;
