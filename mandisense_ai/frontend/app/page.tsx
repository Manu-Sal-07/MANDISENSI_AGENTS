import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { TrendingUp, Activity, BarChart3, Zap } from "lucide-react";
import { OpportunityGrid } from "@/components/home/OpportunityGrid";
import { SectionHeader } from "@/components/home/SectionHeader";
import { OpportunityData } from "@/components/home/OpportunityCard";

// Mock Data
const MOCK_OPPORTUNITIES: OpportunityData[] = [
  {
    id: "tomato",
    name: "Tomato",
    signal: "STRONG BUY",
    score: 8.7,
    change: 6.2,
    confidence: 0.72,
  },
  {
    id: "onion",
    name: "Onion",
    signal: "AVOID",
    score: 2.1,
    change: -4.5,
    confidence: 0.85,
  },
  {
    id: "potato",
    name: "Potato",
    signal: "HOLD",
    score: 5.5,
    change: 0.8,
    confidence: 0.45,
  },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-8 py-8 w-full">
      {/* Header Section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight text-foreground">
            MandiSense AI
          </h1>
          <p className="text-muted-foreground mt-1 text-lg">
            Multi-agent commodity trading intelligence.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="h-10">
            <BarChart3 className="mr-2 h-4 w-4" />
            Analytics
          </Button>
          <Button className="h-10">
            <Activity className="mr-2 h-4 w-4" />
            Live Market
          </Button>
        </div>
      </div>

      <Tabs defaultValue="opportunities" className="w-full">
        <TabsList className="mb-6 h-12 items-center px-2 bg-card border border-border/50">
          <TabsTrigger value="opportunities" className="text-base px-6">Top Opportunities</TabsTrigger>
          <TabsTrigger value="overview" className="text-base px-6">Market Overview</TabsTrigger>
          <TabsTrigger value="portfolio" className="text-base px-6">My Watchlist</TabsTrigger>
        </TabsList>

        <TabsContent value="opportunities" className="mt-0 outline-none">
          {/* TOP OPPORTUNITIES HERO SECTION */}
          <section className="mb-10">
            <SectionHeader 
              title="Top Opportunities Today" 
              description="AI-detected market inefficiencies based on seasonality, supply stress, and external factors."
              icon={Zap}
            />
            <OpportunityGrid opportunities={MOCK_OPPORTUNITIES} />
          </section>
        </TabsContent>

        <TabsContent value="overview" className="mt-0 outline-none space-y-8">
          <section>
            <SectionHeader title="Global Market State" icon={Activity} />
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <Card className="bg-card/60 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardDescription>Global Market Trend</CardDescription>
                  <CardTitle className="text-2xl flex items-center gap-2">
                    Bullish <TrendingUp className="h-5 w-5 text-emerald-500" />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">+2.4% aggregate shift in past 7 days</p>
                </CardContent>
              </Card>

              <Card className="bg-card/60 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardDescription>Active Alerts</CardDescription>
                  <CardTitle className="text-2xl">3 High Priority</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">Supply stress detected in Onion markets</p>
                </CardContent>
              </Card>

              <Card className="bg-card/60 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardDescription>System Status</CardDescription>
                  <CardTitle className="text-2xl text-emerald-500">Operational</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground">All agents running normally (Phase-2.5)</p>
                </CardContent>
              </Card>
            </div>
          </section>
        </TabsContent>
        
        <TabsContent value="portfolio" className="mt-0 outline-none">
           <section>
            <SectionHeader title="Your Watchlist" />
            <Card className="border-dashed h-[400px] flex items-center justify-center bg-transparent border-border/50">
              <div className="text-center">
                <p className="text-muted-foreground mb-4">You are not tracking any commodities yet.</p>
                <Button variant="outline">Browse Markets</Button>
              </div>
            </Card>
          </section>
        </TabsContent>
      </Tabs>
    </div>
  );
}
