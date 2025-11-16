"use client";

import { useEffect, useState, useMemo } from "react";
import type { Session } from "@supabase/supabase-js";

import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import { getSupabaseClient } from "@/lib/supabaseClient";

export default function LogIn() {
  const supabase = useMemo(() => getSupabaseClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      const { data, error } = await supabase.auth.getSession();
      if (cancelled) return;
      if (error) {
        console.error("Error getting session", error);
      }
      setSession(data.session ?? null);
      setLoading(false);
    }

    loadSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [supabase]);

  useEffect(() => {
    let cancelled = false;

    async function validateSession() {
      if (!session) return;

      const { data, error } = await supabase.auth.getUser();

      if (cancelled) return;

      if (error) {
        console.warn("Supabase session invalid, clearing it", error);

        // Wipe out the stale browser session so we force a real re-login.
        await supabase.auth.signOut();

        if (!cancelled) {
          setSession(null);
        }
      }
    }

    validateSession();

    return () => {
      cancelled = true;
    };
  }, [session, supabase]);


  const handleLoginWithGoogle = async () => {
    const redirectTo =
      typeof window !== "undefined"
        ? `${window.location.origin}/login`
        : undefined;

    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo,
      },
    });

    if (error) {
      console.error("Error starting Google login", error);
      alert("Could not start Google login. Please try again.");
    }
  };

  let content: React.ReactNode;

  if (loading) {
    content = (
      <p className="text-base text-gray-700">
        Checking your session…
      </p>
    );
  } else if (!session) {
    content = (
      <div className="flex flex-col gap-4">
        <p className="text-base text-gray-800">
          Sign in with Google to connect your Scaffold macOS app.
        </p>
        <button
          onClick={handleLoginWithGoogle}
          className="inline-flex items-center justify-center px-4 py-2 rounded-md border text-sm font-medium hover:bg-gray-50 transition"
        >
          Log in with Google
        </button>
        <p className="text-xs text-gray-500 max-w-md">
          We’ll open a Google sign-in flow. When you’re done, you’ll come back
          here and can reopen the macOS app with your new account.
        </p>
      </div>
    );
  } else {
    const accessToken = session.access_token;
    const refreshToken = session.refresh_token;

    const deepLink = `scaffold://auth-callback?access_token=${encodeURIComponent(
      accessToken
    )}&refresh_token=${encodeURIComponent(refreshToken)}`;

    content = (
      <div className="flex flex-col gap-4">
        <p className="text-base text-gray-800">
          You’re signed in as{" "}
          <strong>{session.user.email}</strong>.
        </p>
        <a
          href={deepLink}
          className="inline-flex items-center justify-center px-4 py-2 rounded-md border text-sm font-medium hover:bg-gray-50 transition text-center"
        >
          Reopen Scaffold macOS app
        </a>
        <p className="text-xs text-gray-500 max-w-md">
          If nothing happens when you click the button, make sure the Scaffold
          app is installed and has been opened at least once on this Mac.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start min-h-screen px-4 pt-20 md:pt-25">
        <Card>
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">
            Log In
          </CardTitle>
          <CardContent className="mt-4 text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
            {content}
          </CardContent>
        </Card>
        <Footer />
      </main>
    </div>
  );
}
