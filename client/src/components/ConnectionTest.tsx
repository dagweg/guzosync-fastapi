'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { useWebSocket } from './WebSocketProvider';
import { CheckCircleIcon, XCircleIcon, AlertCircleIcon, RefreshCwIcon } from 'lucide-react';

export default function ConnectionTest() {
  const [apiStatus, setApiStatus] = useState<'checking' | 'connected' | 'error'>('checking');
  const [apiError, setApiError] = useState<string>('');
  const { isConnected: wsConnected } = useWebSocket();

  const testApiConnection = async () => {
    setApiStatus('checking');
    setApiError('');
    
    try {
      // Test a simple endpoint that doesn't require auth
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/config/languages`);
      
      if (response.ok) {
        setApiStatus('connected');
      } else {
        setApiStatus('error');
        setApiError(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error: any) {
      setApiStatus('error');
      setApiError(error.message || 'Connection failed');
    }
  };

  useEffect(() => {
    testApiConnection();
  }, []);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
      case 'error':
        return <XCircleIcon className="w-5 h-5 text-red-500" />;
      default:
        return <RefreshCwIcon className="w-5 h-5 text-gray-500 animate-spin" />;
    }
  };

  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg p-4 border max-w-sm">
      <h3 className="font-semibold text-sm mb-3">FastAPI Connection Status</h3>
      
      <div className="space-y-2">
        {/* API Connection */}
        <div className="flex items-center justify-between">
          <span className="text-sm">REST API:</span>
          <div className="flex items-center gap-2">
            {getStatusIcon(apiStatus)}
            <span className={`text-xs ${
              apiStatus === 'connected' ? 'text-green-600' : 
              apiStatus === 'error' ? 'text-red-600' : 'text-gray-600'
            }`}>
              {apiStatus === 'connected' ? 'Connected' : 
               apiStatus === 'error' ? 'Failed' : 'Checking...'}
            </span>
          </div>
        </div>

        {/* WebSocket Connection */}
        <div className="flex items-center justify-between">
          <span className="text-sm">WebSocket:</span>
          <div className="flex items-center gap-2">
            {wsConnected ? 
              <CheckCircleIcon className="w-5 h-5 text-green-500" /> : 
              <XCircleIcon className="w-5 h-5 text-red-500" />
            }
            <span className={`text-xs ${wsConnected ? 'text-green-600' : 'text-red-600'}`}>
              {wsConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Error Details */}
      {apiError && (
        <div className="mt-3 p-2 bg-red-50 rounded text-xs text-red-700">
          <strong>Error:</strong> {apiError}
        </div>
      )}

      {/* Retry Button */}
      <button
        onClick={testApiConnection}
        className="mt-3 w-full px-3 py-1 bg-primary-600 text-white text-xs rounded hover:bg-primary-700"
      >
        Test Connection
      </button>

      {/* Backend URL Info */}
      <div className="mt-2 text-xs text-gray-500">
        <strong>API URL:</strong> {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}
      </div>
      <div className="text-xs text-gray-500">
        <strong>WS URL:</strong> {process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws'}
      </div>
    </div>
  );
}
