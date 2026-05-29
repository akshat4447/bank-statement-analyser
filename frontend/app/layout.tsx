import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Bank Statement Analyser | AI-Powered Financial Intelligence",
  description: "Upload your bank statement and get instant AI-powered financial analysis, risk scores, and insights.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-navy text-white px-6 py-3 flex items-center justify-between shadow-md">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-teal rounded-lg flex items-center justify-center font-bold text-sm">
              BSA
            </div>
            <span className="font-semibold text-lg">Bank Statement Analyser</span>
          </div>
          <span className="text-xs text-blue-200 bg-navy-light px-2 py-1 rounded-full">
            AI-Powered · Powered by Claude & Gemini
          </span>
        </nav>
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  );
}
