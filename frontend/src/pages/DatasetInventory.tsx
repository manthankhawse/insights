import { useState, useRef } from 'react';
import useDatasets from '../hooks/useDatasets';
import useUploadDataset from '../hooks/useUploadDataset';
import { type Dataset} from '../types';
import { Upload, CheckCircle, Loader2, FileText, Database, AlertCircle } from 'lucide-react';
import ConnectDbModal from '../components/ConnectDB';
import DataPreview from '../components/DataPreview';

export default function DatasetInventory() {
  const [isDbModalOpen, setIsDbModalOpen] = useState(false);
  const { data: datasets, isLoading, isError } = useDatasets();
  const uploadMutation = useUploadDataset();
  const [previewId, setPreviewId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>)=>{
    const file = e.target.files?.[0];
    if(file){
        uploadMutation.mutate(file);
    }
  }

  if (isLoading) return <div className="flex justify-center p-12"><Loader2 className="animate-spin text-blue-600" /></div>;
  if (isError) return <div className="p-12 text-red-500 flex items-center"><AlertCircle className="mr-2"/> Failed to load datasets</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Data Assets</h1>
        {/* Hidden Input */}
        <input 
          type="file" 
          ref={fileInputRef} 
          className="hidden" 
          onChange={handleFileChange}
          accept=".csv,.xlsx,.xls,.parquet"
        />

        <button 
            onClick={() => setIsDbModalOpen(true)}
            className="bg-white border border-slate-200 text-slate-700 px-5 py-2.5 rounded-xl font-medium shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2"
          >
            <Database size={20} /> Connect DB
          </button>

        <button 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white px-5 py-2.5 rounded-xl font-medium shadow-lg shadow-blue-200 transition-all active:scale-95 flex items-center gap-2"
        >
          {uploadMutation.isPending ? <Loader2 className="animate-spin" size={20} /> : <Upload size={20} />}
          {uploadMutation.isPending ? 'Uploading...' : 'Import Data'}
        </button>
      </div>

      <ConnectDbModal isOpen={isDbModalOpen} onClose={() => setIsDbModalOpen(false)} />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {datasets?.map((ds: Dataset) => (
          <DatasetCard key={ds.id} dataset={ds} onView={()=>setPreviewId(ds.id)}/>
        ))}
      </div>

      {previewId && (
      <DataPreview 
        datasetId={previewId} 
        onClose={() => setPreviewId(null)} 
      />
    )}
    </div>
  );
}

// Destructure with types
function DatasetCard({ dataset, onView }: { dataset: Dataset, onView : ()=>void }) {
  const isReady = dataset.status === 'completed';
  
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group">
      <div className="flex justify-between items-start mb-4">
        <div className={`p-3 rounded-lg ${dataset.source_id ? 'bg-indigo-50 text-indigo-600' : 'bg-emerald-50 text-emerald-600'}`}>
          {dataset.source_id ? <Database size={24}/> : <FileText size={24}/>}
        </div>
        {/* Use the isReady variable to satisfy the unused variable warning */}
        <StatusBadge status={dataset.status} />
        {isReady && <CheckCircle size={16} className="text-green-500 absolute top-4 right-4" />}
      </div>
      
      <h3 className="font-bold text-slate-800 text-lg mb-1 truncate">{dataset.display_name}</h3>
      <p className="text-slate-500 text-sm mb-4 capitalize">{dataset.source_type} • {dataset.row_count?.toLocaleString() || 0} rows</p>
      
      <button className="w-full py-2 bg-slate-50 hover:bg-slate-100 text-slate-600 rounded-lg text-sm font-semibold transition-colors border border-slate-100" onClick={onView}>
        View Details
      </button>
    </div>
  );
}

function StatusBadge({ status }: { status: Dataset['status'] }) {
  if (status === 'completed') return <span className="text-xs font-bold px-2.5 py-1 bg-green-100 text-green-700 rounded-full">Ready</span>;
  if (status === 'failed') return <span className="text-xs font-bold px-2.5 py-1 bg-red-100 text-red-700 rounded-full">Error</span>;
  return <span className="text-xs font-bold px-2.5 py-1 bg-blue-100 text-blue-700 rounded-full animate-pulse">Processing</span>;
}