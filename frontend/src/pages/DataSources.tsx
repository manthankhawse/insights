import { UploadCloud, FileText, Database, MoreHorizontal, Clock, CheckCircle2 } from "lucide-react";

const dummySources = [
  { id: "1", name: "q4_enterprise_sales.parquet", type: "Parquet", rows: "2.4M", size: "145 MB", uploaded: "2 hours ago", status: "Ready" },
  { id: "2", name: "user_churn_events_nov.csv", type: "CSV", rows: "850K", size: "82 MB", uploaded: "1 day ago", status: "Ready" },
  { id: "3", name: "marketing_spend_2025.xlsx", type: "Excel", rows: "12K", size: "4 MB", uploaded: "3 days ago", status: "Ready" },
];

export default function DataSources() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">Data Sources</h1>
        <p className="text-gray-400 mt-1">Upload and manage your raw datasets before feeding them to the agent.</p>
      </div>

      {/* Upload Zone */}
      <div className="relative group rounded-2xl border-2 border-dashed border-white/10 bg-white/5 hover:bg-white/[0.07] hover:border-blue-500/50 transition-all p-10 text-center cursor-pointer overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="relative z-10 flex flex-col items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:scale-110 group-hover:bg-blue-500/20 transition-all shadow-[0_0_15px_rgba(59,130,246,0)] group-hover:shadow-[0_0_30px_rgba(59,130,246,0.3)]">
            <UploadCloud className="w-8 h-8" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-200">Drag & drop your files here</h3>
            <p className="text-sm text-gray-500 mt-1">Supports .CSV, .XLSX, and .PARQUET up to 5GB</p>
          </div>
          <button className="mt-2 px-6 py-2.5 bg-white/10 hover:bg-white/20 text-white text-sm font-medium rounded-lg transition-colors border border-white/5">
            Browse Files
          </button>
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-white/5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-blue-400" />
            Connected Datasets
          </h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-gray-400 font-medium border-b border-white/10">
              <tr>
                <th className="px-6 py-4">Dataset Name</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4">Rows</th>
                <th className="px-6 py-4">Size</th>
                <th className="px-6 py-4">Uploaded</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-gray-300">
              {dummySources.map((source) => (
                <tr key={source.id} className="hover:bg-white/5 transition-colors group">
                  <td className="px-6 py-4 flex items-center gap-3">
                    <FileText className="w-4 h-4 text-gray-500 group-hover:text-blue-400 transition-colors" />
                    <span className="font-medium text-gray-200">{source.name}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="px-2.5 py-1 rounded-md bg-white/10 text-xs font-medium text-gray-300 border border-white/5">
                      {source.type}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-gray-400">{source.rows}</td>
                  <td className="px-6 py-4 font-mono text-gray-400">{source.size}</td>
                  <td className="px-6 py-4 flex items-center gap-2 text-gray-500">
                    <Clock className="w-3.5 h-3.5" />
                    {source.uploaded}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-emerald-400">
                      <CheckCircle2 className="w-4 h-4" />
                      <span className="text-xs font-medium">{source.status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-1.5 text-gray-500 hover:text-white hover:bg-white/10 rounded-md transition-colors">
                      <MoreHorizontal className="w-5 h-5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}