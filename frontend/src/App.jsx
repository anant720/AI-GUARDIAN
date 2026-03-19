import React from 'react';
import { Toaster } from 'react-hot-toast';
import TestingInterface from './pages/TestingInterface';

function App() {
  return (
    <>
      <Toaster 
        position="top-right" 
        toastOptions={{
          style: {
            background: '#0f172a',
            color: '#f8fafc',
            border: '1px solid rgba(51, 65, 85, 0.5)',
            fontSize: '14px',
            borderRadius: '12px',
          }
        }}
      />
      <TestingInterface />
    </>
  );
}

export default App;
