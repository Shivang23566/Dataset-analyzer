type Tab = 'upload' | 'eda' | 'visualization' | 'preprocess' | 'ml';

type SidebarProps = {
  active: Tab;
  onChange: (next: Tab) => void;
  hasFile: boolean;
};

export default function Sidebar({ active, onChange, hasFile }: SidebarProps) {
  const steps = [
    { id: 'upload' as Tab, num: 1, label: 'Upload Dataset' },
    { id: 'eda' as Tab, num: 2, label: 'EDA Overview' },
    { id: 'visualization' as Tab, num: 3, label: 'Visualization' },
    { id: 'preprocess' as Tab, num: 4, label: 'Preprocessing' },
    { id: 'ml' as Tab, num: 5, label: 'ML Builder' },
  ];

  return (
    <aside className="workspace-sidebar">
      <div className="sidebar-brand">
        <h2 className="sidebar-title">Dataset Analyser</h2>
      </div>
      <nav className="sidebar-nav">
        {steps.map((step) => {
          const isActive = active === step.id;
          const isDisabled = step.id !== 'upload' && !hasFile;
          return (
            <button
              key={step.id}
              className={`sidebar-nav-item${isActive ? ' sidebar-nav-item--active' : ''}${isDisabled ? ' sidebar-nav-item--disabled' : ''}`}
              onClick={() => onChange(step.id)}
              disabled={isDisabled}
            >
              <span className={`sidebar-nav-num${isActive ? ' sidebar-nav-num--active' : ''}`}>
                {step.num}
              </span>
              <span className="sidebar-nav-label">{step.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
