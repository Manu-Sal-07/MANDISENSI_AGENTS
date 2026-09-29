export interface ParsedQuery {
  commodity: string;
  market: string;
  intent: string;
  quantity: string;
  horizon: string;
  tokens: string[];
}

export interface MockAnalysisResult {
  parsed: ParsedQuery;
  recommendation: string;
  expectedChange: string;
  confidence: number;
  dna: {
    arrival: number;
    seasonality: number;
    external: number;
  };
  details: { label: string; impact: string }[];
}

// Simple rule-based client-side NLP parser
export function parseQuery(queryText: string): ParsedQuery {
  const query = queryText.toLowerCase();

  // 1. Commodity
  let commodity = "Tomato";
  if (query.includes("onion")) commodity = "Onion";
  else if (query.includes("potato")) commodity = "Potato";
  else if (query.includes("chilli") || query.includes("chili")) commodity = "Chilli";

  // 2. Market
  let market = "Kolar";
  if (query.includes("bengaluru") || query.includes("bangalore")) market = "Bengaluru";
  else if (query.includes("hubli")) market = "Hubli";
  else if (query.includes("latur")) market = "Latur";
  else if (query.includes("pune")) market = "Pune";

  // 3. Intent
  let intent = "Sell";
  if (query.includes("hold")) intent = "Hold";
  else if (query.includes("buy")) intent = "Buy";
  else if (query.includes("increase") || query.includes("prices") || query.includes("outlook")) intent = "Trend";

  // 4. Quantity
  let quantity = "N/A";
  const qtyMatch = queryText.match(/(\d+)\s*(tons|ton|t|kg|bags|bag)/i);
  if (qtyMatch) {
    quantity = `${qtyMatch[1]} ${qtyMatch[2].charAt(0).toUpperCase() + qtyMatch[2].slice(1).toLowerCase()}`;
  }

  // 5. Horizon
  let horizon = "Today";
  if (query.includes("next week")) horizon = "Next Week";
  else if (query.includes("7 days") || query.includes("7 day")) horizon = "7 Days";
  else if (query.includes("month") || query.includes("30 days")) horizon = "30 Days";

  // Construct structured tokens for SVG packet animation routing
  const tokens = [commodity, market, intent];
  if (quantity !== "N/A") tokens.push(quantity);
  tokens.push(horizon);

  return {
    commodity,
    market,
    intent,
    quantity,
    horizon,
    tokens
  };
}

// Future integration hook: Can swap getMockAnalysis with getRealAnalysis(queryText)
export function getMockAnalysis(queryText: string): MockAnalysisResult {
  const parsed = parseQuery(queryText);

  // Deterministic mock datasets based on parsed commodity
  switch (parsed.commodity) {
    case "Onion":
      return {
        parsed,
        recommendation: "HOLD STOCK",
        expectedChange: "+11.8%",
        confidence: 78,
        dna: { arrival: 0.38, seasonality: 0.29, external: 0.33 },
        details: [
          { label: "Supply Stress Impact", impact: "+38%" },
          { label: "Festival Demand Impact", impact: "-5%" },
          { label: "Weather Outlook Impact", impact: "+12%" },
          { label: "Trend Cycle Consensus", impact: "+33%" }
        ]
      };
    case "Potato":
      return {
        parsed,
        recommendation: "WAIT & WATCH",
        expectedChange: "-1.4%",
        confidence: 72,
        dna: { arrival: 0.15, seasonality: 0.65, external: 0.20 },
        details: [
          { label: "Supply Stress Impact", impact: "-12%" },
          { label: "Festival Demand Impact", impact: "+22%" },
          { label: "Weather Outlook Impact", impact: "-8%" },
          { label: "Trend Cycle Consensus", impact: "+10%" }
        ]
      };
    case "Chilli":
      return {
        parsed,
        recommendation: "BUY/STRADDLE",
        expectedChange: "+4.7%",
        confidence: 65,
        dna: { arrival: 0.55, seasonality: 0.25, external: 0.20 },
        details: [
          { label: "Supply Stress Impact", impact: "+15%" },
          { label: "Festival Demand Impact", impact: "+20%" },
          { label: "Weather Outlook Impact", impact: "-10%" },
          { label: "Trend Cycle Consensus", impact: "+40%" }
        ]
      };
    case "Tomato":
    default:
      return {
        parsed,
        recommendation: "SELL TODAY",
        expectedChange: "+6.2%",
        confidence: 84,
        dna: { arrival: 0.46, seasonality: 0.38, external: 0.16 },
        details: [
          { label: "Supply Stress Impact", impact: "+24%" },
          { label: "Festival Demand Impact", impact: "+18%" },
          { label: "Weather Outlook Impact", impact: "+7%" },
          { label: "Trend Cycle Consensus", impact: "+35%" }
        ]
      };
  }
}
