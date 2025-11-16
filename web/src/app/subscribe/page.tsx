"use client";

import { useEffect, useMemo, useState } from "react";
import type { Session } from "@supabase/supabase-js";

import Header from "../../components/Header";
import Footer from "../../components/Footer";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import { getSupabaseClient } from "@/lib/supabaseClient";

type Profile = {
  is_subscribed: boolean | null;
  free_calls_used: number | null;
  total_cost_dollars: number | null;
};

export default function SubscribePage() {
  const supabase = useMemo(() => getSupabaseClient(), []);
  const [session, setSession] = useState<Session | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load auth session (same pattern as your login page)
  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      const { data, error } = await supabase.auth.getSession();
      if (cancelled) return;
      if (error) {
        console.error("Error getting session", error);
      }
      setSession(data.session ?? null);
    }

    loadSession();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      if (!cancelled) {
        setSession(newSession);
      }
    });

    return () => {
      cancelled = true;
      subscription.unsubscribe();
    };
  }, [supabase]);

  // Once we have a session, load the profile from app.profiles
  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      if (!session) {
        setProfile(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      const { data: userData, error: userError } = await supabase.auth.getUser();
      if (cancelled) return;

      if (userError || !userData.user) {
        console.error("Error getting user", userError);
        setError("Could not load your profile.");
        setProfile(null);
        setLoading(false);
        return;
      }

      const userId = userData.user.id;

      const { data, error } = await supabase
        .schema("app")
        .from("profiles")
        .select("is_subscribed, free_calls_used, total_cost_dollars")
        .eq("user_id", userId)
        .single();

      if (cancelled) return;

      if (error) {
        console.error("Error loading profile", error);
        setError("Could not load your profile.");
        setProfile(null);
      } else {
        setProfile(data as Profile);
      }

      setLoading(false);
    }

    loadProfile();

    return () => {
      cancelled = true;
    };
  }, [session, supabase]);

  const handleStartCheckout = async () => {
    setCheckoutLoading(true);
    setError(null);

    try {
      const { data } = await supabase.auth.getSession();
      const accessToken = data.session?.access_token;

      if (!accessToken) {
        throw new Error("No active session. Please log in again.");
      }

      const res = await fetch("/api/stripe/create-checkout-session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ access_token: accessToken }),
      });

      if (!res.ok) {
        const text = await res.text();
        console.error("Checkout session error:", text);
        throw new Error("Could not start checkout. Please try again.");
      }

      const json = await res.json();
      if (!json.url) {
        throw new Error("No checkout URL returned.");
      }

      // Redirect to Stripe Checkout
      window.location.href = json.url as string;
    } catch (err: unknown) {
      console.error(err);
      const message = err instanceof Error ? err.message : "Something went wrong starting checkout.";
      setError(message);
    } finally {
      setCheckoutLoading(false);
    }
  };

  let content: React.ReactNode;

  if (!session) {
    content = (
      <div className="flex flex-col gap-4">
        <p className="text-base text-gray-800">
          You’re not logged in.
        </p>
        <a
          href="/login"
          className="inline-flex items-center justify-center px-4 py-2 rounded-md border text-sm font-medium hover:bg-gray-50 transition"
        >
          Go to login
        </a>
      </div>
    );
  } else if (loading) {
    content = <p className="text-base text-gray-700">Loading your plan…</p>;
  } else if (!profile) {
    content = (
      <p className="text-base text-red-600">
        We couldn’t load your profile. Please refresh or contact support.
      </p>
    );
  } else if (!profile.is_subscribed) {
    // Free tier view
    content = (
      <div className="flex flex-col gap-4">
        <p className="text-base text-gray-800">
          You’re currently on the <strong>free plan</strong>.
        </p>
        <ul className="list-disc list-inside text-sm text-gray-700">
          <li>Up to 5 voice calls total.</li>
        </ul>
        {typeof profile.free_calls_used === "number" && (
          <p className="text-sm text-gray-700">
            You’ve used <strong>{profile.free_calls_used}</strong> free calls so far.
          </p>
        )}
        <div className="mt-2">
          <p className="text-base text-gray-900 font-semibold mb-1">
            Upgrade to Pro
          </p>
          <p className="text-sm text-gray-700 mb-3">
            Unlock a higher monthly usage cap and keep using Scaffold after the free tier.
          </p>
          <button
            onClick={handleStartCheckout}
            disabled={checkoutLoading}
            className="inline-flex items-center justify-center px-4 py-2 rounded-md border text-sm font-medium hover:bg-gray-50 transition disabled:opacity-60"
          >
            {checkoutLoading ? "Redirecting to Stripe…" : "Subscribe with Stripe"}
          </button>
        </div>
        {error && (
          <p className="text-sm text-red-600">
            {error}
          </p>
        )}
      </div>
    );
  } else {
    // Subscribed view
    content = (
      <div className="flex flex-col gap-4">
        <p className="text-base text-gray-800">
          You’re on the <strong>paid plan</strong>
        </p>
        <p className="text-sm text-gray-700">
          Your usage this month:{" "}
          <strong>${profile.total_cost_dollars ?? 0}</strong> out of your cap.
        </p>
        {/* Later we can add a “Manage billing” button (Stripe Customer Portal) */}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start min-h-screen px-4 pt-20 md:pt-25">
        <Card>
          <CardTitle className="text-3xl md:text-4xl font-bold text-gray-900 leading-relaxed text-center">
            Subscription
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
