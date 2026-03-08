import axios from 'axios';
import toast from 'react-hot-toast';

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (value: unknown) => void; reject: (reason?: unknown) => void }> = [];

const processQueue = (error: unknown, token: string | null = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            const url = originalRequest.url || '';
            
            if (url.includes('/auth/me') || url.includes('/auth/refresh')) {
                return Promise.reject(error);
            }

            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then(() => {
                    return api(originalRequest);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const res = await api.post('/auth/refresh');
                processQueue(null, res.data.access_token);
                return api(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError, null);
                isRefreshing = false;
                window.location.href = '/login';
                return Promise.reject(refreshError);
            }
        }

        if (error.response?.data?.message) {
            toast.error(error.response.data.message);
        } else if (error.response?.status === 429) {
            const retryAfter = error.response.data?.retry_after;
            toast.error(retryAfter ? `Rate limit exceeded. Please wait ${retryAfter} seconds.` : 'Too many requests. Please wait a moment.');
        } else if (error.response?.status === 500) {
            toast.error('Server error. Please try again later.');
        }

        return Promise.reject(error);
    }
);

export const fetchStream = async (endpoint: string, body: any) => {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(body),
    });

    if (!response.ok) {
        let errorMessage = `Request failed: ${response.status}`;
        
        try {
            const errorData = await response.json();
            if (errorData.message) {
                errorMessage = errorData.message;
            }
            if (errorData.code === 'RATE_LIMIT') {
                errorMessage = errorData.retry_after 
                    ? `Rate limit exceeded. Please wait ${errorData.retry_after} seconds.`
                    : 'Too many requests. Please wait a moment.';
                toast.error(errorMessage, { duration: 5000 });
            } else if (errorData.code === 'TIMEOUT') {
                errorMessage = 'Request timed out. Try a simpler query.';
                toast.error(errorMessage);
            } else {
                toast.error(errorMessage);
            }
        } catch {
            toast.error(errorMessage);
        }
        
        throw new Error(errorMessage);
    }

    return response;
};

export const fetchModel = async (): Promise<string> => {
    const response = await fetch(`${API_BASE_URL}/model`, {
        credentials: 'include',
    });
    if (!response.ok) {
        throw new Error(`Failed to fetch model: ${response.status}`);
    }
    const data = await response.json();
    return data.model;
};