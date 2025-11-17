import { NextRequest, NextResponse } from "next/server";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY as string);

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL as string,
  process.env.SUPABASE_SERVICE_ROLE_KEY as string
);

export async function POST(req: NextRequest) {
  try {
    const body = (await req.json().catch(() => null)) as { access_token?: string } | null;
    const accessToken = body?.access_token;

    if (!accessToken) {
      return NextResponse.json(
        { error: "Missing access token" },
        { status: 401 }
      );
    }

    // Validate token / get Supabase user
    const {
      data: { user },
      error: userError,
    } = await supabaseAdmin.auth.getUser(accessToken);

    if (userError || !user) {
      console.error("getUser error in portal session", userError);
      return NextResponse.json(
        { error: "Invalid session" },
        { status: 401 }
      );
    }

    const userId = user.id;

    // Fetch profile to get stripe_customer_id
    const { data: profile, error: profileError } = await supabaseAdmin
      .schema("app")
      .from("profiles")
      .select("stripe_customer_id")
      .eq("user_id", userId)
      .single();

    if (profileError) {
      console.error("Error fetching profile in portal session", profileError);
      return NextResponse.json(
        { error: "Could not load user profile" },
        { status: 400 }
      );
    }

    let stripeCustomerId = profile?.stripe_customer_id as string | null;

    // If no customer exists yet, create one (rare for subscribed users, but safe)
    if (!stripeCustomerId) {
      const customer = await stripe.customers.create({
        email: user.email ?? undefined,
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

    const returnUrl = `${process.env.NEXT_PUBLIC_SITE_URL}/subscribe`;

    const session = await stripe.billingPortal.sessions.create({
      customer: stripeCustomerId,
      return_url: returnUrl,
    });

    return NextResponse.json({ url: session.url }, { status: 200 });
  } catch (err: unknown) {
    console.error("Error creating billing portal session", err);
    return NextResponse.json(
      {
        error:
          err instanceof Error ? err.message : "Internal error creating portal session",
      },
      { status: 500 }
    );
  }
}
