import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload,
  BarChart3,
  Sparkles,
  Settings,
  Brain,
  ChevronRight,
  CheckCircle2,
  Lock,
} from 'lucide-react';

type Tab = 'upload' | 'eda' | 'visualization' | 'preprocess' | 'ml';

type SidebarProps = {
  active: Tab;
  onChange: (next: Tab) => void;
  hasFile: boolean;
};

const STEPS = [
  { 
    id: 'upload' as Tab, 
    num: 1, 
    label: 'Upload Dataset',
    icon: Upload,
    description: 'Import CSV or JSON files'
  },
  { 
    id: 'eda' as Tab, 
    num: 2, 
    label: 'EDA Overview',
    icon: BarChart3,
    description: 'Exploratory Data Analysis'
  },
  { 
    id: 'visualization' as Tab, 
    num: 3, 
    label: 'Visualization',
    icon: Sparkles,
    description: 'Create interactive charts'
  },
  { 
    id: 'preprocess' as Tab, 
    num: 4, 
    label: 'Preprocessing',
    icon: Settings,
    description: 'Clean and transform data'
  },
  { 
    id: 'ml' as Tab, 
    num: 5, 
    label: 'ML Builder',
    icon: Brain,
    description: 'Build machine learning models'
  },
];

export default function Sidebar({ active, onChange, hasFile }: SidebarProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const hoverTimeoutRef = useRef<number | null>(null);
  const collapseTimeoutRef = useRef<number | null>(null);

  // Auto-expand on hover with delay
  const handleMouseEnter = () => {
    if (collapseTimeoutRef.current) {
      clearTimeout(collapseTimeoutRef.current);
      collapseTimeoutRef.current = null;
    }
    
    hoverTimeoutRef.current = setTimeout(() => {
      setIsExpanded(true);
      setIsHovering(true);
    }, 150);
  };

  // Auto-collapse on mouse leave with delay
  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    
    setIsHovering(false);
    collapseTimeoutRef.current = setTimeout(() => {
      setIsExpanded(false);
    }, 300);
  };

  // Collapse when clicking outside or interacting with main content
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (sidebarRef.current && !sidebarRef.current.contains(e.target as Node)) {
        setIsExpanded(false);
        setIsHovering(false);
      }
    };

    const handleScroll = () => {
      if (!isHovering) {
        setIsExpanded(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('scroll', handleScroll, true);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('scroll', handleScroll, true);
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      if (collapseTimeoutRef.current) clearTimeout(collapseTimeoutRef.current);
    };
  }, [isHovering]);

  return (
    <motion.aside
      ref={sidebarRef}
      className={`modern-sidebar ${isExpanded ? 'modern-sidebar--expanded' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      initial={false}
      animate={{ width: isExpanded ? 280 : 80 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Brand Section */}
      <div className="modern-sidebar-brand">
        <motion.div 
          className="sidebar-logo"
          animate={{ scale: isExpanded ? 1 : 0.9 }}
          transition={{ duration: 0.2 }}
        >
          <BarChart3 size={isExpanded ? 28 : 24} strokeWidth={2.5} />
        </motion.div>
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.2 }}
              className="sidebar-brand-text"
            >
              <h2>DataLens</h2>
              <p>Workspace</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation Items */}
      <nav className="modern-sidebar-nav">
        {STEPS.map((step) => {
          const isActive = active === step.id;
          const isDisabled = step.id !== 'upload' && !hasFile;
          const isCompleted = hasFile && STEPS.findIndex(s => s.id === step.id) < STEPS.findIndex(s => s.id === active);
          const Icon = step.icon;

          return (
            <motion.button
              key={step.id}
              className={`modern-nav-item ${isActive ? 'modern-nav-item--active' : ''} ${isDisabled ? 'modern-nav-item--disabled' : ''} ${isCompleted ? 'modern-nav-item--completed' : ''}`}
              onClick={() => !isDisabled && onChange(step.id)}
              disabled={isDisabled}
              whileHover={!isDisabled ? { x: 4 } : {}}
              whileTap={!isDisabled ? { scale: 0.98 } : {}}
              transition={{ duration: 0.2 }}
            >
              {/* Icon Section */}
              <div className="modern-nav-icon-wrapper">
                <div className={`modern-nav-icon ${isActive ? 'modern-nav-icon--active' : ''}`}>
                  {isCompleted ? (
                    <CheckCircle2 size={20} strokeWidth={2.5} />
                  ) : isDisabled ? (
                    <Lock size={20} strokeWidth={2} />
                  ) : (
                    <Icon size={20} strokeWidth={2} />
                  )}
                </div>
                {!isExpanded && isActive && (
                  <motion.div
                    className="nav-active-indicator"
                    layoutId="activeIndicator"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
              </div>

              {/* Text Section */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    className="modern-nav-text"
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    transition={{ duration: 0.2, delay: 0.05 }}
                  >
                    <div className="modern-nav-label-wrapper">
                      <span className="modern-nav-number">{step.num}</span>
                      <span className="modern-nav-label">{step.label}</span>
                    </div>
                    <span className="modern-nav-description">{step.description}</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Arrow indicator for expanded state */}
              {isExpanded && isActive && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className="modern-nav-arrow"
                >
                  <ChevronRight size={16} strokeWidth={3} />
                </motion.div>
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* Expand Hint */}
      {!isExpanded && (
        <motion.div
          className="sidebar-expand-hint"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          whileHover={{ opacity: 1 }}
        >
          <ChevronRight size={14} />
        </motion.div>
      )}
    </motion.aside>
  );
}
