import { api } from '../utils/api';

export const chatService = {
  loadUserChats: async () => {
    const response = await api.get('/chats');
    return response.data;
  },
  loadChatHistory: async (chatId: string) => {
    const response = await api.get(`/messages/${chatId}`);
    return response.data;
  }
};