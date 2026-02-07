import { TerminalSquare, Plus, Activity, Database, ChevronRight, BarChart3 } from "lucide-react";

const dummyWorkspaces = [
  { id: "ws-1", name: "Enterprise Sales Analysis", dataset: "q4_enterprise_sales.parquet", lastActive: "10 mins ago", queries: 34, trend: "up" },
  { id: "ws-2", name: "Marketing ROI Dashboard", dataset: "marketing_spend_2025.xlsx", lastActive: "5 hours ago", queries: 12, trend: "neutral" },
  { id: "ws-3", name: "Predictive Churn Model", dataset: "user_churn_events_nov.csv", lastActive: "2 days ago", queries: 89, trend: "up" },
];

export default function Workspaces() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header & CTA */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Workspaces</h1>
          <p className="text-gray-400 mt-1">Chat with your datasets and build automated visual reports.</p>
        </div>
        <button className="flex items-center gap-2 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg shadow-[0_0_15px_rgba(59,130,246,0.4)] transition-all hover:scale-105">
          <Plus className="w-5 h-5" />
          New Workspace
        </button>
      </div>

      {/* Workspaces Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {dummyWorkspaces.map((ws) => (
          <div 
            key={ws.id} 
            className="group relative bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl p-6 hover:bg-white/5 hover:border-blue-500/30 transition-all cursor-pointer overflow-hidden shadow-lg hover:shadow-[0_0_30px_rgba(59,130,246,0.15)]"
          >
            {/* Subtle Top Gradient Line */}
            <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-blue-500 to-violet-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
                <TerminalSquare className="w-5 h-5" />
              </div>
              <span className="text-xs font-medium text-gray-500 flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-emerald-500" />
                {ws.lastActive}
              </span>
            </div>
            
            <h3 className="text-lg font-semibold text-gray-100 group-hover:text-blue-400 transition-colors">
              {ws.name}
            </h3>
            
            <div className="mt-4 space-y-3">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Database className="w-4 h-4 text-gray-500" />
                <span className="truncate">{ws.dataset}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <BarChart3 className="w-4 h-4 text-gray-500" />
                <span>{ws.queries} total queries run</span>
              </div>
            </div>

            {/* Bottom action row */}
            <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
              <span className="text-sm font-medium text-gray-400 group-hover:text-gray-200 transition-colors">
                Open Workspace
              </span>
              <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-blue-500/20 group-hover:text-blue-400 transition-all">
                <ChevronRight className="w-4 h-4" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}