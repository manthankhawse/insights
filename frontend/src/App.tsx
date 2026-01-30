import { useState } from 'react'
import { Database, BarChart3, Table } from 'lucide-react'
import DatasetInventory from './pages/DatasetInventory'

function App() {
  const [activeTab, setActiveTab] = useState('inventory')

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-6 text-2xl font-bold border-b border-slate-800 text-blue-400">
          Insights AI
        </div>
        <nav className="flex-1 p-4 space-y-2">
          <NavItem 
            icon={<Table size={20}/>} 
            label="Datasets" 
            active={activeTab === 'inventory'} 
            onClick={() => setActiveTab('inventory')}
          />
          <NavItem 
            icon={<BarChart3 size={20} />}
            label="Visualizations"
            active={activeTab === 'viz'} onClick={undefined}          />
          <NavItem 
            icon={<Database size={20}/>} 
            label="Connections" 
            active={activeTab === 'db'} onClick={undefined}
          />
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-8">
        {activeTab === 'inventory' && <DatasetInventory />}
      </main>
    </div>
  )
}
//@ts-ignore
function NavItem({ icon, label, active, onClick }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full flex items-center space-x-3 p-3 rounded-lg transition-colors ${
        active ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 text-slate-400'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
    </button>
  )
}

export default App