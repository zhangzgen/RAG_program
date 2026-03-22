import React, { useState, useEffect } from 'react';
import { getFaqs, createFaq, updateFaq, deleteFaq } from '../api';
import './FqaPage.css';

const FqaPage = () => {
  const [faqs, setFaqs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [selectedFqa, setSelectedFqa] = useState(null);
  const [editingFqa, setEditingFqa] = useState(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [formData, setFormData] = useState({
    subject_name: '',
    question: '',
    answer: ''
  });

  useEffect(() => {
    loadFaqs();
  }, []);

  const loadFaqs = async (search = null) => {
    try {
      setLoading(true);
      const data = await getFaqs(search);
      setFaqs(data.faqs || []);
    } catch (error) {
      console.error('加载FQA失败:', error);
      alert(error.message || '加载FQA失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadFaqs(searchKeyword.trim() || null);
  };

  const handleSearchKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleClearSearch = () => {
    setSearchKeyword('');
    loadFaqs(null);
  };

  const handleOpenModal = (faq = null, e) => {
    if (e) e.stopPropagation();
    if (faq) {
      setEditingFqa(faq);
      setFormData({
        subject_name: faq.subject_name || '',
        question: faq.question || '',
        answer: faq.answer || ''
      });
    } else {
      setEditingFqa(null);
      setFormData({
        subject_name: '',
        question: '',
        answer: ''
      });
    }
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setEditingFqa(null);
    setFormData({
      subject_name: '',
      question: '',
      answer: ''
    });
  };

  const handleOpenDetail = (faq) => {
    setSelectedFqa(faq);
    setShowDetailModal(true);
  };

  const handleCloseDetailModal = () => {
    setShowDetailModal(false);
    setSelectedFqa(null);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.subject_name.trim() || !formData.question.trim() || !formData.answer.trim()) {
      alert('请填写所有字段');
      return;
    }

    try {
      if (editingFqa) {
        await updateFaq(editingFqa.id, formData);
        alert('更新成功');
      } else {
        await createFaq(formData);
        alert('创建成功');
      }
      handleCloseModal();
      loadFaqs(searchKeyword.trim() || null);
    } catch (error) {
      console.error('保存FQA失败:', error);
      alert(error.message || '保存失败');
    }
  };

  const handleDelete = async (faqId, e) => {
    e.stopPropagation();
    if (!window.confirm('确定要删除这条FQA吗？')) {
      return;
    }

    try {
      await deleteFaq(faqId);
      alert('删除成功');
      loadFaqs(searchKeyword.trim() || null);
    } catch (error) {
      console.error('删除FQA失败:', error);
      alert(error.message || '删除失败');
    }
  };

  return (
    <div className="fqa-page">
      <div className="fqa-header">
        <h2>FQA管理</h2>
        <button className="add-fqa-btn" onClick={(e) => handleOpenModal(null, e)}>
          + 新增FQA
        </button>
      </div>

      <div className="fqa-search">
        <input
          type="text"
          placeholder="搜索学科或问题..."
          value={searchKeyword}
          onChange={(e) => setSearchKeyword(e.target.value)}
          onKeyPress={handleSearchKeyPress}
        />
        <button className="search-btn" onClick={handleSearch}>搜索</button>
        {searchKeyword && (
          <button className="clear-btn" onClick={handleClearSearch}>清除</button>
        )}
      </div>

      {loading ? (
        <div className="fqa-loading">加载中...</div>
      ) : faqs.length === 0 ? (
        <div className="fqa-empty">暂无FQA数据</div>
      ) : (
        <div className="fqa-list">
          {faqs.map(faq => (
            <div 
              key={faq.id} 
              className="fqa-item"
              onClick={() => handleOpenDetail(faq)}
            >
              <div className="fqa-item-header">
                <span className="fqa-subject">{faq.subject_name}</span>
                <div className="fqa-actions">
                  <button 
                    className="fqa-edit-btn"
                    onClick={(e) => handleOpenModal(faq, e)}
                  >
                    编辑
                  </button>
                  <button 
                    className="fqa-delete-btn"
                    onClick={(e) => handleDelete(faq.id, e)}
                  >
                    删除
                  </button>
                </div>
              </div>
              <div className="fqa-question">
                <strong>问：</strong>{faq.question}
              </div>
              <div className="fqa-answer">
                <strong>答：</strong>{faq.answer}
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal-content fqa-modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editingFqa ? '编辑FQA' : '新增FQA'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>学科名称</label>
                <input
                  type="text"
                  name="subject_name"
                  value={formData.subject_name}
                  onChange={handleInputChange}
                  placeholder="请输入学科名称"
                  maxLength={20}
                />
              </div>
              <div className="form-group">
                <label>问题</label>
                <textarea
                  name="question"
                  value={formData.question}
                  onChange={handleInputChange}
                  placeholder="请输入问题"
                  maxLength={1000}
                  rows={3}
                />
              </div>
              <div className="form-group">
                <label>答案</label>
                <textarea
                  name="answer"
                  value={formData.answer}
                  onChange={handleInputChange}
                  placeholder="请输入答案"
                  maxLength={1000}
                  rows={5}
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="cancel-btn" onClick={handleCloseModal}>
                  取消
                </button>
                <button type="submit" className="submit-btn">
                  {editingFqa ? '更新' : '创建'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showDetailModal && selectedFqa && (
        <div className="modal-overlay" onClick={handleCloseDetailModal}>
          <div className="modal-content fqa-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="fqa-detail-header">
              <span className="fqa-detail-subject">{selectedFqa.subject_name}</span>
              <button className="close-detail-btn" onClick={handleCloseDetailModal}>×</button>
            </div>
            <div className="fqa-detail-content">
              <div className="fqa-detail-question">
                <strong>问：</strong>{selectedFqa.question}
              </div>
              <div className="fqa-detail-answer">
                <strong>答：</strong>{selectedFqa.answer}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FqaPage;
