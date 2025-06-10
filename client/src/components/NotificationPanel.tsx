'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from './WebSocketProvider';
import { apiClient } from '@/lib/api';
import { NotificationMessage } from '@/types';
import { 
  BellIcon, 
  AlertTriangleIcon, 
  InfoIcon, 
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  FilterIcon
} from 'lucide-react';
import toast from 'react-hot-toast';

type NotificationFilter = 'all' | 'trip_update' | 'route_alert' | 'maintenance' | 'emergency';

export default function NotificationPanel() {
  const [filter, setFilter] = useState<NotificationFilter>('all');
  const [historicalNotifications, setHistoricalNotifications] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const { notifications } = useWebSocket();

  // Load historical notifications
  useEffect(() => {
    loadHistoricalNotifications();
  }, []);

  const loadHistoricalNotifications = async () => {
    try {
      setIsLoading(true);
      const data = await apiClient.getNotifications();
      setHistoricalNotifications(data);
    } catch (error) {
      console.error('Error loading notifications:', error);
      toast.error('Failed to load notifications');
    } finally {
      setIsLoading(false);
    }
  };

  // Combine real-time and historical notifications
  const allNotifications = [
    ...notifications.map(n => ({ ...n.notification, isRealtime: true })),
    ...historicalNotifications.map(n => ({ ...n, isRealtime: false }))
  ].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  // Filter notifications
  const filteredNotifications = filter === 'all' 
    ? allNotifications 
    : allNotifications.filter(n => n.type === filter);

  const getNotificationIcon = (type: string, priority: string) => {
    if (priority === 'critical' || type === 'emergency') {
      return <XCircleIcon className="w-5 h-5 text-red-500" />;
    }
    
    switch (type) {
      case 'trip_update':
        return <ClockIcon className="w-5 h-5 text-blue-500" />;
      case 'route_alert':
        return <AlertTriangleIcon className="w-5 h-5 text-yellow-500" />;
      case 'maintenance':
        return <InfoIcon className="w-5 h-5 text-gray-500" />;
      default:
        return <BellIcon className="w-5 h-5 text-gray-500" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'border-l-red-500 bg-red-50';
      case 'high':
        return 'border-l-orange-500 bg-orange-50';
      case 'medium':
        return 'border-l-yellow-500 bg-yellow-50';
      case 'low':
        return 'border-l-green-500 bg-green-50';
      default:
        return 'border-l-gray-500 bg-gray-50';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  };

  const markAsRead = async (notificationId: string) => {
    try {
      await apiClient.markNotificationRead(notificationId);
      toast.success('Notification marked as read');
    } catch (error) {
      console.error('Error marking notification as read:', error);
      toast.error('Failed to mark as read');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b bg-white">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Notifications</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">
              {filteredNotifications.length} notifications
            </span>
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          <FilterIcon className="w-4 h-4 text-gray-500" />
          {(['all', 'trip_update', 'route_alert', 'maintenance', 'emergency'] as NotificationFilter[]).map(filterType => (
            <button
              key={filterType}
              onClick={() => setFilter(filterType)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                filter === filterType
                  ? 'bg-primary-100 text-primary-800'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {filterType.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Notifications List */}
      <div className="flex-1 overflow-y-auto">
        {filteredNotifications.length === 0 ? (
          <div className="flex items-center justify-center h-64 text-gray-500">
            <div className="text-center">
              <BellIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No notifications found</p>
              <p className="text-sm mt-1">
                {filter === 'all' ? 'All caught up!' : `No ${filter.replace('_', ' ')} notifications`}
              </p>
            </div>
          </div>
        ) : (
          <div className="p-4 space-y-3">
            {filteredNotifications.map((notification, index) => (
              <div
                key={`${notification.id}-${index}`}
                className={`p-4 rounded-lg border-l-4 ${getPriorityColor(notification.priority)} hover:shadow-md transition-shadow`}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-1">
                    {getNotificationIcon(notification.type, notification.priority)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-gray-900 mb-1">
                          {notification.title}
                        </h3>
                        <p className="text-sm text-gray-700 mb-2">
                          {notification.message}
                        </p>
                        
                        {/* Additional data */}
                        {notification.data && (
                          <div className="text-xs text-gray-600 bg-white p-2 rounded border">
                            {Object.entries(notification.data).map(([key, value]) => (
                              <div key={key} className="flex justify-between">
                                <span className="font-medium">{key}:</span>
                                <span>{String(value)}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-2 ml-4">
                        {notification.isRealtime && (
                          <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded-full font-medium">
                            Live
                          </span>
                        )}
                        <span className={`px-2 py-1 text-xs rounded-full font-medium ${
                          notification.priority === 'critical' ? 'bg-red-100 text-red-800' :
                          notification.priority === 'high' ? 'bg-orange-100 text-orange-800' :
                          notification.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {notification.priority}
                        </span>
                      </div>
                    </div>
                    
                    <div className="flex items-center justify-between mt-3">
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>{formatTimestamp(notification.timestamp)}</span>
                        <span className="capitalize">{notification.type.replace('_', ' ')}</span>
                      </div>
                      
                      {!notification.isRealtime && (
                        <button
                          onClick={() => markAsRead(notification.id)}
                          className="text-xs text-primary-600 hover:text-primary-800 font-medium"
                        >
                          Mark as read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
