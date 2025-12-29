import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Factor Evaluation Logic', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Factor metrics display logic', () => {
    it('should display metrics when IC is not null', () => {
      const factor = {
        id: 1,
        name: 'momentum_5d',
        ic: 0.0374,
        icir: 0.0824,
        sharpe_ratio: -0.3464,
        annual_return: -0.2486
      }

      // Check condition: ic !== null && ic !== undefined
      const shouldDisplay = factor.ic !== null && factor.ic !== undefined
      expect(shouldDisplay).toBe(true)

      // Format metrics
      const formattedIC = factor.ic.toFixed(3)
      const formattedICIR = factor.icir?.toFixed(2)
      const formattedSharpe = factor.sharpe_ratio?.toFixed(2)
      const formattedReturn = (factor.annual_return * 100).toFixed(2)

      expect(formattedIC).toBe('0.037')
      expect(formattedICIR).toBe('0.08')
      expect(formattedSharpe).toBe('-0.35')
      expect(formattedReturn).toBe('-24.86')
    })

    it('should not display metrics when IC is null', () => {
      const factor = {
        id: 2,
        name: 'new_factor',
        ic: null,
        icir: null,
        sharpe_ratio: null,
        annual_return: null
      }

      const shouldDisplay = factor.ic !== null && factor.ic !== undefined
      expect(shouldDisplay).toBe(false)
    })

    it('should not display metrics when IC is undefined', () => {
      const factor = {
        id: 3,
        name: 'another_factor'
      }

      const shouldDisplay = factor.ic !== null && factor.ic !== undefined
      expect(shouldDisplay).toBe(false)
    })

    it('should handle zero IC value correctly', () => {
      const factor = {
        id: 4,
        name: 'zero_ic_factor',
        ic: 0,
        icir: 0,
        sharpe_ratio: 0,
        annual_return: 0
      }

      // IC = 0 is valid, should display
      const shouldDisplay = factor.ic !== null && factor.ic !== undefined
      expect(shouldDisplay).toBe(true)

      const formattedIC = factor.ic.toFixed(3)
      expect(formattedIC).toBe('0.000')
    })
  })

  describe('Evaluation state management', () => {
    it('should track evaluating factors using Set', () => {
      const evaluatingFactors = new Set<number>()

      // Add factor 1 to evaluation
      evaluatingFactors.add(1)
      expect(evaluatingFactors.has(1)).toBe(true)
      expect(evaluatingFactors.size).toBe(1)

      // Add factor 2
      evaluatingFactors.add(2)
      expect(evaluatingFactors.has(2)).toBe(true)
      expect(evaluatingFactors.size).toBe(2)

      // Remove factor 1 when done
      evaluatingFactors.delete(1)
      expect(evaluatingFactors.has(1)).toBe(false)
      expect(evaluatingFactors.size).toBe(1)
    })

    it('should prevent duplicate evaluation of same factor', () => {
      const evaluatingFactors = new Set<number>()
      const factorId = 1

      // First evaluation
      if (!evaluatingFactors.has(factorId)) {
        evaluatingFactors.add(factorId)
      }
      expect(evaluatingFactors.has(factorId)).toBe(true)

      // Try to evaluate again (should be blocked)
      const canEvaluate = !evaluatingFactors.has(factorId)
      expect(canEvaluate).toBe(false)
    })
  })

  describe('IC decay analysis', () => {
    it('should classify factor as short-term', () => {
      const icValues = [0.08, 0.05, 0.02, 0.01, 0.005]
      const firstIC = icValues[0]
      const lastIC = icValues[icValues.length - 1]
      const decayRate = (firstIC - lastIC) / firstIC

      let factorType = 'N/A'
      if (decayRate > 0.5) {
        factorType = '短期因子'
      } else if (decayRate > 0.2) {
        factorType = '中期因子'
      } else {
        factorType = '長期因子'
      }

      // Decay rate = (0.08 - 0.005) / 0.08 = 0.9375 > 0.5
      expect(decayRate).toBeGreaterThan(0.5)
      expect(factorType).toBe('短期因子')
    })

    it('should classify factor as medium-term', () => {
      const icValues = [0.05, 0.04, 0.035, 0.032, 0.03]
      const firstIC = icValues[0]
      const lastIC = icValues[icValues.length - 1]
      const decayRate = (firstIC - lastIC) / firstIC

      let factorType = 'N/A'
      if (decayRate > 0.5) {
        factorType = '短期因子'
      } else if (decayRate > 0.2) {
        factorType = '中期因子'
      } else {
        factorType = '長期因子'
      }

      // Decay rate = (0.05 - 0.03) / 0.05 = 0.4 > 0.2
      expect(decayRate).toBeGreaterThan(0.2)
      expect(decayRate).toBeLessThanOrEqual(0.5)
      expect(factorType).toBe('中期因子')
    })

    it('should classify factor as long-term', () => {
      const icValues = [0.05, 0.048, 0.046, 0.045, 0.044]
      const firstIC = icValues[0]
      const lastIC = icValues[icValues.length - 1]
      const decayRate = (firstIC - lastIC) / firstIC

      let factorType = 'N/A'
      if (decayRate > 0.5) {
        factorType = '短期因子'
      } else if (decayRate > 0.2) {
        factorType = '中期因子'
      } else {
        factorType = '長期因子'
      }

      // Decay rate = (0.05 - 0.044) / 0.05 = 0.12 < 0.2
      expect(decayRate).toBeLessThanOrEqual(0.2)
      expect(factorType).toBe('長期因子')
    })

    it('should find best holding period', () => {
      const icDecayData = {
        lags: [1, 5, 10, 15, 20],
        ic_values: [0.04, 0.065, 0.05, 0.03, 0.01],
        rank_ic_values: [0.05, 0.07, 0.055, 0.035, 0.015]
      }

      // Find max IC
      const maxIC = Math.max(...icDecayData.ic_values)
      const maxIndex = icDecayData.ic_values.indexOf(maxIC)
      const bestHoldingPeriod = icDecayData.lags[maxIndex]

      expect(maxIC).toBe(0.065)
      expect(bestHoldingPeriod).toBe(5) // 5 days is best
    })
  })

  describe('API response handling', () => {
    it('should parse successful evaluation response', () => {
      const mockResponse = {
        ic: 0.0374,
        icir: 0.0824,
        rank_ic: 0.0412,
        rank_icir: 0.0891,
        sharpe_ratio: -0.3464,
        annual_return: -0.2486
      }

      // Format alert message
      const message = `評估完成！\n\nIC: ${mockResponse.ic.toFixed(4)}\nICIR: ${mockResponse.icir.toFixed(4)}\nSharpe Ratio: ${mockResponse.sharpe_ratio.toFixed(2)}\n年化報酬: ${(mockResponse.annual_return * 100).toFixed(2)}%`

      expect(message).toContain('評估完成')
      expect(message).toContain('IC: 0.0374')
      expect(message).toContain('ICIR: 0.0824')
      expect(message).toContain('Sharpe Ratio: -0.35')
      expect(message).toContain('年化報酬: -24.86%')
    })

    it('should handle evaluation errors', () => {
      const mockError = {
        data: {
          detail: 'Qlib data not found for factor'
        }
      }

      const errorMessage = '評估失敗：' + (mockError.data?.detail || '未知錯誤')

      expect(errorMessage).toBe('評估失敗：Qlib data not found for factor')
    })

    it('should handle errors without detail', () => {
      const mockError = {
        message: 'Network error'
      }

      const errorMessage = '評估失敗：' + (mockError.message || '未知錯誤')

      expect(errorMessage).toBe('評估失敗：Network error')
    })
  })
})
