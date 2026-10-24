import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirect to login on 401 (expired/invalid token)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/auth/')) {
        window.location.href = '/auth/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    api.post('/api/auth/register', data),
  
  login: (username: string, password: string) =>
    api.post('/api/auth/login', new URLSearchParams({ username, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  
  getCurrentUser: () => api.get('/api/auth/me'),
}

// Interview API
export const interviewAPI = {
  create: (data: { title: string; domain: string; difficulty: string; resume_id?: number; eval_mode?: string }) =>
    api.post('/api/interview/create', data),
  
  list: () => api.get('/api/interview/list'),
  
  generateQuestion: (data: { interview_id: number; domain: string; difficulty: string }) =>
    api.post('/api/interview/question/generate', data),
  
  submitAnswer: (data: { question_id: number; answer: string }) =>
    api.post('/api/interview/answer/submit', data),
  
  endInterview: (interviewId: number) =>
    api.post(`/api/interview/end/${interviewId}`),
  
  getHistory: (interviewId: number) =>
    api.get(`/api/interview/history/${interviewId}`),
  
  deleteInterview: (interviewId: number) =>
    api.delete(`/api/interview/delete/${interviewId}`),

  getAntiCheatStatus: () => api.get('/api/interview/anticheat/status'),
  reportViolation: (data: { interview_id: number; violation_type: string; details: string }) =>
    api.post('/api/interview/anticheat/report', data),
  
  uploadResume: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/interview/resume/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  listResumes: () => api.get('/api/interview/resume/list'),
  
  getResume: (resumeId: number) => api.get(`/api/interview/resume/${resumeId}`),
  
  getResumeDomains: (resumeId: number) => api.get(`/api/interview/resume/${resumeId}/domains`),
  
  deleteResume: (resumeId: number) => api.delete(`/api/interview/resume/${resumeId}`),

  createManualProfile: (data: { skills: string[]; experience_years: number; role: string }) =>
    api.post('/api/interview/resume/manual', data),
}

// Admin API
export const adminAPI = {
  uploadDocuments: (files: File[], domain: string) => {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    return api.post(`/api/admin/upload/documents?domain=${domain}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  getStats: () => api.get('/api/admin/documents/stats'),
  
  getDomains: () => api.get('/api/admin/questions/domains'),
  
  getQuestions: (domain: string) => api.get(`/api/admin/questions/${domain}`),
  
  addQuestion: (domain: string, data: { question: string; answer: string; file?: string }) =>
    api.post(`/api/admin/questions/${domain}/add`, data),
  
  updateQuestion: (domain: string, questionId: string, data: { question: string; answer: string }) =>
    api.put(`/api/admin/questions/${domain}/${questionId}`, data),
  
  deleteQuestion: (domain: string, questionId: string) =>
    api.delete(`/api/admin/questions/${domain}/${questionId}`),
  
  getUsers: () => api.get('/api/admin/users/list'),

  toggleUserActive: (userId: number) =>
    api.patch(`/api/admin/users/${userId}/toggle-active`),

  getUserInterviews: (userId: number) =>
    api.get(`/api/admin/users/${userId}/interviews`),

  getInterviewStats: () => api.get('/api/admin/interviews/stats'),

  getAntiCheatSettings: () => api.get('/api/admin/anticheat/settings'),
  updateAntiCheatSettings: (enabled: boolean) =>
    api.post('/api/admin/anticheat/settings', { anticheat_enabled: enabled }),
  getAntiCheatViolations: () => api.get('/api/admin/anticheat/violations'),
  getUserViolations: (userId: number) => api.get(`/api/admin/anticheat/violations/${userId}`),
}

// Analytics API
export const analyticsAPI = {
  getPerformance: () => api.get('/api/analytics/performance'),
  getSkills: () => api.get('/api/analytics/skills'),
}

// RAG API
export const ragAPI = {
  retrieve: (data: { query: string; top_k?: number; use_hybrid?: boolean }) =>
    api.post('/api/rag/retrieve', data),
  
  generate: (data: { query: string; top_k?: number }) =>
    api.post('/api/rag/generate', data),
  
  health: () => api.get('/api/rag/health'),
}

export default api
