import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import { AuthProvider } from './context/AuthContext';
import { DiagramProvider } from './context/DiagramContext';
import { ToastProvider } from './components/common/ToastProvider';
import { ToastStack } from './components/common/Toast';
import { App } from './App';
import './styles/theme.css';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <DiagramProvider>
            <App />
            <ToastStack />
          </DiagramProvider>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
