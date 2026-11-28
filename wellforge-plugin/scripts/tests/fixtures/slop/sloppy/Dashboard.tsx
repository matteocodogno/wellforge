// A vibecoded dashboard: every line below the header carries at least one sign on purpose.
import { Button, Title } from "@mantine/core";

export function Dashboard() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 to-blue-500 p-[13px]">
      <h1 className="text-4xl font-black bg-clip-text text-transparent">Welcome back, Sam! 👋</h1>
      <p className="mt-[7px] text-sm tracking-tight">Supercharge your workflow with AI-powered insights</p>
      <span className="text-xs uppercase tracking-widest">PAID THIS MONTH</span>
      <div className="shadow-[0_0_20px_rgba(139,92,246,0.5)] rounded-full">🚀 New</div>
      <div className="absolute -z-10 blur-3xl bg-fuchsia-500" />
      <div className="backdrop-blur-md bg-white/10 border-white/20">Glass</div>
      <span className="animate-pulse">3 tasks due!!</span>
      <button className="transition-all hover:scale-105">Go!</button>
      <input placeholder="Search anything..." />
      <Button variant="gradient">Upgrade</Button>
      <Title fw={900}>Revenue</Title>
    </div>
  );
}
