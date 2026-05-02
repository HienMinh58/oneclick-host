"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* ── Navbar ─────────────────────────────── */}
      <header className="border-b border-border/40 backdrop-blur-sm bg-background/80 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center text-white font-bold text-sm">
              1
            </div>
            <span className="text-xl font-bold tracking-tight">
              OneClick<span className="text-violet-400">Host</span>
            </span>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <Link href="/register">
              <Button
                size="sm"
                className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500"
              >
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ───────────────────────────────── */}
      <main className="flex-1 flex items-center justify-center px-6">
        <div className="max-w-3xl text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 text-sm font-medium">
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
            Zero-config deployments
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight">
            Deploy your project
            <br />
            <span className="bg-gradient-to-r from-violet-400 via-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              in one click
            </span>
          </h1>

          <p className="text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Paste your GitHub URL. We detect the stack, build the Docker image,
            and deploy it — all automatically. Built for students and small teams.
          </p>

          <div className="flex items-center justify-center gap-4 pt-2">
            <Link href="/register">
              <Button
                size="lg"
                className="bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-base px-8 h-12"
              >
                Start Deploying →
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="outline" size="lg" className="text-base px-8 h-12">
                Sign In
              </Button>
            </Link>
          </div>

          {/* ── Stack badges ──────────────────── */}
          <div className="flex items-center justify-center gap-3 pt-6 flex-wrap">
            {["React", "Next.js", "ASP.NET Core", "Spring Boot"].map(
              (stack) => (
                <span
                  key={stack}
                  className="px-3 py-1.5 rounded-lg bg-muted/50 border border-border/50 text-sm text-muted-foreground"
                >
                  {stack}
                </span>
              )
            )}
          </div>
        </div>
      </main>

      {/* ── Footer ─────────────────────────────── */}
      <footer className="border-t border-border/40 py-6">
        <p className="text-center text-sm text-muted-foreground">
          © 2026 OneClick-Host · Built for students, by students
        </p>
      </footer>
    </div>
  );
}
