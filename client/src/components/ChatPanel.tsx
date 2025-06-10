'use client';

import { useState, useEffect, useRef } from 'react';
import { useWebSocket } from './WebSocketProvider';
import { apiClient } from '@/lib/api';
import { ChatMessage } from '@/types';
import { SendIcon, MessageCircleIcon, UsersIcon } from 'lucide-react';
import toast from 'react-hot-toast';

interface Conversation {
  id: string;
  name: string;
  type: 'general' | 'route' | 'emergency';
  participants: number;
}

// Mock conversations for demo
const mockConversations: Conversation[] = [
  { id: 'conv_general', name: 'General Chat', type: 'general', participants: 45 },
  { id: 'conv_route_1', name: 'Route 1 - Arat Kilo', type: 'route', participants: 12 },
  { id: 'conv_route_2', name: 'Route 2 - Bole', type: 'route', participants: 8 },
  { id: 'conv_emergency', name: 'Emergency Channel', type: 'emergency', participants: 3 },
];

export default function ChatPanel() {
  const [selectedConversation, setSelectedConversation] = useState<string>('conv_general');
  const [message, setMessage] = useState('');
  const [isJoined, setIsJoined] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { wsClient, chatMessages } = useWebSocket();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Join selected conversation
  useEffect(() => {
    if (!wsClient || !selectedConversation) return;

    // Leave previous conversations
    isJoined.forEach(convId => {
      if (convId !== selectedConversation) {
        wsClient.leaveRoom(`conversation:${convId}`);
      }
    });

    // Join new conversation
    if (!isJoined.has(selectedConversation)) {
      wsClient.joinRoom(`conversation:${selectedConversation}`);
      setIsJoined(prev => new Set([...prev, selectedConversation]));
    }
  }, [selectedConversation, wsClient, isJoined]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || !selectedConversation) return;

    try {
      await apiClient.sendMessage(selectedConversation, message.trim());
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Failed to send message');
    }
  };

  const getConversationTypeColor = (type: string) => {
    switch (type) {
      case 'emergency':
        return 'text-red-600 bg-red-100';
      case 'route':
        return 'text-blue-600 bg-blue-100';
      default:
        return 'text-green-600 bg-green-100';
    }
  };

  const currentMessages = chatMessages.get(selectedConversation) || [];
  const selectedConv = mockConversations.find(c => c.id === selectedConversation);

  return (
    <div className="h-full flex">
      {/* Conversations List */}
      <div className="w-80 border-r bg-white">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">Conversations</h2>
          <p className="text-sm text-gray-500">Real-time chat channels</p>
        </div>
        
        <div className="overflow-y-auto">
          {mockConversations.map(conv => (
            <div
              key={conv.id}
              onClick={() => setSelectedConversation(conv.id)}
              className={`p-4 border-b cursor-pointer hover:bg-gray-50 ${
                selectedConversation === conv.id ? 'bg-primary-50 border-primary-200' : ''
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <MessageCircleIcon className="w-5 h-5 text-gray-600" />
                  <div>
                    <h3 className="font-medium text-sm">{conv.name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConversationTypeColor(conv.type)}`}>
                        {conv.type}
                      </span>
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <UsersIcon className="w-3 h-3" />
                        <span>{conv.participants}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {isJoined.has(conv.id) && (
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-gray-50">
        {selectedConv ? (
          <>
            {/* Chat Header */}
            <div className="p-4 bg-white border-b">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{selectedConv.name}</h3>
                  <p className="text-sm text-gray-500">
                    {selectedConv.participants} participants • {isJoined.has(selectedConv.id) ? 'Connected' : 'Disconnected'}
                  </p>
                </div>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${getConversationTypeColor(selectedConv.type)}`}>
                  {selectedConv.type}
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {currentMessages.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <MessageCircleIcon className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No messages yet. Start the conversation!</p>
                </div>
              ) : (
                currentMessages.map((msg, index) => (
                  <div key={index} className="flex gap-3">
                    <div className="w-8 h-8 bg-primary-500 rounded-full flex items-center justify-center text-white text-sm font-medium">
                      {msg.message.sender_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm">{msg.message.sender_name}</span>
                        <span className="text-xs text-gray-500">
                          {new Date(msg.message.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="bg-white p-3 rounded-lg shadow-sm">
                        <p className="text-sm">{msg.message.content}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <div className="p-4 bg-white border-t">
              <form onSubmit={handleSendMessage} className="flex gap-2">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={`Message ${selectedConv.name}...`}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={!isJoined.has(selectedConv.id)}
                />
                <button
                  type="submit"
                  disabled={!message.trim() || !isJoined.has(selectedConv.id)}
                  className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <SendIcon className="w-4 h-4" />
                  Send
                </button>
              </form>
              
              {!isJoined.has(selectedConv.id) && (
                <p className="text-xs text-gray-500 mt-2">
                  Connecting to conversation...
                </p>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <MessageCircleIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select a conversation to start chatting</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
