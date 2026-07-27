import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope } from "next/font/google";
import "./globals.css";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const publicBaseUrl =
  "https://rajshah4.github.io/openhands-agent-research-lab";
const title =
  "NeuroGolf with OpenHands | Reproducing a Kaggle multi-agent workflow";
const description =
  "How we used OpenHands to coordinate the 400-task NeuroGolf workload, compare deployment structures, preserve experiment history, and recover incomplete agent work.";

export const metadata: Metadata = {
  metadataBase: new URL(publicBaseUrl),
  title,
  description,
  icons: {
    icon: "favicon.svg",
    shortcut: "favicon.svg",
  },
  openGraph: {
    title,
    description,
    type: "website",
    images: [
      {
        url: `${publicBaseUrl}/og.png`,
        width: 1672,
        height: 941,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: [`${publicBaseUrl}/og.png`],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${plexMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
