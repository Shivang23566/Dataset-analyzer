type SidebarProps = {
  active: 'upload' | 'eda' | 'visualization';
  onChange: (next: SidebarProps['active']) => void;
  hasFile: boolean;
};

export default function Sidebar({ active, onChange, hasFile }: SidebarProps) {
  return (
    <aside className="workspace-sidebar">
      <h2>Analysis Flow</h2>
      <button
        className={active === 'upload' ? 'active' : ''}
        onClick={() => onChange('upload')}
      >
        1. Upload Dataset
      </button>
      <button
        className={active === 'eda' ? 'active' : ''}
        onClick={() => onChange('eda')}
        disabled={!hasFile}
      >
        2. EDA Overview
      </button>
      <button
        className={active === 'visualization' ? 'active' : ''}
        onClick={() => onChange('visualization')}
        disabled={!hasFile}
      >
        3. Visualization
      </button>
    </aside>
  );
}
