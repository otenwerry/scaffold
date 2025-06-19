// src/pages/api/compress.ts
import { NextApiRequest, NextApiResponse } from 'next'
import { supabase } from '../../../lib/supabase'
import { spawn } from 'child_process'

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { input } = req.body

    if (!input || typeof input !== 'string') {
      return res.status(400).json({ error: 'Input text is required' })
    }

    // Process the original text through entropy.py
    const originalResult = await processTextWithEntropy(input)
    
    // Generate a simplified version (for now, just remove some words)
    const simplifiedText = generateSimplifiedText(input)
    const simplifiedResult = await processTextWithEntropy(simplifiedText)

    // Store results in Supabase
    const { data, error } = await supabase
      .from('text_compressions')
      .insert([
        {
          original_text: input,
          original_bits_per_token: originalResult.bitsPerToken,
          original_total_bits: originalResult.totalBits,
          simplified_text: simplifiedText,
          simplified_bits_per_token: simplifiedResult.bitsPerToken,
          simplified_total_bits: simplifiedResult.totalBits,
          created_at: new Date().toISOString()
        }
      ])
      .select()

    if (error) {
      console.error('Supabase error:', error)
      return res.status(500).json({ error: 'Failed to store results' })
    }

    res.status(200).json({
      original: {
        text: input,
        bitsPerToken: originalResult.bitsPerToken,
        totalBits: originalResult.totalBits
      },
      simplified: {
        text: simplifiedText,
        bitsPerToken: simplifiedResult.bitsPerToken,
        totalBits: simplifiedResult.totalBits
      },
      id: data?.[0]?.id
    })

  } catch (error) {
    console.error('API error:', error)
    res.status(500).json({ error: 'Internal server error' })
  }
}

function processTextWithEntropy(text: string): Promise<{ bitsPerToken: number; totalBits: number }> {
  return new Promise((resolve, reject) => {
    const pythonProcess = spawn('python', ['entropy.py'], {
      stdio: ['pipe', 'pipe', 'pipe']
    })

    let output = ''
    let errorOutput = ''

    pythonProcess.stdout.on('data', (data) => {
      output += data.toString()
    })

    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data.toString()
    })

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python process failed: ${errorOutput}`))
        return
      }

      try {
        // Parse the output to extract bits per token
        const lines = output.trim().split('\n')
        const bitsPerTokenLine = lines.find(line => line.includes('Bits per token:'))
        const totalBitsLine = lines.find(line => line.includes('Total bits:'))
        
        if (!bitsPerTokenLine || !totalBitsLine) {
          reject(new Error('Could not parse Python output'))
          return
        }

        const bitsPerToken = parseFloat(bitsPerTokenLine.split(':')[1].trim())
        const totalBits = parseFloat(totalBitsLine.split(':')[1].trim())

        resolve({ bitsPerToken, totalBits })
      } catch (parseError) {
        reject(new Error(`Failed to parse output: ${parseError}`))
      }
    })

    // Send the text to Python process
    pythonProcess.stdin.write(text)
    pythonProcess.stdin.end()
  })
}

function generateSimplifiedText(text: string): string {
  // Simple simplification: remove some common words and make sentences shorter
  const words = text.split(' ')
  const commonWords = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
  
  const filteredWords = words.filter(word => {
    const cleanWord = word.toLowerCase().replace(/[^\w]/g, '')
    return !commonWords.includes(cleanWord) || Math.random() > 0.3
  })

  // Take first 70% of words to make it shorter
  const shortenedWords = filteredWords.slice(0, Math.floor(filteredWords.length * 0.7))
  
  return shortenedWords.join(' ')
}
