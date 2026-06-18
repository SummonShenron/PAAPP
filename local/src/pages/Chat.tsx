import React, { useEffect, useState, useRef } from 'react';
import sonicImg from '../assets/sonicandshadow.jpg';
import { api } from '../api'; 
import sonicSpinImg from '../assets/sonic-rolling.gif';
import shadowSpinImg from '../assets/shadow.gif';
import friezaImg from '../assets/frieza.jpg';
import friezaGif from '../assets/frieza.gif';

interface Message {
  sender: 'user' | 'ai' | 'system';
  text: string;
}

interface ChatPageProps {
  onExit: () => void;
}

export const ChatPage: React.FC<ChatPageProps> = ({ onExit }) => {
  // Grab current authorized user signature
  const [username] = useState(() => localStorage.getItem('x-user-id') || 'Jack H.');
  
  // 1. Warm-initialize the messages state from localStorage to prevent auto-clearing
  const [messages, setMessages] = useState<Message[]>(() => {
    const persistedHistory = localStorage.getItem(`chat-messages-${username}`);
    if (persistedHistory) {
      try {
        return JSON.parse(persistedHistory);
      } catch (e) {
        console.error("Failed to parse persisted conversation logs:", e);
      }
    }
    return [
      { sender: 'system', text: `Good day, ${username.split(' ')[0]}. What can I handle for your schedule or dashboard today?` }
    ];
  });
  
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  
  const [theme, setTheme] = useState<'sonic' | 'shadow'>(() => {
    const savedTheme = localStorage.getItem('saapp-theme');
    return (savedTheme === 'shadow' || savedTheme === 'sonic') ? savedTheme : 'sonic';
  });

  const chatWindowRef = useRef<HTMLDivElement>(null);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'sonic' ? 'shadow' : 'sonic'));
  };

  // 2. Clear history updates both reactive states and physical client-side storage keys
  const handleClearChat = () => {
    const initialMessage: Message[] = [
      { sender: 'system', text: `Cleared. What else can I tackle for you, Jack?` }
    ];
    setMessages(initialMessage);
    localStorage.removeItem(`chat-messages-${username}`);
  };

  // 3. Sync themes to localStorage
  useEffect(() => {
    localStorage.setItem('saapp-theme', theme);
  }, [theme]);

  // 4. Clean side-effect trigger: Auto-sync dialogue history to localStorage on any message mutations
  useEffect(() => {
    localStorage.setItem(`chat-messages-${username}`, JSON.stringify(messages));
  }, [messages, username]);

  // Reliable scroll anchor alignment
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTo({
        top: chatWindowRef.current.scrollHeight,
        behavior: 'smooth'
      });
    }
  }, [messages, loading]);

  const handleSendMessage = async (textToSend: string) => {
    if (!textToSend.trim() || loading) return;

    const userMsg = { sender: 'user' as const, text: textToSend };
    setMessages(prev => [...prev, userMsg, { sender: 'ai' as const, text: '' }]);
    setInput('');
    setLoading(true);

    try {
      await api.sendChatMessage(username, textToSend, (newToken) => {
        setMessages(prev => {
          const updated = [...prev];
          const lastIndex = updated.length - 1;
          if (updated[lastIndex] && updated[lastIndex].sender === 'ai') {
            updated[lastIndex] = {
              ...updated[lastIndex],
              text: updated[lastIndex].text + newToken
            };
          }
          return updated;
        });
      });
    } catch (error) {
      console.error(error);
      setMessages(prev => [...prev, { sender: 'ai', text: "Assistant connection timed out. Check local tool hooks." }]);
    } finally {
      setLoading(false);
    }
  };

  const onSubmitForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    handleSendMessage(input);
  };

  // Determine whether user has engaged in active dialogue with the agent
  const hasChatted = messages.some(msg => msg.sender === 'user');

  // Hardcoded core helper action starters
  const agentQuickPrompts = [
    "Schedule a Coding Session for Sunday at 3 PM",
    "change my recent Arc Raiders session to be 1 hour instead of 30 minutes",
    "What's on my agenda for today?"
  ];

  return (
    // Instead of two nested layout divs, we keep ONE root wrapper component and merge them!
    <div className={`portal-container ${theme === 'shadow' ? 'theme-shadow' : ''}`}>
      
      <nav className="menu-navigator">
        <div className="nav-logo">
          <a href="/" style={{ textDecoration: 'none' }}> 
            {theme === 'sonic' ? '⚡Final Form' : '⚡Black Form'}
          </a>
        </div>
        <div className="nav-links">
          <span onClick={toggleTheme} className="theme-toggle-btn">
            {theme === 'sonic' ? 'Hero' : 'Dark'}
          </span>
          <span className="active">Cockpit</span>
          <span onClick={onExit} className="nav-exit">Disconnect</span>
        </div>
      </nav>

      <header className="hero-banner" style={{ backgroundImage: `linear-gradient(rgba(18, 24, 36, 0.7), rgba(18, 24, 36, 0.95)), url(${friezaImg})` }}>
        <div className="banner-context">
          <h3>{theme === 'sonic' ? 'Personal Executive Assistant' : 'Shadow Automation Hub'}</h3>
          <h4>{theme === 'sonic' ? 'Managing schedules at the speed of sound.' : 'Chaos Control Automation Engine.'}</h4>
        </div>
      </header>

      <main className={`portal-body ${!hasChatted ? 'initial-state-view' : ''}`}>
        {!hasChatted && (
          <div className="example-cards-container">
            {agentQuickPrompts.map((q, idx) => (
              <div key={idx} className="query-card" onClick={() => !loading && handleSendMessage(q)}>
                <p>{q}</p>
                <span>→</span>
              </div>
            ))}
          </div>
        )}

        {hasChatted && (
          <div className="chat-window" ref={chatWindowRef}>
            {messages
              .filter(msg => msg.sender !== 'system') // Simplified filtering logic
              .map((msg, index) => (
                <div key={index} className={`message-bubble ${msg.sender}`}>
                  <div className="message-sender">{msg.sender.toUpperCase()}</div>
                  <div className="message-text">{msg.text}</div>
                </div>
              ))}
              
            {loading && (
              <div className="message-bubble ai thinking sonic-loader-container">
                <img 
                  src={theme === 'sonic' ? friezaGif : friezaGif} 
                  alt="Spinning..." 
                  className={theme === 'sonic' ? "sonic-spin-gif" : "shadow-spin-gif"} 
                  />
                <div className="loading-text">
                  Executing automated agent instructions...
                </div>
              </div>
            )}
          </div>
        )}

        <footer className="controls-footer">
          <form onSubmit={onSubmitForm} className="chat-input-area">
            <input
              type="text"
              placeholder="Ask a question or update your Google Calendar..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
            />
            <button className="submit-button" type="submit" disabled={loading || !input.trim()}>Send</button>
            <button
              className="clear-button" 
              type="button" 
              onClick={handleClearChat} 
              disabled={loading}
              style={{ backgroundColor: '#334155', marginLeft: '0.5rem' }}
            >
              Clear
            </button>
          </form>
        </footer>
      </main>
    </div>
  );
};