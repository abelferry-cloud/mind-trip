// frontend/src/components/FeatureCards.jsx
import React, { useState } from 'react';

const FEATURE_CARDS = [
  { id: 'attractions', icon: '🗺️', label: '景点推荐', status: 'coming_soon' },
  { id: 'route', icon: '📍', label: '路线规划', status: 'coming_soon' },
  { id: 'budget', icon: '💰', label: '预算控制', status: 'coming_soon' },
  { id: 'food', icon: '🍜', label: '美食推荐', status: 'coming_soon' },
  { id: 'hotel', icon: '🏨', label: '酒店预订', status: 'coming_soon' },
];

const FeatureCards = () => {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleFeatureClick = (feature) => {
    if (feature.status === 'coming_soon') {
      // Future: Navigate to feature or show modal
      console.log(`Feature ${feature.id} clicked (coming soon)`);
    }
  };

  return (
    <div className="feature-cards">
      <div
        className="feature-cards-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="feature-cards-title">功能</span>
        <button className="feature-cards-toggle">
          {isExpanded ? '−' : '+'}
        </button>
      </div>

      {isExpanded && (
        <div className="feature-cards-list">
          {FEATURE_CARDS.map((feature) => (
            <div
              key={feature.id}
              className={`feature-card ${feature.status}`}
              onClick={() => handleFeatureClick(feature)}
            >
              <span className="feature-card-icon">
                {feature.status === 'coming_soon' ? '🔒' : feature.icon}
              </span>
              <span className="feature-card-label">{feature.label}</span>
              {feature.status === 'coming_soon' && (
                <span className="feature-card-badge">即将上线</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FeatureCards;