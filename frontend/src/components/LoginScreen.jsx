import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function LoginScreen() {
    const { login, register } = useAuth();

    const [mode, setMode] = useState('login');   // 'login' | 'register'
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        setError(''); setLoading(true);
        try {
            if (mode === 'login') {
                await login(email, password);
            } else {
                await register(email, password, name);
            }
        } catch (e) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleKey = (e) => { if (e.key === 'Enter') handleSubmit(); };

    return (
        <div style={styles.root}>
            <div style={styles.gridBg} />

            <div style={styles.card}>
                <div style={styles.logoBlock}>
                    <div style={styles.logoSub}>AI SURVEILLANCE SYSTEM</div>
                    <div style={styles.logoDivider} />
                </div>

                <div style={styles.modeToggle}>
                    {['login', 'register'].map((m) => (
                        <button
                            key={m}
                            onClick={() => { setMode(m); setError(''); }}
                            style={{
                                ...styles.modeBtn,
                                borderBottomColor: mode === m ? 'var(--green-threat)' : 'transparent',
                                color: mode === m ? 'var(--green-threat)' : 'var(--text-dim)',
                            }}
                        >
                            {m.toUpperCase()}
                        </button>
                    ))}
                </div>

                <div style={styles.fields}>
                    {mode === 'register' && (
                        <Field
                            label="FULL NAME"
                            value={name}
                            onChange={setName}
                            placeholder="Rahul Shrestha"
                            onKeyDown={handleKey}
                        />
                    )}
                    <Field
                        label="EMAIL ADDRESS"
                        value={email}
                        onChange={setEmail}
                        type="email"
                        placeholder="operator@security.local"
                        onKeyDown={handleKey}
                    />
                    <Field
                        label="PASSWORD"
                        value={password}
                        onChange={setPassword}
                        type="password"
                        placeholder="••••••••"
                        onKeyDown={handleKey}
                    />
                </div>

                {error && (
                    <div style={styles.error}>
                        ✗ {error}
                    </div>
                )}

                <button
                    onClick={handleSubmit}
                    disabled={loading || !email || !password}
                    style={{
                        ...styles.submitBtn,
                        opacity: (loading || !email || !password) ? 0.4 : 1,
                        cursor: (loading || !email || !password) ? 'not-allowed' : 'pointer',
                    }}
                >
                    {loading
                        ? '...'
                        : mode === 'login' ? '▶ AUTHENTICATE' : '▶ CREATE ACCOUNT'}
                </button>

                <div style={styles.footer}>
                    SECURED WITH JWT + BCRYPT
                </div>
            </div>
        </div>
    );
}

function Field({ label, value, onChange, type = 'text', placeholder, onKeyDown }) {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label style={{
                fontSize: 9,
                letterSpacing: '0.2em',
                color: 'var(--text-dim)',
                fontFamily: 'var(--font-mono)',
            }}>
                {label}
            </label>
            <input
                type={type}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder={placeholder}
                style={{
                    background: 'var(--bg-void)',
                    border: '1px solid var(--bg-border)',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 13,
                    padding: '9px 12px',
                    outline: 'none',
                    width: '100%',
                    transition: 'border-color 0.2s',
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--green-dim)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--bg-border)'}
            />
        </div>
    );
}

const styles = {
    root: {
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-void)',
        position: 'relative',
        overflow: 'hidden',
    },
    gridBg: {
        position: 'absolute',
        inset: 0,
        backgroundImage: `
      linear-gradient(var(--bg-border) 1px, transparent 1px),
      linear-gradient(90deg, var(--bg-border) 1px, transparent 1px)
    `,
        backgroundSize: '48px 48px',
        opacity: 0.4,
    },
    card: {
        position: 'relative',
        zIndex: 1,
        width: 360,
        background: 'var(--bg-panel)',
        border: '1px solid var(--bg-border)',
        padding: '32px 28px',
        display: 'flex',
        flexDirection: 'column',
        gap: 20,
        boxShadow: '0 0 60px rgba(0,0,0,0.8)',
    },
    logoBlock: {
        textAlign: 'center',
    },
    logoText: {
        fontFamily: 'var(--font-display)',
        fontSize: 32,
        fontWeight: 700,
        letterSpacing: '0.25em',
        color: 'var(--green-threat)',
        textShadow: '0 0 30px var(--green-glow)',
    },
    logoSub: {
        fontFamily: 'var(--font-mono)',
        fontSize: 9,
        letterSpacing: '0.2em',
        color: 'var(--text-dim)',
        marginTop: 4,
    },
    logoDivider: {
        height: 1,
        background: 'linear-gradient(90deg, transparent, var(--green-dim), transparent)',
        marginTop: 16,
    },
    modeToggle: {
        display: 'flex',
        borderBottom: '1px solid var(--bg-border)',
    },
    modeBtn: {
        flex: 1,
        background: 'none',
        border: 'none',
        borderBottom: '2px solid',
        padding: '6px 0',
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        letterSpacing: '0.15em',
        cursor: 'pointer',
        transition: 'all 0.2s',
    },
    fields: {
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
    },
    error: {
        fontSize: 11,
        color: 'var(--red-critical)',
        border: '1px solid var(--red-critical)',
        padding: '6px 10px',
        letterSpacing: '0.05em',
    },
    submitBtn: {
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '0.2em',
        padding: '11px',
        border: '1px solid var(--green-threat)',
        background: 'var(--green-glow)',
        color: 'var(--green-threat)',
        width: '100%',
        transition: 'all 0.2s',
    },
    footer: {
        textAlign: 'center',
        fontSize: 9,
        color: 'var(--text-dim)',
        letterSpacing: '0.15em',
    },
};