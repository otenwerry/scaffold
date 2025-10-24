import { NextRequest, NextResponse } from "next/server";
import { stripe } from "../../../lib/stripe";
import Stripe from "stripe";

export const runtime = "nodejs";
export const dynamic = "force-dynamic"; // ensure edge caching doesn't interfere

export async function POST(req: NextRequest) {
  const sig = req.headers.get("stripe-signature");
  const buf = Buffer.from(await req.arrayBuffer());

  if (!sig) return NextResponse.json({ error: "No signature" }, { status: 400 });

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(
      buf,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET!
    );
  } catch (err: any) {
    return NextResponse.json({ error: `Webhook Error: ${err.message}` }, { status: 400 });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        // session.customer (id) & session.subscription (id)
        // TODO: upsert user in DB with customerId/subscriptionId
        break;
      }
      case "customer.subscription.created":
      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const sub = event.data.object as Stripe.Subscription;
        // sub.status, sub.items, sub.current_period_end, sub.customer
        // TODO: update user's entitlements in DB
        break;
      }
      case "invoice.payment_failed": {
        // TODO: email / degrade access after grace period
        break;
      }
      default:
        // no-op
        break;
    }
    return NextResponse.json({ received: true }, { status: 200 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
