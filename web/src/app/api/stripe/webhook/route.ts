import { NextRequest, NextResponse } from "next/server";
import { headers } from "next/headers";
import Stripe from "stripe";
import { createClient } from "@supabase/supabase-js";

export const runtime = "nodejs"; // important: Stripe SDK expects Node, not edge

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY as string);

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL as string,
  process.env.SUPABASE_SERVICE_ROLE_KEY as string
);

// Helper: update subscription status in app.profiles
async function updateSubscriptionForCustomer(opts: {
    stripeCustomerId: string;
    stripeSubscriptionId: string | null;
    status: Stripe.Subscription.Status | string;
    supabaseUserId?: string | null;
  }) {
    const { stripeCustomerId, stripeSubscriptionId, status, supabaseUserId } = opts;
  
    const activeStatuses = new Set(["active", "trialing"]);
    const isSubscribed = activeStatuses.has(status);
  
    // --- Fetch the profile row we need to update ---
  
    let profilesRes;
    if (supabaseUserId) {
      profilesRes = await supabaseAdmin
        .schema("app")
        .from("profiles")
        .select("user_id")
        .eq("user_id", supabaseUserId)
        .limit(1);
    } else {
      profilesRes = await supabaseAdmin
        .schema("app")
        .from("profiles")
        .select("user_id")
        .eq("stripe_customer_id", stripeCustomerId)
        .limit(1);
    }
  
    const { data: profiles, error: fetchError } = profilesRes;
  
    if (fetchError) {
      console.error("Error fetching profile in webhook:", fetchError);
      return;
    }
  
    if (!profiles || profiles.length === 0) {
      console.warn(
        "No profile found for customer in webhook",
        stripeCustomerId,
        supabaseUserId
      );
      return;
    }
  
    const userId = profiles[0].user_id;
  
    // --- Update subscription fields in app.profiles ---
  
    const { error: updateError } = await supabaseAdmin
      .schema("app")
      .from("profiles")
      .update({
        stripe_customer_id: stripeCustomerId,
        stripe_subscription_id: stripeSubscriptionId,
        stripe_subscription_status: status,
        is_subscribed: isSubscribed,
      })
      .eq("user_id", userId);
  
    if (updateError) {
      console.error("Error updating profile subscription status:", updateError);
    }
  }
  

  export async function POST(req: NextRequest) {
    // Use headers from the request directly
    const sig = req.headers.get("stripe-signature");
    const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  
    if (!sig || !webhookSecret) {
      return NextResponse.json(
        { error: "Missing webhook configuration" },
        { status: 400 }
      );
    }
  
    let event: Stripe.Event;
  
    try {
      const rawBody = await req.text(); // IMPORTANT: raw text, not JSON
      event = stripe.webhooks.constructEvent(rawBody, sig, webhookSecret);
    } catch (err: any) {
      console.error("Error verifying Stripe webhook signature:", err);
      return NextResponse.json(
        { error: `Webhook Error: ${err.message}` },
        { status: 400 }
      );
    }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;

        const stripeCustomerId = session.customer as string;
        const subscriptionId = session.subscription as string | null;
        const supabaseUserId =
          (session.metadata && session.metadata["supabase_user_id"]) ||
          session.client_reference_id ||
          null;

        // Stripe marks the subscription "active/trialing" shortly after
        await updateSubscriptionForCustomer({
          stripeCustomerId,
          stripeSubscriptionId: subscriptionId,
          status: "active",
          supabaseUserId,
        });

        break;
      }

      case "customer.subscription.created":
      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const subscription = event.data.object as Stripe.Subscription;

        const stripeCustomerId = subscription.customer as string;
        const subscriptionId = subscription.id;
        const status = subscription.status;
        const supabaseUserId =
          subscription.metadata && subscription.metadata["supabase_user_id"]
            ? (subscription.metadata["supabase_user_id"] as string)
            : undefined;

        await updateSubscriptionForCustomer({
          stripeCustomerId,
          stripeSubscriptionId: subscriptionId,
          status,
          supabaseUserId,
        });

        break;
      }

      default: {
        // For now, ignore other event types
        break;
      }
    }

    // Stripe just needs a 2xx response to acknowledge
    return NextResponse.json({ received: true }, { status: 200 });
  } catch (err) {
    console.error("Error handling Stripe webhook event:", err);
    return NextResponse.json(
      { error: "Webhook handler failed" },
      { status: 500 }
    );
  }
}
