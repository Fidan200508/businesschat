import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || (
  window.location.hostname === 'localhost' ? 'http://localhost:8000' : '/api'
);

export default function History({ token }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await axios.get(`${API_URL}/history`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setHistory(response.data);
      } catch (err) {
        console.error("Failed to load history", err);
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [token]);

  if (loading) {
    return <div style={{ textAlign: 'center', marginTop: '3rem' }}>Loading history...</div>;
  }

  return (
    <div className="glass-panel">
      <h2 style={{ marginBottom: '2rem' }}>Prediction History</h2>
      
      {history.length === 0 ? (
        <p style={{ color: 'var(--text-muted)' }}>You haven't made any predictions yet.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Assets</th>
                <th>Liabilities</th>
                <th>D/E Ratio</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {history.map((record) => (
                <tr key={record.id}>
                  <td>{new Date(record.created_at).toLocaleDateString()}</td>
                  <td>${record.total_assets.toLocaleString()}</td>
                  <td>${record.total_liabilities.toLocaleString()}</td>
                  <td>{record.debt_equity_ratio.toFixed(2)}</td>
                  <td>
                    {record.risk_label === 0 ? (
                      <span className="status-badge status-good">Low Risk</span>
                    ) : (
                      <span className="status-badge status-bad">High Risk</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
