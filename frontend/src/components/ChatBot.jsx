import React, { useState, useRef, useEffect } from 'react';
import { MessageCircle, Send, X, Bot, Activity } from 'lucide-react';

const getWsUrl = () => {
  const url = import.meta.env.VITE_WS_URL || (
    window.location.hostname === 'localhost'
      ? 'http://localhost:8000'
      : window.location.origin
  );
  const wsUrl = url.replace('http', 'ws');
  return `${wsUrl}/ws/chat`;
};

const WS_URL = getWsUrl();

export default function ChatBot({ token, context }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'bot', content: "Hello! I'm your Multi-Agent Financial Advisor. Ask me anything about your analysis." }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const messagesEndRef = useRef(null);
  const socketRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, status]);

  // Connect WebSocket when opened
  useEffect(() => {
    if (isOpen && !socketRef.current) {
      socketRef.current = new WebSocket(WS_URL);

      socketRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'update') {
          setStatus({ agent: data.agent, content: data.content });
        } else if (data.type === 'result') {
          setMessages(prev => [...prev, { role: 'bot', content: data.content, agent: data.agent }]);
          setStatus(null);
          setLoading(false);
        } else if (data.type === 'error') {
          setMessages(prev => [...prev, { role: 'bot', content: data.content }]);
          setLoading(false);
        }
      };

      socketRef.current.onclose = () => {
        socketRef.current = null;
        console.log("WebSocket closed");
      };
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.close(); // Prevent connection leak on unmount
        socketRef.current = null;
      }
    };
  }, [isOpen]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setMessages(prev => [...prev, { role: 'bot', content: "Lost connection to advisor. Please try again." }]);
      return;
    }

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    
    // Send data via WebSocket
    socketRef.current.send(JSON.stringify({
      message: input,
      context: context,
      token: token
    }));

    setInput('');
    setLoading(true);
    setStatus({ agent: "Supervisor", content: "Routing your request..." });
  };

  return (
    <div className="chatbot-container">
      {!isOpen && (
        <button className="chat-bubble" onClick={() => setIsOpen(true)}>
          <Activity size={28} color="white" className="pulse" />
          <span className="chat-badge">Agent AI</span>
        </button>
      )}

      {isOpen && (
        <div className="chat-window glass-panel">
          <div className="chat-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div className="bot-avatar">
                <Bot size={20} color="white" />
              </div>
              <div>
                <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>Financial Advisor Team</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--success)' }}>● Multi-Agent Active</div>
              </div>
            </div>
            <button className="close-chat" onClick={() => setIsOpen(false)}>
              <X size={20} />
            </button>
          </div>

          <div className="chat-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message-row ${msg.role === 'bot' ? 'bot-row' : 'user-row'}`}>
                <div className={`message-bubble ${msg.role === 'bot' ? 'bot-bubble' : 'user-bubble'}`}>
                  {msg.agent && <div className="agent-tag">{msg.agent}</div>}
                  {msg.content}
                </div>
              </div>
            ))}
            
            {status && (
              <div className="message-row bot-row">
                <div className="message-bubble bot-bubble status-update">
                  <div className="agent-tag">{status.agent}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div className="typing-indicator">
                      <span></span><span></span><span></span>
                    </div>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{status.content}</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chat-input-area" onSubmit={handleSend}>
            <input 
              type="text" 
              placeholder="Ask our agents anything..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button type="submit" disabled={!input.trim() || loading}>
              <Send size={18} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
