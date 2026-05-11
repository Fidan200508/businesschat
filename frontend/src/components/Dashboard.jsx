import React, { useState } from 'react';
import axios from 'axios';
import ChatBot from './ChatBot';

const API_URL = import.meta.env.VITE_API_URL || (
  window.location.hostname === 'localhost' ? 'http://localhost:8000' : '/api'
);

function formatApiError(detail) {
  if (!detail) {
    return 'Failed to analyze risk';
  }

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : 'field';
        return `${field}: ${item.msg || 'Invalid value'}`;
      })
      .join(', ');
  }

  return 'Failed to analyze risk';
}

export default function Dashboard({ token }) {
  const [formData, setFormData] = useState({
    total_assets: 1000000.0,
    total_liabilities: 100000.0,
    revenue: 2000000.0,
    current_assets: 500000.0,
    cash_flow: 100000.0,
    net_income: 50000.0,
    operating_income: 75000.0,
    current_liabilities: 250000.0,
    credit_score: 700.0
  });

  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: parseFloat(e.target.value) || 0 });
  };

  const handleAnalyze = async () => {
    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await axios.post(`${API_URL}/predict`, formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setResult(response.data);
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>Corporate Financial Profile</h1>

      <div className="grid-2">
        <div className="glass-panel">
          <h3 style={{ marginBottom: '1.5rem', color: 'var(--primary)' }}>Assets & Liabilities</h3>

          <div className="input-group">
            <label>Total Assets ($)</label>
            <input type="number" name="total_assets" className="input-field" value={formData.total_assets} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Total Liabilities ($)</label>
            <input type="number" name="total_liabilities" className="input-field" value={formData.total_liabilities} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Current Assets ($)</label>
            <input type="number" name="current_assets" className="input-field" value={formData.current_assets} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Current Liabilities ($)</label>
            <input type="number" name="current_liabilities" className="input-field" value={formData.current_liabilities} onChange={handleChange} />
          </div>
        </div>

        <div className="glass-panel">
          <h3 style={{ marginBottom: '1.5rem', color: 'var(--primary)' }}>Income & Cash Flow</h3>

          <div className="input-group">
            <label>Revenue ($)</label>
            <input type="number" name="revenue" className="input-field" value={formData.revenue} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Net Income ($)</label>
            <input type="number" name="net_income" className="input-field" value={formData.net_income} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Operating Income ($)</label>
            <input type="number" name="operating_income" className="input-field" value={formData.operating_income} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Cash Flow ($)</label>
            <input type="number" name="cash_flow" className="input-field" value={formData.cash_flow} onChange={handleChange} />
          </div>
          <div className="input-group">
            <label>Credit Score</label>
            <input type="number" name="credit_score" className="input-field" value={formData.credit_score} onChange={handleChange} min="300" max="850" />
          </div>
        </div>
      </div>

      <div style={{ marginTop: '2rem', textAlign: 'center' }}>
        <button className="btn" onClick={handleAnalyze} disabled={loading} style={{ padding: '1rem 3rem', fontSize: '1.1rem' }}>
          {loading ? 'Analyzing...' : 'Analyze Financial Health'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginTop: '2rem' }}>
          {error}
        </div>
      )}

      {result && (
        <div className="glass-panel" style={{ marginTop: '2rem', animation: 'fadeIn 0.5s ease' }}>
          <h2 style={{ marginBottom: '1.5rem' }}>Analysis Result</h2>

          <div style={{ marginBottom: '2rem' }}>
            {result.risk_label === 0 ? (
              <div className="alert alert-success" style={{ fontSize: '1.25rem', padding: '1.5rem', textAlign: 'center' }}>
                🌟 STATUS: LOWER RISK (GOOD)
              </div>
            ) : (
              <div className="alert alert-error" style={{ fontSize: '1.25rem', padding: '1.5rem', textAlign: 'center' }}>
                ⚠️ STATUS: HIGHER RISK (BAD)
              </div>
            )}
          </div>

          <div className="grid-2">
            <div className="metric-card">
              <div className="metric-label">Calculated Debt-Equity Ratio</div>
              <div className="metric-value">
                {Number.isFinite(Number(result.debt_equity_ratio)) ? Number(result.debt_equity_ratio).toFixed(2) : 'N/A'}
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Total Assets</div>
              <div className="metric-value">${formData.total_assets.toLocaleString()}</div>
            </div>

            <div className="metric-card" style={{ gridColumn: 'span 2', marginTop: '1rem' }}>
              <h3 style={{ marginBottom: '1rem', color: 'var(--text)' }}>AI Explainability (Top Factors)</h3>
              {result.explanations && result.explanations.length > 0 ? (
                <ul style={{ listStyleType: 'none', padding: 0 }}>
                  {result.explanations.map((exp, idx) => (
                    <li key={idx} style={{ marginBottom: '0.8rem', fontSize: '1.1rem', borderLeft: '3px solid var(--primary)', paddingLeft: '1rem' }}>
                      <strong style={{ color: 'var(--primary)' }}>{exp.feature}</strong>: 
                      This factor <span style={{ color: exp.impact.includes('increases') ? 'var(--error)' : 'var(--success)', fontWeight: 'bold' }}>{exp.impact}</span>.
                    </li>
                  ))}
                </ul>
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>No detailed explanation available for this prediction.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ChatBot with Context */}
      <ChatBot token={token} context={result} />
    </div>
  );
}
