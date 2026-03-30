// frontend/src/components/MemoryTab.jsx
import React, { useState, useEffect } from 'react';

const MemoryTab = ({ userId = 'default' }) => {
  const [preferences, setPreferences] = useState({});
  const [historyTrips, setHistoryTrips] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPreferences();
  }, [userId]);

  const loadPreferences = async () => {
    try {
      const response = await fetch(`/api/preference/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setPreferences(data.preferences || {});
        setHistoryTrips(data.history_trips || []);
      }
    } catch (error) {
      console.error('Failed to load preferences:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddPreference = async (key, value) => {
    try {
      const response = await fetch(`/api/preference/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value })
      });
      if (response.ok) {
        setPreferences(prev => ({ ...prev, [key]: value }));
      }
    } catch (error) {
      console.error('Failed to update preference:', error);
    }
  };

  const formatPreferenceValue = (key, value) => {
    if (key.includes('budget') || key.includes('range')) {
      return `¥${value}`;
    }
    return value;
  };

  const getPreferenceIcon = (key) => {
    if (key.includes('cuisine') || key.includes('food')) return '🍜';
    if (key.includes('budget')) return '💰';
    if (key.includes('style') || key.includes('prefer')) return '📌';
    if (key.includes('destination')) return '📍';
    return '•';
  };

  if (loading) {
    return (
      <div className="memory-tab-loading">
        <div className="loading-dots">
          <span></span><span></span><span></span>
        </div>
        <span>Loading memory...</span>
      </div>
    );
  }

  return (
    <div className="memory-tab">
      {/* Session Context */}
      <div className="memory-section">
        <div className="memory-section-header">
          <span className="section-icon">🟢</span>
          <span>Session Context</span>
        </div>
        <div className="memory-section-content">
          <div className="memory-item">
            <span className="memory-label">Active for</span>
            <span className="memory-value">23 messages</span>
          </div>
          <div className="memory-item">
            <span className="memory-label">Last:</span>
            <span className="memory-value">"帮我规划杭州3日游"</span>
          </div>
        </div>
      </div>

      {/* Long-term Memory */}
      <div className="memory-section">
        <div className="memory-section-header">
          <span className="section-icon">📌</span>
          <span>Key Preferences</span>
        </div>
        <div className="memory-section-content">
          {Object.entries(preferences).length === 0 ? (
            <div className="memory-empty">
              No preferences set yet
            </div>
          ) : (
            Object.entries(preferences).map(([key, value]) => (
              <div key={key} className="memory-preference-item">
                <span className="preference-icon">{getPreferenceIcon(key)}</span>
                <span className="preference-key">{key}:</span>
                <span className="preference-value">{formatPreferenceValue(key, value)}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Past Trips */}
      {historyTrips.length > 0 && (
        <div className="memory-section">
          <div className="memory-section-header">
            <span className="section-icon">📅</span>
            <span>Past Trips</span>
          </div>
          <div className="memory-section-content">
            {historyTrips.map((trip, index) => (
              <div key={index} className="memory-trip-item">
                <span className="trip-date">{trip.date}</span>
                <span className="trip-destination">{trip.destination}</span>
                <span className="trip-duration">{trip.duration}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="memory-actions">
        <button className="memory-action-btn" onClick={() => {
          const key = window.prompt('Enter preference key (e.g., preferred_cuisine):');
          if (key) {
            const value = window.prompt('Enter preference value:');
            if (value) handleAddPreference(key, value);
          }
        }}>
          + Add Preference
        </button>
        <button className="memory-action-btn secondary" onClick={() => {
          const key = window.prompt('Enter preference key to edit:');
          if (key && preferences[key]) {
            const value = window.prompt('Enter new value:', preferences[key]);
            if (value) handleAddPreference(key, value);
          }
        }}>
          Edit
        </button>
        <button className="memory-action-btn secondary" onClick={() => {
          const data = JSON.stringify({ preferences, history_trips }, null, 2);
          console.log('Memory Export:', data);
          alert('Memory data logged to console. Backend export endpoint coming soon.');
        }}>
          Export
        </button>
      </div>
    </div>
  );
};

export default MemoryTab;