import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary
      fallbackTitle="MineIntel System Notice"
      fallbackMessage="An unexpected issue occurred while rendering the application. Please refresh or reset to the Overview dashboard."
    >
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);

