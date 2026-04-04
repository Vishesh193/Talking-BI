import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({ baseURL: `${BASE}/api/v1` })

export const apiService = {
  getConnectors: () => api.get('/connectors').then(r => r.data),
  getKPIs: () => api.get('/kpis').then(r => r.data),
  getDashboards: () => api.get('/dashboards').then(r => r.data),
  getQueryLog: () => api.get('/query-log').then(r => r.data),
  seedDemoKPIs: () => api.post('/seed-demo-kpis').then(r => r.data),

  // Upload file (basic — returns UploadedFileInfo)
  uploadFile: (file: File, sessionId: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('session_id', sessionId)
    return api.post('/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  // Upload + analyze (returns FileAnalysisResult with suggestions + questions)
  analyzeFile: (file: File, sessionId: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('session_id', sessionId)
    return api.post('/upload/analyze', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data)
  },

  generateAdvancedDashboard: (data: { session_id: string; answers: any }) =>
    api.post('/upload/advanced-dashboard', data).then(r => r.data),

  createDashboard: (data: { name: string; layout: any[]; kpis: any[] }) =>
    api.post('/dashboards', data).then(r => r.data),

  updateDashboard: (id: string, data: any) =>
    api.put(`/dashboards/${id}`, data).then(r => r.data),
}
