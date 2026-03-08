import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import UploaderPanel from '../components/UploaderPanel';
import EDAView from '../components/EDAView';
import VisualizationView from '../components/VisualizationView';
import PreprocessingView from '../components/PreprocessingView';
import MLBuilderView from '../components/MLBuilderView';
import { getLoggedInEmail } from '../lib/authStore';
import { logout } from '../lib/api';

type Tab = 'upload' | 'eda' | 'visualization' | 'preprocess' | 'ml';

export default function WorkspacePage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [fileName, setFileName] = useState('');
  const [processedFileName, setProcessedFileName] = useState('');

  const onLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <main className="workspace-layout">
      <Sidebar active={activeTab} onChange={setActiveTab} hasFile={Boolean(fileName)} />

      <section className="workspace-content">
        <header className="workspace-header">
          <div>
            <h1>Dataset Workspace</h1>
            <p>{getLoggedInEmail()}</p>
          </div>
          <button className="btn btn-ghost" onClick={onLogout}>
            <LogOut size={16} /> Logout
          </button>
        </header>

        {activeTab === 'upload' ? (
          <UploaderPanel
            currentFile={fileName}
            onUploaded={(uploaded) => {
              setFileName(uploaded);
              setProcessedFileName('');
              setActiveTab('eda');
            }}
          />
        ) : null}

        {activeTab === 'eda' && fileName ? <EDAView filename={fileName} /> : null}
        {activeTab === 'visualization' && fileName ? <VisualizationView filename={fileName} /> : null}
        {activeTab === 'preprocess' && fileName ? (
          <PreprocessingView
            filename={fileName}
            onProcessed={(pf) => setProcessedFileName(pf)}
          />
        ) : null}
        {activeTab === 'ml' && fileName ? (
          <MLBuilderView filename={processedFileName || fileName} />
        ) : null}
      </section>
    </main>
  );
}
