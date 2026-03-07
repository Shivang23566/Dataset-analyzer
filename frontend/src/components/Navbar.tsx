import { Link } from 'react-router-dom';

export default function Navbar() {
  return (
    <header className="nav-shell">
      <div className="brand-pill">Dataset Analyzer</div>
      <nav className="nav-links">
        <a href="#features">Features</a>
        <a href="#workflow">Workflow</a>
        <a href="#trust">Trust</a>
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
