import { Link } from 'react-router-dom';

export default function Navbar() {
  return (
    <header className="nav-shell">
      <div className="brand-pill">
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          style={{ display: 'inline', marginRight: 8, verticalAlign: 'middle' }}
        >
          <line x1="4" y1="20" x2="4" y2="14" />
          <line x1="8" y1="20" x2="8" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="16" y1="20" x2="16" y2="8" />
          <line x1="20" y1="20" x2="20" y2="12" />
        </svg>
        DataLens
      </div>
      <nav className="nav-links">
        <a href="#features">Features</a>
        <a href="#workflow">Workflow</a>
        <a href="#pricing">Pricing</a>
      </nav>
      <div className="nav-actions">
        <Link to="/login" className="btn btn-ghost">
          Login
        </Link>
        <Link to="/signup" className="btn btn-primary">
          Start Free
        </Link>
      </div>
    </header>
  );
}
