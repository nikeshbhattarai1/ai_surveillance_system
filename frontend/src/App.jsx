import { Routes, Route } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginScreen from './components/LoginScreen';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import LiveFeed from './pages/LiveFeed';
import VideoUpload from './pages/VideoUpload';
import DetectionHistory from './pages/DetectionHistory';

function AppShell() {
  const { user, loading } = useAuth();

  if (loading) return (
    <div style={{
      height: '100vh', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-void)',
      color: 'var(--green-dim)',
      fontFamily: 'var(--font-mono)',
      fontSize: 11,
      letterSpacing: '0.2em',
    }}>
      INITIALIZING...
    </div>
  );

  if (!user) return <LoginScreen />;
  return <AppInner />;
}

function AppInner() {
  const { user, logout } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ flex: 1 }}>
          <Navbar />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16, paddingRight: 24 }}>
          <span style={{ fontSize: 10, color: 'var(--text-secondary)', letterSpacing: '0.1em' }}>
            {user?.email}
            <span style={{
              marginLeft: 8,
              color: 'var(--green-dim)',
              border: '1px solid var(--green-dim)',
              padding: '1px 6px',
              fontSize: 9,
            }}>
              {user?.role?.toUpperCase()}
            </span>
          </span>
          <button
            onClick={logout}
            style={{
              background: 'none',
              border: '1px solid var(--bg-border)',
              color: 'var(--text-dim)',
              fontFamily: 'var(--font-mono)',
              fontSize: 9,
              letterSpacing: '0.15em',
              padding: '3px 10px',
              cursor: 'pointer',
            }}
          >
            LOGOUT
          </button>
        </div>
      </div>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/live-feed" element={<LiveFeed />} />
        <Route path="/video-upload" element={<VideoUpload />} />
        <Route path="/history" element={<DetectionHistory />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}