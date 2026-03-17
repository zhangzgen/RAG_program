import React from 'react';
import './PlaceholderPage.css';

const PlaceholderPage = ({ title, description }) => {
  return (
    <div className="placeholder-page">
      <div className="placeholder-content">
        <div className="placeholder-icon">
          {title === '配置信息' ? '⚙️' : '🔍'}
        </div>
        <h2 className="placeholder-title">{title}</h2>
        <p className="placeholder-description">{description}</p>
      </div>
    </div>
  );
};

export default PlaceholderPage;
