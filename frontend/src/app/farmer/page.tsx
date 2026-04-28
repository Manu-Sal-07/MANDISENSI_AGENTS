import { fetchPrediction } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { PremiumDashboard } from "@/components/dashboard/PremiumDashboard";

// Ensure this page loads fresh data and doesn't get statically cached
export const revalidate = 0;

export default async function FarmerPage() {
  const data = await fetchPrediction("onion", "kolar");
  const guidance = data.farmer_guidance;

  const MOCK_EXTENSIONS = {
    alerts: [
      guidance.risk_label === "High" ? "High risk of volatility detected" : "Market conditions are steady",
      guidance.decision === "SELL" ? "Strong selling window open" : "Hold your inventory"
    ],
    changes: "Backend models updated with new arrival volumes",
    accuracy: 72,
    users: 1240,
    price_now: 30,
    mandis: [
      { name: "Kolar", price: 32 },
      { name: "Hoskote", price: 28 }
    ],
    last_prediction: {
      predicted: "29-33",
      actual: 32
    }
  };

  return (
    <div className="flex flex-col min-h-screen w-full bg-[#020617] text-slate-50 relative overflow-x-hidden">
      <Header />
      <main className="flex-1 overflow-y-auto no-scrollbar">
        <PremiumDashboard data={data} mockExtensions={MOCK_EXTENSIONS} />
      </main>
    </div>
  );
}
