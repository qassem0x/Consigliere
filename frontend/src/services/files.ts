import { api } from '../utils/api';
import { Dossier, FileUploadResult, AnalysisResult } from '../types';

export const fileService = {
  uploadFileOnly: async (file: File): Promise<FileUploadResult> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<FileUploadResult>('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  createDossier: async (fileId: string): Promise<AnalysisResult> => {
    const res = await api.post<AnalysisResult>(`/files/${fileId}/analyze`);
    return res.data;
  },

  loadDossier: async (chatId: string): Promise<Dossier> => {
    const res = await api.get<Dossier>(`/chats/${chatId}/dossier`);
    return res.data;
  },

  connectDatabase: async (dbData: any) => {
    const res = await api.post('/connections', dbData);
    return res.data;
  }
};