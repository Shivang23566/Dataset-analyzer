import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, FileSpreadsheet, CheckCircle } from 'lucide-react';
import { uploadDataset } from '../lib/api';

type UploaderPanelProps = {
  currentFile: string;
  onUploaded: (fileName: string) => void;
};

const UPLOAD_PHASES = [
  'Uploading Dataset',
  'Parsing Schema',
  'Indexing Columns',
  'Finalizing Upload',
] as const;

const MIN_LOADER_MS = 3000;
const PHASE_INTERVAL_MS = MIN_LOADER_MS / UPLOAD_PHASES.length;

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export default function UploaderPanel({ currentFile, onUploaded }: UploaderPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Cycle through phase labels while loading
  useEffect(() => {
    if (!loading) {
      setPhaseIndex(0);
      return;
    }
    const id = setInterval(() => {
      setPhaseIndex((prev) => (prev + 1) % UPLOAD_PHASES.length);
    }, PHASE_INTERVAL_MS);
    return () => clearInterval(id);
  }, [loading]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
    setError('');
  };

  const handleUpload = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError('Choose a CSV or JSON dataset first.');
      return;
    }

    setError('');
    setLoading(true);
    const t0 = Date.now();

    try {
      const result = await uploadDataset(file);
      // Guarantee the animation shows for the full minimum duration
      const elapsed = Date.now() - t0;
      if (elapsed < MIN_LOADER_MS) await sleep(MIN_LOADER_MS - elapsed);
      onUploaded(result.saved_as);
      setFile(null);
    } catch (err) {
      const elapsed = Date.now() - t0;
      if (elapsed < MIN_LOADER_MS) await sleep(MIN_LOADER_MS - elapsed);
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const triggerFileSelect = () => fileInputRef.current?.click();

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <section className="panel uploader-panel">
      <AnimatePresence mode="wait">
        {loading ? (
          /* ─── LOADING STATE ─────────────────────────── */
          <motion.div
            key="loader"
            className="upload-loader-container"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
          >
            {/* Noise texture overlay */}
            <div className="ul-noise" aria-hidden="true" />

            {/* Sweeping background lines */}
            <div className="upload-longfazers" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
            </div>

            {/* ── Corner: top-left brand ── */}
            <div className="ul-corner ul-corner--tl">
              <div className="ul-brand">
                <span className="ul-brand-dot" />
                DATASET ANALYZER
              </div>
            </div>

            {/* ── Corner: top-right processing status ── */}
            <div className="ul-corner ul-corner--tr">
              <div className="ul-status-label">PROCESSING</div>
              <div className="ul-status-sub">SCHEMA: ACTIVE</div>
            </div>

            {/* ── Character loader ── */}
            <div className="upload-loader-scene">
              <div className="upload-loader">
                <span>
                  <span />
                  <span />
                  <span />
                  <span />
                </span>
                <div className="upload-loader-base">
                  <span />
                  <div className="upload-loader-face" />
                </div>
              </div>
            </div>

            {/* ── Centre info ── */}
            <div className="upload-loader-info">
              <AnimatePresence mode="wait">
                <motion.h3
                  key={phaseIndex}
                  className="upload-loader-title"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.25 }}
                >
                  {UPLOAD_PHASES[phaseIndex]}
                </motion.h3>
              </AnimatePresence>
              <p className="upload-loader-subtitle">
                {file?.name ?? 'your file'}
              </p>
              <div className="upload-progress-track">
                <div className="upload-progress-bar" />
              </div>
            </div>

            {/* ── Corner: bottom-left nominal ── */}
            <div className="ul-corner ul-corner--bl">
              <div className="ul-nominal">
                <span className="ul-nominal-dot" />
                SYSTEMS NOMINAL
              </div>
              <div className="ul-protocol">CSV INGEST // COLUMN SCAN</div>
            </div>
          </motion.div>
        ) : (
          /* ─── UPLOAD FORM STATE ─────────────────────── */
          <motion.div
            key="form"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="uploader-header">
              <h3>Upload Dataset</h3>
              <p>
                Supported formats: CSV and JSON. Your file will be used for EDA
                and visual chart generation.
              </p>
            </div>

            <form onSubmit={handleUpload} className="upload-form-redesigned">
              {/* SR-accessible hidden file input */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.json"
                onChange={handleFileChange}
                className="upload-input-hidden"
                aria-label="Select dataset file"
              />

              {/* Floating selection box */}
              <motion.div
                role="button"
                tabIndex={0}
                aria-label="Click to choose a dataset file"
                className={`upload-dropzone${file ? ' upload-dropzone--has-file' : ''}`}
                onClick={triggerFileSelect}
                onKeyDown={(e) => e.key === 'Enter' && triggerFileSelect()}
                animate={{
                  y: [0, -6, 0],
                  boxShadow: [
                    '0 8px 32px rgba(0,0,0,0.2)',
                    '0 16px 48px rgba(0,0,0,0.3)',
                    '0 8px 32px rgba(0,0,0,0.2)',
                  ],
                }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                whileHover={{ scale: 1.015 }}
                whileTap={{ scale: 0.99 }}
              >
                <AnimatePresence mode="wait">
                  {file ? (
                    <motion.div
                      key="has-file"
                      className="upload-dropzone-content"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="upload-file-icon upload-file-icon--active">
                        <FileSpreadsheet size={28} />
                      </div>
                      <div className="upload-file-details">
                        <span className="upload-file-name">{file.name}</span>
                        <span className="upload-file-meta">
                          {formatFileSize(file.size)}&nbsp;&middot;&nbsp;
                          {file.name.toLowerCase().endsWith('.csv') ? 'CSV' : 'JSON'}
                        </span>
                      </div>
                      <span className="upload-file-change">Change file</span>
                    </motion.div>
                  ) : (
                    <motion.div
                      key="empty"
                      className="upload-dropzone-content"
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="upload-file-icon">
                        <Upload size={28} />
                      </div>
                      <div className="upload-file-details">
                        <span className="upload-file-name">Select your dataset</span>
                        <span className="upload-file-meta">
                          Click to browse CSV or JSON files
                        </span>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>

              {/* Submit button */}
              <motion.button
                type="submit"
                className="btn btn-primary upload-submit-btn"
                disabled={!file || loading}
                whileHover={file ? { scale: 1.02 } : {}}
                whileTap={file ? { scale: 0.98 } : {}}
              >
                <Upload size={16} />
                Upload Dataset
              </motion.button>
            </form>

            {currentFile && (
              <motion.div
                className="success-banner"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <CheckCircle size={14} />
                Current dataset: {currentFile}
              </motion.div>
            )}
            {error && (
              <motion.div
                className="error-banner"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {error}
              </motion.div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
