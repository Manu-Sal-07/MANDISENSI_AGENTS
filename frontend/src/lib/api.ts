export interface PredictionResponse {
  request_id: string;
  commodity: string;
  mandi: string;
  prediction: {
    price_change_7d_pct: number;
    confidence: number;
    direction: string;
  };
  attribution: {
    seasonality_pct: number;
    arrival_pct: number;
    external_pct: number;
  };
  farmer_guidance: {
    decision: "SELL" | "WAIT";
    price_range: {
      min: number;
      max: number;
    };
    confidence_label: "High" | "Medium" | "Low";
    risk_label: "High" | "Medium" | "Low";
    explanation: string[];
  };
}

export async function fetchPrediction(commodity: string, mandi: string): Promise<PredictionResponse> {
  // Use a timeout of 10 seconds to prevent endless loading in the UI
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch("http://127.0.0.1:8000/v1/predict", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        commodity,
        mandi,
        use_learned: true
      }),
      cache: "no-store", 
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      throw new Error(`Failed to fetch prediction: ${res.statusText}`);
    }

    return res.json();
  } catch (error) {
    clearTimeout(timeoutId);
    console.error("API Fetch Error:", error);
    
    // Provide a graceful fallback to ensure the UI NEVER goes blank
    return {
      request_id: "fallback_id",
      commodity,
      mandi,
      prediction: { price_change_7d_pct: 0, confidence: 0.5, direction: "neutral" },
      attribution: { seasonality_pct: 0, arrival_pct: 0, external_pct: 0 },
      farmer_guidance: {
        decision: "WAIT",
        price_range: { min: 28, max: 32 },
        confidence_label: "Medium",
        risk_label: "Medium",
        explanation: ["Fallback mode activated due to network timeout."]
      }
    };
  }
}
