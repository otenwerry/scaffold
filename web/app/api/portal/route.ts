import { NextRequest, NextResponse } from "next/server";
//import { stripe } from "../../lib/stripe";
/*
export const runtime = "nodejs";

// Replace this with your auth lookup (e.g., Supabase) to find the user's customer id
async function getCustomerIdFromSessionOrDB(): Promise<string | null> {
  // TODO: read session, then fetch user.stripeCustomerId from your DB
  return null;
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}));
    const customerId =
      (await getCustomerIdFromSessionOrDB()) || body.customerId || null;

    if (!customerId) {
      return NextResponse.json(
        { error: "Missing Stripe customer id" },
        { status: 400 }
      );
    }
    
    const portal = await stripe.billingPortal.sessions.create({
      customer: customerId,
      return_url:
        process.env.STRIPE_PORTAL_RETURN_URL ||
        process.env.NEXT_PUBLIC_SITE_URL!,
    });
    
    return NextResponse.json({ url: portal.url });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}*/