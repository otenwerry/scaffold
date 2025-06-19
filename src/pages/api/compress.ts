// src/pages/api/compress.ts
import type { NextApiRequest, NextApiResponse } from 'next'
import { supabase } from '../../../lib/supabase'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).end()

  const { input, userId } = req.body as { input: string; userId: string }

  // 1) Your real entropy/compression logic here:
  const compressed = input
    .split(' ')
    .filter(w => w.length > 3)
    .join(' ')
  const bitsPerWord = /* your calc */ (Math.random() * 4 + 4).toFixed(2)

  // 2) Save to Supabase
  const { error } = await supabase
    .from('submissions')
    .insert({ user_id: userId, input, output: compressed, bits: bitsPerWord })

  if (error) {
    console.error('Supabase insert error:', error)
    return res.status(500).json({ error: error.message })
  }

  // 3) Return to front-end
  res.status(200).json({ compressed, bitsPerWord })
}
