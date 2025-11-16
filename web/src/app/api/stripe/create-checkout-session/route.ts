import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY as string, {
  apiVersion: "2024-06-20",
});

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL as string,
  process.env.SUPABASE_SERVICE_ROLE_KEY as string
);

export async function POST(req: NextRequest) {
  try {
    // 1) Get access token from body
    const body = await req.json().catch(() => null) as { access_token?: string } | null;
    const accessToken = body?.access_token;

    if (!accessToken) {
      return NextResponse.json(
        { error: "Missing access token" },
        { status: 401 }
      );
    }

    // 2) Validate token / get Supabase user
    const {
      data: { user },
      error: userError,
    } = await supabaseAdmin.auth.getUser(accessToken);

    if (userError || !user) {
      console.error("getUser error", userError);
      return NextResponse.json(
        { error: "Invalid session" },
        { status: 401 }
      );
    }

    const userId = user.id;
    const email = user.email ?? undefined;

    // 3) Get or create Stripe customer
    const { data: profile, error: profileError } = await supabaseAdmin
      .schema("app")
      .from("profiles")
      .select("stripe_customer_id")
      .eq("user_id", userId)
      .single();

    if (profileError) {
      console.error("Error fetching profile", profileError);
      return NextResponse.json(
        { error: "Could not load user profile" },
        { status: 400 }
      );
    }

    let stripeCustomerId = profile?.stripe_customer_id as string | null;

    if (!stripeCustomerId) {
      // Create a Stripe customer if this is the first time
      const customer = await stripe.customers.create({
        email,
        metadata: {
          supabase_user_id: userId,
        },
      });

      stripeCustomerId = customer.id;

      await supabaseAdmin
        .schema("app")
        .from("profiles")
        .update({ stripe_customer_id: stripeCustomerId })
        .eq("user_id", userId);
    }

    // 4) Create Checkout Session
    const priceId = process.env.STRIPE_PRICE_ID;
    if (!priceId) {
      throw new Error("Missing STRIPE_PRICE_ID environment variable.");
    }

    const successUrl = `${process.env.NEXT_PUBLIC_SITE_URL}/subscribe?status=success`;
    const cancelUrl = `${process.env.NEXT_PUBLIC_SITE_URL}/subscribe?status=cancel`;

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      customer: stripeCustomerId,
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      success_url: successUrl,
      cancel_url: cancelUrl,
      client_reference_id: userId,
      metadata: {
        supabase_user_id: userId,
      },
    });

    if (!session.url) {
      throw new Error("No session URL returned from Stripe.");
    }

    return NextResponse.json({ url: session.url });
  } catch (err: any) {
    console.error("Error creating checkout session", err);
    return NextResponse.json(
      { error: "Internal error creating checkout session" },
      { status: 500 }
    );
  }
}
