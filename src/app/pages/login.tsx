import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '../lib/supabase'

export default function Login() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Auth
        supabaseClient={supabase}
        appearance={{ theme: ThemeSupa }}
        theme="light"
        providers={['google']}
        redirectTo="/"
      />
    </div>
  )
}