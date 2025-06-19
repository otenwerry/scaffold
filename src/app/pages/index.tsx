import { useState } from 'react'
import { supabase } from '../lib/supabase'

export default async function Home() {
  // … auth logic from above …
  const { data: { user } } = await supabase.auth.getUser()

  const [input, setInput] = useState('')
  const [output, setOutput] = useState('')
  const [bits, setBits] = useState<string>('')

  const compress = async () => {
    const res = await fetch('/api/compress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input, userId: user?.id ?? '' })
    })
    const { compressed, bitsPerWord } = await res.json()
    setOutput(compressed)
    setBits(bitsPerWord)
  }

  return (
    <div className="max-w-xl mx-auto p-4 space-y-4">
      <textarea
        className="w-full p-2 border rounded"
        rows={5}
        value={input}
        onChange={e => setInput(e.target.value)}
      />
      <button
        className="px-4 py-2 bg-blue-600 text-white rounded"
        onClick={compress}
      >
        Compress
      </button>
      {output && (
        <div className="space-y-2">
          <p><strong>Output:</strong> {output}</p>
          <p><strong>Bits/word:</strong> {bits}</p>
        </div>
      )}
    </div>
  )
}
