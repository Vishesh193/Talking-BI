import { create } from 'zustand'
import axios from 'axios'

export interface Metric {
  key: string
  description: string
  unit: string | null
  direction: string
  aliases: string[]
}

interface MetricState {
  metrics: Metric[]
  loading: boolean
  error: string | null
  fetchMetrics: () => Promise<void>
}

export const useMetricStore = create<MetricState>((set) => ({
  metrics: [],
  loading: false,
  error: null,
  fetchMetrics: async () => {
    set({ loading: true, error: null })
    try {
      const response = await axios.get('/api/metrics')
      set({ metrics: response.data, loading: false })
    } catch (err: any) {
      set({ error: err.message, loading: false })
      // Fallback metrics if API fails
      set({
        metrics: [
          { key: 'mrr', description: 'Monthly Recurring Revenue', unit: '$', direction: 'up_is_good', aliases: [] },
          { key: 'revenue', description: 'Total Revenue', unit: '$', direction: 'up_is_good', aliases: [] },
          { key: 'churn', description: 'Churn Rate (%)', unit: '%', direction: 'down_is_good', aliases: [] },
          { key: 'cac', description: 'Customer Acquisition Cost', unit: '$', direction: 'down_is_good', aliases: [] },
        ]
      })
    }
  },
}))
