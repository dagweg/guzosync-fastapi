'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { GuzoSyncWebSocket } from '@/lib/websocket';
import { BusLocationUpdate, ChatMessage, NotificationMessage } from '@/types';
import toast from 'react-hot-toast';

interface WebSocketContextType {
  wsClient: GuzoSyncWebSocket | null;
  isConnected: boolean;
  busLocations: Map<string, BusLocationUpdate>;
  notifications: NotificationMessage[];
  chatMessages: Map<string, ChatMessage[]>;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const [wsClient, setWsClient] = useState<GuzoSyncWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [busLocations, setBusLocations] = useState<Map<string, BusLocationUpdate>>(new Map());
  const [notifications, setNotifications] = useState<NotificationMessage[]>([]);
  const [chatMessages, setChatMessages] = useState<Map<string, ChatMessage[]>>(new Map());

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const client = new GuzoSyncWebSocket(token);

    // Connection event handlers
    client.onOpen = () => {
      setIsConnected(true);
      toast.success('Connected to real-time server');
    };

    client.onClose = () => {
      setIsConnected(false);
      toast.error('Disconnected from real-time server');
    };

    client.onAuthError = () => {
      toast.error('Authentication failed');
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    };

    client.onMaxReconnectAttemptsReached = () => {
      toast.error('Failed to reconnect to server');
    };

    // Message handlers
    client.on('bus_location_update', (message: BusLocationUpdate) => {
      setBusLocations(prev => {
        const newMap = new Map(prev);
        newMap.set(message.bus_id, message);
        return newMap;
      });
    });

    client.on('chat_message', (message: ChatMessage) => {
      setChatMessages(prev => {
        const newMap = new Map(prev);
        const conversationMessages = newMap.get(message.conversation_id) || [];
        conversationMessages.push(message);
        newMap.set(message.conversation_id, conversationMessages);
        return newMap;
      });

      // Show toast notification for new messages
      toast.success(`New message from ${message.message.sender_name}`);
    });

    client.on('notification', (message: NotificationMessage) => {
      setNotifications(prev => [message, ...prev]);
      
      // Show toast notification
      const { notification } = message;
      switch (notification.priority) {
        case 'high':
        case 'critical':
          toast.error(notification.title);
          break;
        case 'medium':
          toast(notification.title);
          break;
        default:
          toast.success(notification.title);
      }
    });

    client.on('room_joined', (message) => {
      console.log('Joined room:', message.room_id);
    });

    client.on('room_left', (message) => {
      console.log('Left room:', message.room_id);
    });

    client.on('pong', (message) => {
      console.log('Received pong:', message.timestamp);
    });

    setWsClient(client);

    return () => {
      client.disconnect();
      setIsConnected(false);
    };
  }, []);

  const value: WebSocketContextType = {
    wsClient,
    isConnected,
    busLocations,
    notifications,
    chatMessages,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket(): WebSocketContextType {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}

export default WebSocketProvider;
