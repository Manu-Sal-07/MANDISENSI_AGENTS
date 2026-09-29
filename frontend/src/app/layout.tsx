import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk, JetBrains_Mono, Baloo_2, Baloo_Tamma_2 } from "next/font/google";
import "./globals.css";
import Providers from "./providers";
import TopBar from "@/components/TopBar";
import BottomNav from "@/components/BottomNav";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["500", "600", "700"],
});

// Baloo 2 is an Ek Type (Mumbai) family with a Devanagari companion:
// rounded, high x-height, and legible at large sizes on low-end screens in
// direct sunlight. It carries the farmer-facing surface, where the audience
// reads Hindi as readily as English. The trader surfaces keep Space Grotesk.
const baloo = Baloo_2({
  subsets: ["latin", "devanagari"],
  variable: "--font-farm",
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

// Baloo 2 has no Kannada glyphs at all — every tracked mandi is in
// Karnataka, and Kannada text (ProduceIcon, CallCard's verb, the Tools Hub)
// was rendering in whatever fallback font the browser picked, visually
// inconsistent with the rest of the farm surface. Baloo Tamma 2 is the same
// Ek Type family's Kannada-script sibling — same weight range, same
// rounded, high-x-height design language — so farm-display text reads as
// one typeface across scripts instead of two unrelated ones stitched
// together by script.
const balooKannada = Baloo_Tamma_2({
  subsets: ["kannada"],
  variable: "--font-farm-kn",
  display: "swap",
  weight: ["400", "500", "600", "700", "800"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "MandiSense AI | Intelligence Dashboard",
  description: "Advanced multi-agent commodity trading intelligence.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#05070c" },
    { media: "(prefers-color-scheme: light)", color: "#f7f8fa" },
  ],
};

// Runs before hydration so the correct theme class is present on first
// paint — eliminates the light-theme flash that would otherwise show for a
// frame while ThemeProvider's effect resolves localStorage.
const themeInitScript = `
(function () {
  try {
    var stored = localStorage.getItem('theme');
    var theme = stored === 'light' ? 'light' : 'dark';
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.documentElement.style.colorScheme = theme;
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${spaceGrotesk.variable} ${jetbrainsMono.variable} ${baloo.variable} ${balooKannada.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="font-sans antialiased min-h-screen bg-background text-foreground selection:bg-accent/25 selection:text-foreground">
        <Providers>
          <div className="relative flex min-h-screen flex-col">
            <TopBar />
            <main className="flex-1">{children}</main>
            <BottomNav />
          </div>
        </Providers>
      </body>
    </html>
  );
}
