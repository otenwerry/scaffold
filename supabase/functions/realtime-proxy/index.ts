import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3'

const OPENAI_API_KEY = Deno.env.get('OPENAI_API_KEY')
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const MAX_SESSION_DURATION_MS = 5 * 60 * 1000 // 5 minutes

interface UsageData {
  input_tokens: number
  output_tokens: number
  input_token_details: {
    audio_tokens: number
    text_tokens: number
    cached_tokens?: number
  }
  output_token_details: {
    audio_tokens: number
    text_tokens: number
  }
}

Deno.serve(async (req) => {
  // Only handle WebSocket upgrade requests
  if (req.headers.get('upgrade') !== 'websocket') {
    return new Response('Expected WebSocket', { status: 426 })
  }

  console.log('WebSocket upgrade requested')

  // Get auth token from request
  const authHeader = req.headers.get('authorization')
  if (!authHeader?.startsWith('Bearer ')) {
    console.error('Missing or invalid authorization header')
    return new Response('Unauthorized', { status: 401 })
  }

  const token = authHeader.substring(7)

  // Verify user with Supabase
  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
  const { data: { user }, error: authError } = await supabase.auth.getUser(token)

  if (authError || !user) {
    console.error('Auth failed:', authError?.message)
    return new Response('Unauthorized', { status: 401 })
  }

  console.log(`User authenticated: ${user.id}`)

  // Check quota
  const { data: quotaData, error: quotaError } = await supabase.rpc('rpc_check_quota')

  if (quotaError) {
    console.error('Quota check failed:', quotaError.message)
    return new Response('Quota check failed', { status: 500 })
  }

  const [allowed, used, remaining, limit] = quotaData[0] || []
  console.log(`Quota check: allowed=${allowed}, used=${used}, remaining=${remaining}, limit=${limit}`)

  if (!allowed) {
    console.log('User over quota')
    return new Response(JSON.stringify({
      error: 'quota_exceeded',
      message: 'You have exceeded your usage limit',
      used,
      limit
    }), {
      status: 403,
      headers: { 'Content-Type': 'application/json' }
    })
  }

  // Upgrade to WebSocket
  const { socket: clientSocket, response } = Deno.upgradeWebSocket(req)
  console.log('Client WebSocket upgraded')

  let openaiSocket: WebSocket | null = null
  let sessionStartTime = Date.now()
  let sessionTimeout: number | null = null
  let accumulatedUsage: UsageData | null = null

  // Track usage when session ends
  const trackUsage = async () => {
    if (!accumulatedUsage) {
      console.log('No usage data to track')
      return
    }

    const usage = accumulatedUsage
    const audioInputTokens = usage.input_token_details?.audio_tokens || 0
    const audioOutputTokens = usage.output_token_details?.audio_tokens || 0
    const textInputTokens = (usage.input_token_details?.text_tokens || 0) + (usage.input_token_details?.cached_tokens || 0)
    const textOutputTokens = usage.output_token_details?.text_tokens || 0

    // Calculate costs (prices per 1M tokens)
    const textInputCost = (textInputTokens / 1_000_000) * 4
    const textOutputCost = (textOutputTokens / 1_000_000) * 16
    const audioInputCost = (audioInputTokens / 1_000_000) * 32
    const audioOutputCost = (audioOutputTokens / 1_000_000) * 64
    const totalCost = textInputCost + textOutputCost + audioInputCost + audioOutputCost

    console.log(`Usage: text_in=${textInputTokens}, text_out=${textOutputTokens}, audio_in=${audioInputTokens}, audio_out=${audioOutputTokens}, cost=$${totalCost.toFixed(4)}`)

    try {
      const { data, error } = await supabase.rpc('rpc_track_usage', {
        p_text_input_tokens: textInputTokens,
        p_text_output_tokens: textOutputTokens,
        p_audio_input_tokens: audioInputTokens,
        p_audio_output_tokens: audioOutputTokens,
        p_total_cost: totalCost
      })

      if (error) {
        console.error('Failed to track usage:', error.message)
      } else {
        console.log('Usage tracked successfully')
      }
    } catch (err) {
      console.error('Exception tracking usage:', err)
    }
  }

  // Cleanup function
  const cleanup = async () => {
    console.log('Cleaning up session')
    
    if (sessionTimeout) {
      clearTimeout(sessionTimeout)
      sessionTimeout = null
    }

    if (openaiSocket && openaiSocket.readyState === WebSocket.OPEN) {
      openaiSocket.close()
    }

    await trackUsage()
  }

  // Set up session timeout
  sessionTimeout = setTimeout(() => {
    console.log('Session timeout reached (5 minutes)')
    clientSocket.close(1000, 'Session timeout')
  }, MAX_SESSION_DURATION_MS)

  // Handle client messages
  clientSocket.onopen = async () => {
    console.log('Client WebSocket opened, connecting to OpenAI')

    try {
      // Connect to OpenAI Realtime API
      const openaiUrl = 'wss://api.openai.com/v1/realtime?model=gpt-realtime'
      openaiSocket = new WebSocket(openaiUrl, {
        headers: {
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
          'OpenAI-Beta': 'realtime=v1'
        }
      })

      openaiSocket.onopen = () => {
        console.log('OpenAI WebSocket connected')
      }

      openaiSocket.onmessage = (event) => {
        // Forward OpenAI messages to client
        if (clientSocket.readyState === WebSocket.OPEN) {
          clientSocket.send(event.data)
        }

        // Track usage from response.done events
        try {
          const message = JSON.parse(event.data)
          if (message.type === 'response.done') {
            const usage = message.response?.usage
            if (usage) {
              accumulatedUsage = usage
              console.log('Captured usage data from response.done')
            }
          }
        } catch (e) {
          // Not JSON or missing usage, ignore
        }
      }

      openaiSocket.onerror = (error) => {
        console.error('OpenAI WebSocket error:', error)
        if (clientSocket.readyState === WebSocket.OPEN) {
          clientSocket.close(1011, 'OpenAI connection error')
        }
      }

      openaiSocket.onclose = () => {
        console.log('OpenAI WebSocket closed')
        if (clientSocket.readyState === WebSocket.OPEN) {
          clientSocket.close()
        }
      }

    } catch (err) {
      console.error('Failed to connect to OpenAI:', err)
      clientSocket.close(1011, 'Failed to connect to OpenAI')
    }
  }

  clientSocket.onmessage = (event) => {
    // Handle special client messages
    try {
      const message = JSON.parse(event.data)
      
      // If client sends screen context, forward it as a conversation item
      if (message.type === 'screen_context') {
        console.log(`Received screen context: ${message.text?.length || 0} chars`)
        
        if (openaiSocket && openaiSocket.readyState === WebSocket.OPEN) {
          // Forward as conversation item to OpenAI
          openaiSocket.send(JSON.stringify({
            type: 'conversation.item.create',
            item: {
              type: 'message',
              role: 'user',
              content: [{
                type: 'input_text',
                text: `Screen content:\n${message.text}`
              }]
            }
          }))
        }
        return
      }
    } catch (e) {
      // Not a special message, just forward it
    }

    // Forward all other client messages to OpenAI
    if (openaiSocket && openaiSocket.readyState === WebSocket.OPEN) {
      openaiSocket.send(event.data)
    }
  }

  clientSocket.onerror = (error) => {
    console.error('Client WebSocket error:', error)
  }

  clientSocket.onclose = async () => {
    console.log('Client WebSocket closed')
    await cleanup()
  }

  return response
})