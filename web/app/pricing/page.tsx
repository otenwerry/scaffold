"use client";

import { useSearchParams } from "next/navigation";
import { useState } from "react";

function Logo() {
  return (
    <svg width="14" height="16" viewBox="0 0 14 16" aria-hidden>
      <path
        d="M127,50 L126,50 C123.238576,50 121,47.7614237 121,45 C121,42.2385763 123.238576,40 126,40 L135,40 L135,56 L133,56 L133,42 L129,42 L129,56 L127,56 L127,50 Z M127,48 L127,42 L126,42 C124.343146,42 123,43.3431458 123,45 C123,46.6568542 124.343146,48 126,48 L127,48 Z"
        transform="translate(-121 -40)"
        fill="#E184DF"
      />
    </svg>
  );
}

function SubscribeButton({
  lookupKey,
  priceId,
}: { lookupKey?: string; priceId?: string }) {
  const [loading, setLoading] = useState(false);

  const startCheckout = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lookupKey: lookupKey ?? process.env.NEXT_PUBLIC_STRIPE_PRICE_LOOKUP_KEY,
          priceId,
        }),
      });
      const data = await res.json();
      if (data.url) window.location.href = data.url;
      else alert(data.error || "Failed to start checkout");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={startCheckout}
      className="rounded-2xl px-4 py-2 shadow"
      disabled={loading}
    >
      {loading ? "Redirecting…" : "Checkout"}
    </button>
  );
}

function PortalButton({ customerId }: { customerId?: string }) {
  const [loading, setLoading] = useState(false);

  const openPortal = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customerId }), // in real app, omit—server infers from session
      });
      const data = await res.json();
      if (data.url) window.location.href = data.url;
      else alert(data.error || "Could not open portal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={openPortal}
      className="rounded-2xl px-4 py-2 shadow"
      disabled={loading}
    >
      {loading ? "Opening…" : "Manage billing"}
    </button>
  );
}

export default function PricingPage() {
  const qp = useSearchParams();
  const success = qp.get("success");
  const canceled = qp.get("canceled");
  const sessionId = qp.get("session_id");

  return (
    <section className="max-w-xl mx-auto p-6 grid gap-4">
      <div className="flex items-center gap-3">
        <Logo />
        <div>
          <h3 className="text-lg font-semibold">Starter Plan</h3>
          <p className="text-sm opacity-70">$20.00 / month</p>
        </div>
      </div>

      {!success && !canceled && (
        <SubscribeButton lookupKey={process.env.NEXT_PUBLIC_STRIPE_PRICE_LOOKUP_KEY} />
      )}

      {success && sessionId && (
        <div className="rounded-xl p-4 bg-green-50">
          <p className="font-medium">Subscription successful!</p>
          <p className="text-sm opacity-70">Session: {sessionId}</p>
          <div className="mt-3">
            <PortalButton />
          </div>
        </div>
      )}

      {canceled && (
        <p className="rounded-xl p-4 bg-yellow-50">
          Order canceled — try again anytime.
        </p>
      )}
    </section>
  );
}