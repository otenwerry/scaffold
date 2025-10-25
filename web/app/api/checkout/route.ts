import { NextRequest, NextResponse } from "next/server";
//import { stripe } from "../../lib/stripe";
/*
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const { lookupKey, priceId, customerId } = await req.json();
    const origin =
      process.env.NEXT_PUBLIC_SITE_URL || req.headers.get("origin") || "";

    // Choose ONE: lookupKey (recommended) or priceId (explicit)
    let price = priceId as string | undefined;
    if (!price && lookupKey) {
      const prices = await stripe.prices.list({
        lookup_keys: [lookupKey],
        expand: ["data.product"],
      });
      price = prices.data[0]?.id;
    }
    if (!price) {
      return NextResponse.json({ error: "Price not found" }, { status: 400 });
    }
    
    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      line_items: [{ price, quantity: 1 }],
      success_url: `${origin}/pricing?success=1&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/pricing?canceled=1`,
      allow_promotion_codes: true,
      billing_address_collection: "auto",
      // If your user already has a Stripe customer id:
      // customer: customerId,
    });
  
    return NextResponse.json({ url: session.url });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
*/