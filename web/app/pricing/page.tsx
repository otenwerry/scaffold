"use client";

import Header from "../components/Header";
import { useSearchParams } from "next/navigation";

export default function PricingPage() {
  return (
    <div className="flex flex-col items-center justify-center">
    <Header />
    <script async src="https://js.stripe.com/v3/pricing-table.js"></script>
    <div 
      dangerouslySetInnerHTML={{
        __html: `<stripe-pricing-table 
          pricing-table-id="prctbl_1SEKUNLsDCj5bzxFnPy8MS31"
          publishable-key="pk_test_51SDdSxLsDCj5bzxF3VNe8j0dq7K5CSV1Yil436bRRDV68jSTOWPNbfrTZLzR6vmuGfOR3aqhglEPxcaD1D1kQORL00BI4icUH8">
        </stripe-pricing-table>`
      }}
    />
    </div>
  );
}