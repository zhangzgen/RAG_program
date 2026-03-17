import React, { useState } from 'react';
import { sendVerificationCode, login } from '../api';
import './Login.css';

function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [sendingCode, setSendingCode] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [error, setError] = useState('');

  // 验证邮箱格式
  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  // 发送验证码
  const handleSendCode = async () => {
    setError('');
    
    if (!email) {
      setError('请输入邮箱地址');
      return;
    }

    if (!validateEmail(email)) {
      setError('请输入有效的邮箱地址');
      return;
    }

    setSendingCode(true);
    try {
      await sendVerificationCode(email);
      // 开始倒计时
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err) {
      setError(err.message || '验证码发送失败');
    } finally {
      setSendingCode(false);
    }
  };

  // 登录
  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !verificationCode) {
      setError('请填写邮箱和验证码');
      return;
    }

    if (!validateEmail(email)) {
      setError('请输入有效的邮箱地址');
      return;
    }

    setLoading(true);
    try {
      const response = await login(email, verificationCode);
      
      // 保存token和用户信息到localStorage
      localStorage.setItem('token', response.token);
      localStorage.setItem('user', JSON.stringify({
        user_id: response.user_id,
        email: response.email
      }));

      // 通知父组件登录成功
      if (onLoginSuccess) {
        onLoginSuccess(response);
      }
    } catch (err) {
      setError(err.message || '登录失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <h1>智能问答系统</h1>
          <p>请使用邮箱验证码登录</p>
        </div>

        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label htmlFor="email">邮箱地址</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="请输入您的邮箱"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="code">验证码</label>
            <div className="code-input-group">
              <input
                type="text"
                id="code"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                placeholder="请输入6位验证码"
                maxLength={6}
                disabled={loading}
              />
              <button
                type="button"
                className="send-code-btn"
                onClick={handleSendCode}
                disabled={sendingCode || countdown > 0 || loading}
              >
                {sendingCode ? '发送中...' : countdown > 0 ? `${countdown}秒后重试` : '发送验证码'}
              </button>
            </div>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" className="login-btn" disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <div className="login-footer">
          <p>首次登录将自动创建账号</p>
        </div>
      </div>
    </div>
  );
}

export default Login;
