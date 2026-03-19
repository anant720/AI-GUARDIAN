import axios from 'axios';

const axiosClient = axios.create({
  // The Vite proxy handles /api -> http://localhost:8000
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercept requests to inject the JWT token
axiosClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('ai_guardian_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercept responses for global error handling
axiosClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    try {
      const { response } = error;
      if (response && response.status === 401) {
        localStorage.removeItem('ai_guardian_token');
        // Handle forced logout / redirect if token is expired.
      }
    } catch (e) {
        console.error(e);
    }
    throw error;
  }
);

export default axiosClient;
