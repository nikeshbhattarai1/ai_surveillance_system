import { NavLink } from 'react-router-dom';

const LINKS = [
  { to: '/', label: 'HOME' },
  { to: '/live-feed', label: 'LIVE FEED' },
  { to: '/video-upload', label: 'VIDEO UPLOAD' },
  { to: '/history', label: 'DETECTION HISTORY' },
];

export default function Navbar() {
  return (
    <header style={styles.bar}>
      <div style={styles.logo}>
        <span style={styles.logoBadge}>AI SURVEILLANCE v1.0</span>
      </div>

      <nav style={styles.nav}>
        {LINKS.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              ...styles.link,
              color: isActive ? 'var(--green-threat)' : 'var(--text-secondary)',
              borderBottom: isActive
                ? '1px solid var(--green-threat)'
                : '1px solid transparent',
            })}
          >
            {label}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}

const styles = {
  bar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 24px',
    background: 'var(--bg-panel)',
    borderBottom: '1px solid var(--bg-border)',
    flexShrink: 0,
  },
  logo: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 12,
  },
  logoText: {
    fontFamily: 'var(--font-display)',
    fontSize: 24,
    fontWeight: 700,
    letterSpacing: '0.2em',
    color: 'var(--green-threat)',
    textShadow: '0 0 20px var(--green-glow)',
    textDecoration: 'none',
  },
  logoBadge: {
    fontFamily: 'var(--font-mono)',
    fontSize: 10,
    color: 'var(--text-dim)',
    letterSpacing: '0.15em',
  },
  nav: {
    display: 'flex',
    gap: 32,
  },
  link: {
    fontFamily: 'var(--font-mono)',
    fontSize: 11,
    letterSpacing: '0.12em',
    textDecoration: 'none',
    paddingBottom: 4,
    transition: 'color 0.2s, border-color 0.2s',
  },
};