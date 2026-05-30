import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FinSight — Bank Statement Intelligence Platform",
  description: "Enterprise-grade bank statement analysis. Extract transactions, detect risk, and generate underwriter-ready reports.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="glass sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between border-b border-[#1e2d45]">
          <div className="flex items-center gap-3">
            {/* Logo */}
            <div className="relative w-9 h-9">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center text-[#0a0f1e] font-black text-sm"
                style={{ background: "linear-gradient(135deg, #00d4aa 0%, #3b82f6 100%)" }}>
                FS
              </div>
              <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-[#00d4aa] rounded-full border-2 border-[#0a0f1e] animate-pulse-slow" />
            </div>
            <div>
              <span className="font-bold text-lg text-slate-100 tracking-tight">FinSight</span>
              <span className="text-slate-500 text-xs ml-1.5">BSA Platform</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="badge-teal">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00d4aa] mr-1.5 animate-pulse" />
              Live
            </span>
          </div>
        </nav>
        <main className="min-h-screen">{children}</main>
      </body>
    </html>
  );
}
