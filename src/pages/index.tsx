import { useState } from 'react'

interface CompressionResult {
  original: {
    text: string
    bitsPerToken: number
    totalBits: number
  }
  simplified: {
    text: string
    bitsPerToken: number
    totalBits: number
  }
  id: string
}

export default function Home() {
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<CompressionResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const compress = async () => {
    if (!input.trim()) {
      setError('Please enter some text')
      return
    }

    setIsLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await fetch('/api/compress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input: input.trim() })
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || 'Failed to process text')
      }

      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">
          Hi Owen mwah mwah
        </h1>
        
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <label htmlFor="input" className="block text-sm font-medium text-gray-700 mb-2">
            Enter your text:
          </label>
          <textarea
            id="input"
            className="w-full p-3 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={6}
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Enter a paragraph or text to analyze its entropy..."
            disabled={isLoading}
          />
          
          <button
            onClick={compress}
            disabled={isLoading || !input.trim()}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Processing...' : 'Analyze Entropy'}
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {result && (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Original Text */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-800">Original Text</h2>
              <div className="bg-gray-50 p-4 rounded-md mb-4">
                <p className="text-gray-700 whitespace-pre-wrap">{result.original.text}</p>
              </div>
              <div className="space-y-2">
                <p><span className="font-medium">Bits per token:</span> {result.original.bitsPerToken.toFixed(2)}</p>
                <p><span className="font-medium">Total bits:</span> {result.original.totalBits.toFixed(2)}</p>
              </div>
            </div>

            {/* Simplified Text */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-800">Simplified Version</h2>
              <div className="bg-gray-50 p-4 rounded-md mb-4">
                <p className="text-gray-700 whitespace-pre-wrap">{result.simplified.text}</p>
              </div>
              <div className="space-y-2">
                <p><span className="font-medium">Bits per token:</span> {result.simplified.bitsPerToken.toFixed(2)}</p>
                <p><span className="font-medium">Total bits:</span> {result.simplified.totalBits.toFixed(2)}</p>
              </div>
            </div>
          </div>
        )}

        {result && (
          <div className="mt-6 bg-blue-50 border border-blue-200 rounded-md p-4">
            <h3 className="text-lg font-semibold mb-2 text-blue-800">Analysis Summary</h3>
            <div className="grid md:grid-cols-3 gap-4 text-sm">
              <div>
                <p className="font-medium">Compression Ratio:</p>
                <p className="text-blue-600">
                  {((result.simplified.totalBits / result.original.totalBits) * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="font-medium">Token Reduction:</p>
                <p className="text-blue-600">
                  {((result.simplified.text.split(' ').length / result.original.text.split(' ').length) * 100).toFixed(1)}%
                </p>
              </div>
              <div>
                <p className="font-medium">Efficiency Gain:</p>
                <p className="text-blue-600">
                  {((result.original.bitsPerToken - result.simplified.bitsPerToken) / result.original.bitsPerToken * 100).toFixed(1)}%
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
