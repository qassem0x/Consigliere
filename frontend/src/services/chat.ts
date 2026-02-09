import { api, fetchStream } from '../utils/api';

export const chatService = {
  loadUserChats: async () => {
    const response = await api.get('/chats');
    return response.data;
  },
  loadChatHistory: async (chatId: string) => {
    const response = await api.get(`/messages/${chatId}`);
    return response.data;
  },
  sendMessage: async (chatId: string, content: string) => {
    const response = await api.post(`/messages/${chatId}`, { content });
    return response.data;
  },
  sendMessageStream: async (chatId: string, content: string) => {
    return await fetchStream(`/messages/${chatId}`, { content });
  },
  async deleteChat(chatId: string) {
    const res = await api.delete(`/chats/${chatId}`);
    return true;
  }
};