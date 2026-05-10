import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import History from './components/History';
import { LogOut, Activity, Clock } from 'lucide-react';
import './index.css';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }, [token]);

  const handleLogout = () => {
    setToken(null);
  };

  return (
    <Router>
      {token && (
        <nav className="navbar">
          <Link to="/" className="nav-brand">
            <Activity color="var(--primary)" />
            Corporate Loan Risk AI
          </Link>
          <div className="nav-links">
            <Link to="/">Dashboard</Link>
            <Link to="/history">
              <Clock size={18} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
              History
            </Link>
            <button onClick={handleLogout}>
              <LogOut size={18} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
              Logout
            </button>
          </div>
        </nav>
      )}

      <div className="container">
        <Routes>
          <Route 
            path="/login" 
            element={!token ? <Login setToken={setToken} /> : <Navigate to="/" />} 
          />
          <Route 
            path="/" 
            element={token ? <Dashboard token={token} /> : <Navigate to="/login" />} 
          />
          <Route 
            path="/history" 
            element={token ? <History token={token} /> : <Navigate to="/login" />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
