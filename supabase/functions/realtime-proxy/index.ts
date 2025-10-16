import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3'
import WebSocket from 'npm:ws'

const OPENAI_API_KEY = Deno.env.get('OPENAI_API_KEY')
const SUPABASE_URL = Deno.env.get('URL')!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SERVICE_ROLE_KEY')!
const SUPABASE_ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!
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
  const supabaseAdmin = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
  const { data: { user }, error: authError } = await supabaseAdmin.auth.getUser(token)
  // User client for RPC calls
const supabaseUser = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    global: {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    }
})
const appDB = supabaseUser.schema('app')

  if (authError || !user) {
    console.error('Auth failed:', authError?.message)
    return new Response('Unauthorized', { status: 401 })
  }

  console.log(`User authenticated: ${user.id}`)

  // Check quota
  const { data: quotaData, error: quotaError } = await appDB.rpc('rpc_check_quota')

  if (quotaError) {
    console.error('Quota check failed:', quotaError.message)
    return new Response('Quota check failed', { status: 500 })
  }

  const row = quotaData?.[0]
  if (!row) {
    console.error('Quota check returned no rows')
    return new Response('Quota check failed', { status: 500 })
  }
  const { allowed, used, remaining, limit } = row
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
      const { data, error } = await appDB.rpc('rpc_track_usage', {
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
// === Session ownership + state machine (put near other top-level consts) ===
const SYSTEM_PROMPT = Deno.env.get("SYSTEM_PROMPT") ?? "You are a concise, helpful AI tutor.";
const MIN_AUDIO_BYTES_100MS = 4800; // 24kHz mono PCM16 => 0.1s * 24000 * 2 bytes
type Phase = "IDLE" | "STREAMING" | "AWAITING_RESPONSE";

let openaiSocket: WebSocket | null = null;
let configured = false;
let phase: Phase = "IDLE";
let bufferedAudioBytes = 0;
const pendingToOpenAI: string[] = [];
const pendingClientMsgsUntilConfigured: string[] = [];

// === Helpers ===
const sendToClient = (obj: unknown) => {
  if (clientSocket.readyState === WebSocket.OPEN) clientSocket.send(JSON.stringify(obj));
};
const forwardToOpenAI = (obj: unknown) => {
  const msg = typeof obj === "string" ? obj : JSON.stringify(obj);
  if (openaiSocket && openaiSocket.readyState === WebSocket.OPEN) openaiSocket.send(msg);
  else pendingToOpenAI.push(msg);
};
const flushPendingToOpenAI = () => {
  for (const m of pendingToOpenAI) openaiSocket!.send(m);
  pendingToOpenAI.length = 0;
};
const flushBufferedClientMsgs = () => {
  for (const m of pendingClientMsgsUntilConfigured) openaiSocket!.send(m);
  pendingClientMsgsUntilConfigured.length = 0;
};

// === Client socket opened: connect to OpenAI ===
clientSocket.onopen = async () => {
  try {
    const openaiUrl = "wss://api.openai.com/v1/realtime?model=gpt-realtime";
    openaiSocket = new WebSocket(openaiUrl, {
      headers: {
        Authorization: `Bearer ${OPENAI_API_KEY}`,
        "OpenAI-Beta": "realtime=v1",
      },
    });

    // OpenAI connected: immediately configure the session (NO VAD, with instructions)
    openaiSocket.onopen = () => {
      // Baseline session.update owned by EDGE
      console.log("SESSION.UPDATE: sending baseline config");
      console.log("SYSTEM_PROMPT: ", SYSTEM_PROMPT);
      forwardToOpenAI({
        type: "session.update",
        session: {
          instructions: SYSTEM_PROMPT,
          modalities: ["text", "audio"],
          voice: "alloy",
          input_audio_format: "pcm16",
          output_audio_format: "pcm16",
          input_audio_transcription: { model: "whisper-1" },
          turn_detection: null, // disable VAD at the server
        },
      });
      console.log("SESSION.UPDATE: sent");
    };

    // Messages from OpenAI → Client, and local state updates
    openaiSocket.onmessage = (event) => {
      // Always forward raw data to client
      if (clientSocket.readyState === WebSocket.OPEN) clientSocket.send(event.data);

      // Track config/phase/usage
      try {
        const msg = JSON.parse(event.data as string);

        if (msg.type === "session.updated") {
          console.log("SESSION.UPDATED: ack from OpenAI (config is active)");
          configured = true;
          // Only now allow anything to flow to OpenAI
          flushBufferedClientMsgs();
          flushPendingToOpenAI();
        }

        if (msg.type === "response.created") {
          console.log("RESPONSE.CREATED: turn started (should follow canary prompt)");
          phase = "AWAITING_RESPONSE";
        }
        if (msg.type === "response.done") {
          console.log("RESPONSE.DONE: turn finished");
          phase = "IDLE";
          bufferedAudioBytes = 0;
          // (Your existing usage capture stays as-is)
          const usage = msg.response?.usage;
          if (usage) accumulatedUsage = usage;
        }
      } catch {
        /* not JSON – ignore */
      }
    };

    openaiSocket.onerror = (error) => {
      console.error("OpenAI WebSocket error:", error);
      if (clientSocket.readyState === WebSocket.OPEN) clientSocket.close(1011, "OpenAI connection error");
    };
    openaiSocket.onclose = () => {
      console.log("OpenAI WebSocket closed");
      if (clientSocket.readyState === WebSocket.OPEN) clientSocket.close();
    };
  } catch (err) {
    console.error("Failed to connect to OpenAI:", err);
    clientSocket.close(1011, "Failed to connect to OpenAI");
  }
};

// Messages from client → EDGE (we own the turn lifecycle)
clientSocket.onmessage = (event) => {
  // Accept only these client-originated types:
  //  - input_audio_buffer.append (audio streaming)
  //  - client.end (custom; user finished speaking)
  //  - screen_context (optional text context; we may queue a response)
  // Any client-side commit/response/create is blocked here.

  let parsed: any = null;
  try { parsed = JSON.parse(event.data as string); } catch { /* non-JSON: ignore */ }

  // Block disallowed control messages from client
  if (parsed && (parsed.type === "input_audio_buffer.commit" || parsed.type === "response.create")) {
    return sendToClient({
      type: "error",
      error: { type: "invalid_request_error", code: "client_control_blocked", message: "Client may not commit or create responses." },
    });
  }

  // 1) Audio streaming from client
  if (parsed && parsed.type === "input_audio_buffer.append") {
    if (!configured) {
      pendingClientMsgsUntilConfigured.push(JSON.stringify(parsed));
      return;
    }
    // Track bytes to enforce ≥100ms on commit
    try {
      const b64 = parsed.audio as string;
      const bytes = b64 ? (typeof atob === "function" ? atob(b64) : Buffer.from(b64, "base64").toString("binary")).length : 0;
      bufferedAudioBytes += bytes;
    } catch { /* ignore size if decoding fails */ }

    phase = phase === "IDLE" ? "STREAMING" : phase;
    return forwardToOpenAI(parsed);
  }

  // 2) Client indicates they're done talking
  if (parsed && parsed.type === "client.end") {
    if (!configured) {
      pendingClientMsgsUntilConfigured.push(JSON.stringify(parsed));
      return;
    }
    if (phase !== "STREAMING") {
      return sendToClient({
        type: "error",
        error: { type: "invalid_request_error", code: "no_active_stream", message: "No active audio stream to end." },
      });
    }
    if (bufferedAudioBytes < MIN_AUDIO_BYTES_100MS) {
      // Don't commit; reset state and inform client
      phase = "IDLE";
      bufferedAudioBytes = 0;
      return sendToClient({
        type: "error",
        error: { type: "invalid_request_error", code: "input_audio_buffer_commit_empty", message: "No speech detected (need ≥100ms of audio)." },
      });
    }
    // Single authoritative commit + response
    forwardToOpenAI({ type: "input_audio_buffer.commit" });
    phase = "AWAITING_RESPONSE";
    forwardToOpenAI({ type: "response.create" });
    return;
  }

  // 3) Screen context (text) → add item, and (if idle) create one response
  if (parsed && parsed.type === "screen_context") {
    const item = {
      type: "conversation.item.create",
      item: {
        type: "message",
        role: "user",
        content: [{ type: "input_text", text: `Screen content:\n${parsed.text ?? ""}` }],
      },
    };
    if (!configured) {
      pendingClientMsgsUntilConfigured.push(JSON.stringify(item));
      return;
    }
    forwardToOpenAI(item);

    if (phase === "IDLE") {
      phase = "AWAITING_RESPONSE";
      forwardToOpenAI({ type: "response.create" });
    } // else: if STREAMING/AWAITING_RESPONSE, do nothing (no duplicates)
    return;
  }

  // Everything else from client is ignored (or you can log it)
};


  clientSocket.onerror = (error) => {
    console.error('Client WebSocket error:', error)
  }

  clientSocket.onclose = async () => {
    console.log('Client WebSocket closed')
    await cleanup()
  }

  return response
})