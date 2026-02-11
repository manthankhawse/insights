import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Play, Square, Plus, Trash2, ChevronUp, ChevronDown,
  ArrowLeft, Loader2, Database, FileText,
  AlignLeft, LayoutDashboard, Table2, TerminalSquare,
  Pin, Code, Copy, RotateCcw
} from "lucide-react";
import VegaChart, { type ChartUIBlock } from "../components/VegaChart";

// ─── TYPES ────────────────────────────────────────────────────────────────────
type Tab = 'notebook' | 'explorer' | 'dashboard';
type CellType = 'code' | 'markdown';
type CellStatus = 'idle' | 'running' | 'done' | 'error';

type UIBlock =
  | { type: "markdown"; content: string }
  | { type: "code"; language: string; content: string }
  | { type: "table"; columns: string[]; data: any[]; warning?: string | null }
  | { type: "chart"; };

type Cell = {
  id: string;
  type: CellType;
  input: string;
  execCount: number | null;
  status: CellStatus;
  blocks: UIBlock[];
  isEditing: boolean;
  collapsed: boolean;
};

const INGEST_API_URL = "http://127.0.0.1:8000/api/v1";
const CHAT_API_URL   = "http://127.0.0.1:8000/api/v1/chat";

let globalExecCounter = 1;

function makeCell(type: CellType = 'code'): Cell {
  return {
    id: crypto.randomUUID(),
    type,
    input: '',
    execCount: null,
    status: 'idle',
    blocks: [],
    isEditing: type === 'markdown',
    collapsed: false,
  };
}

// ─── NOTEBOOK KERNEL STATUS ───────────────────────────────────────────────────
function KernelDot({ status }: { status: 'idle' | 'busy' }) {
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-gray-400 font-mono select-none">
      <span className={`w-2 h-2 rounded-full ${status === 'idle' ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`} />
      {status === 'idle' ? 'Kernel idle' : 'Kernel busy'}
    </span>
  );
}

// ─── CELL EXECUTION GUTTER ────────────────────────────────────────────────────
// function ExecLabel({ count, status }: { count: number | null; status: CellStatus }) {
//   return (
//     <div className="w-[52px] shrink-0 pt-[10px] pr-2 text-right font-mono text-[12px] text-gray-500 select-none leading-none">
//       {status === 'running'
//         ? <span className="text-blue-400 animate-pulse">[ * ]</span>
//         : count !== null
//           ? <span>[{count}]</span>
//           : <span className="opacity-0">[ ]</span>
//       }
//     </div>
//   );
// }

// ─── MARKDOWN RENDERER (lightweight) ─────────────────────────────────────────
function MdRender({ content }: { content: string }) {
  // Very simple: headings, bold, inline code, paragraph
  const lines = content.split('\n');
  return (
    <div className="text-[13.5px] leading-relaxed text-gray-200 space-y-1 select-text">
      {lines.map((line, i) => {
        if (/^### /.test(line)) return <h3 key={i} className="text-base font-semibold text-white mt-3">{line.slice(4)}</h3>;
        if (/^## /.test(line))  return <h2 key={i} className="text-lg font-bold text-white mt-4">{line.slice(3)}</h2>;
        if (/^# /.test(line))   return <h1 key={i} className="text-xl font-extrabold text-white mt-4">{line.slice(2)}</h1>;
        if (line.trim() === '')  return <br key={i} />;
        // inline bold & code
        const parts = line.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
        return (
          <p key={i}>
            {parts.map((p, j) => {
              if (/^`[^`]+`$/.test(p)) return <code key={j} className="px-1.5 py-0.5 rounded bg-white/10 font-mono text-[12px] text-emerald-300">{p.slice(1,-1)}</code>;
              if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={j} className="text-white font-semibold">{p.slice(2,-2)}</strong>;
              return <span key={j}>{p}</span>;
            })}
          </p>
        );
      })}
    </div>
  );
}

// ─── TABLE BLOCK ─────────────────────────────────────────────────────────────
function TableBlock({ block }: { block: Extract<UIBlock, {type:'table'}> }) {
  return (
    <div className="overflow-x-auto">
      {block.warning && (
        <div className="mx-3 mt-3 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded text-xs text-amber-400 font-mono">
          ⚠ {block.warning}
        </div>
      )}
      <table className="w-full text-left text-[12.5px] font-mono">
        <thead>
          <tr className="border-b border-white/10">
            <th className="w-10 px-3 py-2.5 text-gray-600 text-right text-[11px]">#</th>
            {block.columns.map(c => (
              <th key={c} className="px-3 py-2.5 text-gray-400 font-medium whitespace-nowrap">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.data.map((row, i) => (
            <tr key={i} className={`border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors`}>
              <td className="px-3 py-2 text-gray-600 text-right text-[11px]">{i}</td>
              {block.columns.map(c => (
                <td key={c} className="px-3 py-2 whitespace-nowrap text-gray-300">
                  {row[c] !== null && row[c] !== undefined
                    ? <span>{String(row[c])}</span>
                    : <span className="text-gray-600 italic">NaN</span>}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-3 py-2 text-[11px] text-gray-600 font-mono border-t border-white/[0.04]">
        {block.data.length} rows × {block.columns.length} columns
      </div>
    </div>
  );
}

// ─── SINGLE CELL ─────────────────────────────────────────────────────────────
function NotebookCell({
  cell,
  index,
  total,
  onUpdate,
  onRun,
  onDelete,
  onMove,
  onAddBelow,
  isKernelBusy,
}: {
  cell: Cell;
  index: number;
  total: number;
  onUpdate: (id: string, patch: Partial<Cell>) => void;
  onRun: (id: string) => void;
  onDelete: (id: string) => void;
  onMove: (id: string, dir: 'up' | 'down') => void;
  onAddBelow: (id: string, type: CellType) => void;
  isKernelBusy: boolean;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [focused, setFocused] = useState(false);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.max(ta.scrollHeight, 52)}px`;
  }, [cell.input]);

  const isRunning = cell.status === 'running';
  const hasOutput = cell.blocks.length > 0;

  return (
    <div className="relative group/cell">
      {/* Cell container */}
      <div className={`flex items-start transition-all duration-150 ${focused ? 'opacity-100' : 'opacity-90 hover:opacity-100'}`}>
        
        {/* Left gutter: exec count + run button */}
        <div className="flex flex-col items-end shrink-0 w-[52px] pt-[6px] pr-1">
          <button
            onClick={() => onRun(cell.id)}
            disabled={isKernelBusy && !isRunning}
            className={`w-7 h-7 flex items-center justify-center rounded transition-all ${
              isRunning
                ? 'text-amber-400 hover:text-amber-300'
                : focused
                  ? 'text-blue-400 hover:text-blue-300 hover:bg-blue-500/10'
                  : 'text-gray-600 hover:text-gray-400'
            }`}
            title="Run cell (Shift+Enter)"
          >
            {isRunning
              ? <Square className="w-3.5 h-3.5" />
              : <Play className="w-3.5 h-3.5 fill-current" />
            }
          </button>
          <span className="font-mono text-[11px] text-gray-600 mt-0.5 select-none">
            {isRunning ? <span className="text-amber-400 animate-pulse">*</span> : cell.execCount !== null ? cell.execCount : ''}
          </span>
        </div>

        {/* Cell body */}
        <div className={`flex-1 min-w-0 rounded-[4px] border transition-all duration-100 ${
          focused
            ? cell.type === 'code'
              ? 'border-blue-500/60 bg-[#1a1a1a] shadow-[0_0_0_1px_rgba(59,130,246,0.15)]'
              : 'border-violet-500/50 bg-[#1a1a1a]'
            : 'border-white/[0.07] bg-[#161616] hover:border-white/[0.12]'
        }`}>
          
          {/* Cell type badge */}
          {focused && (
            <div className="absolute -top-0 left-[60px] flex items-center gap-1 z-10">
              <span className={`text-[9px] font-mono uppercase tracking-widest px-2 py-0.5 rounded-t ${
                cell.type === 'code' ? 'text-blue-400/70' : 'text-violet-400/70'
              }`}>
                {cell.type === 'code' ? '⬡ code' : '⬡ markdown'}
              </span>
            </div>
          )}

          {/* INPUT AREA */}
          {cell.type === 'code' ? (
            <textarea
              ref={textareaRef}
              value={cell.input}
              onChange={e => onUpdate(cell.id, { input: e.target.value })}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              onKeyDown={e => {
                if ((e.shiftKey || e.ctrlKey) && e.key === 'Enter') {
                  e.preventDefault();
                  onRun(cell.id);
                }
              }}
              spellCheck={false}
              placeholder="# Write a query or question for the AI agent..."
              className="w-full bg-transparent text-[13px] font-mono text-[#d4d4d4] leading-6 px-4 py-3 focus:outline-none resize-none placeholder-gray-700 caret-blue-400"
              style={{ minHeight: '52px' }}
            />
          ) : cell.isEditing ? (
            <div>
              <textarea
                autoFocus
                value={cell.input}
                onChange={e => onUpdate(cell.id, { input: e.target.value })}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                onKeyDown={e => {
                  if (e.key === 'Escape') {
                    onUpdate(cell.id, { isEditing: false });
                    setFocused(false);
                  }
                  if ((e.shiftKey || e.ctrlKey) && e.key === 'Enter') {
                    e.preventDefault();
                    onRun(cell.id);
                  }
                }}
                placeholder="Write markdown notes..."
                className="w-full bg-transparent text-[13px] text-gray-300 leading-6 px-4 py-3 focus:outline-none resize-none placeholder-gray-700 caret-violet-400 font-sans"
                style={{ minHeight: '52px' }}
              />
              <div className="flex justify-end gap-2 px-3 pb-2">
                <button
                  onClick={() => { onRun(cell.id); setFocused(false); }}
                  className="px-3 py-1 bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium rounded transition-colors"
                >
                  Render (Shift+Enter)
                </button>
              </div>
            </div>
          ) : (
            <div
              className="px-5 py-4 cursor-text"
              onDoubleClick={() => { onUpdate(cell.id, { isEditing: true }); setFocused(true); }}
              onClick={() => setFocused(true)}
            >
              {cell.input
                ? <MdRender content={cell.input} />
                : <span className="text-gray-600 italic text-[13px]">Double-click to edit markdown...</span>
              }
            </div>
          )}

          {/* OUTPUT AREA */}
          {hasOutput && (
            <div className="border-t border-white/[0.06]">
              {cell.blocks.map((block, idx) => (
                <div key={idx} className="relative group/block">
                  {block.type === 'code' && (
                    <div>
                      <div className="flex items-center justify-between px-4 py-1.5 bg-white/[0.02] border-b border-white/[0.04]">
                        <span className="text-[10px] font-mono text-gray-600 uppercase tracking-wider">{block.language}</span>
                        <button
                          onClick={() => navigator.clipboard.writeText(block.content)}
                          className="p-1 text-gray-600 hover:text-gray-400 transition-colors"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                      </div>
                      <pre className="px-4 py-3 text-[12.5px] font-mono text-emerald-400/90 overflow-x-auto leading-5 bg-black/20">
                        <code>{block.content}</code>
                      </pre>
                    </div>
                  )}
                  {block.type === 'table' && <TableBlock block={block} />}
                  {block.type === 'markdown' && (
                    <div className="px-4 py-3">
                      <MdRender content={block.content} />
                    </div>
                  )}

                  {block.type === 'chart' && <VegaChart block={block as ChartUIBlock} />}

                  {/* Pin to dashboard */}
                  <button
                    className="absolute top-2 right-2 p-1 bg-black/60 text-gray-600 hover:text-blue-400 rounded opacity-0 group-hover/block:opacity-100 transition-all"
                    title="Pin to Dashboard"
                  >
                    <Pin className="w-3 h-3" />
                  </button>
                </div>
              ))}

              {cell.status === 'running' && (
                <div className="flex items-center gap-2.5 px-4 py-3 text-[12px] text-gray-500 font-mono">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
                  <span>Running agent...</span>
                </div>
              )}
            </div>
          )}
          {cell.status === 'running' && !hasOutput && (
            <div className="flex items-center gap-2.5 px-4 py-3 border-t border-white/[0.06] text-[12px] text-gray-500 font-mono">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
              <span>Executing LangGraph workflow...</span>
            </div>
          )}
        </div>

        {/* Right toolbar (visible on hover/focus) */}
        <div className={`flex flex-col items-center gap-1 pl-1.5 pt-1 transition-opacity ${focused ? 'opacity-100' : 'opacity-0 group-hover/cell:opacity-100'}`}>
          <button onClick={() => onMove(cell.id, 'up')} disabled={index === 0} className="p-1 text-gray-600 hover:text-gray-300 disabled:opacity-20 transition-colors" title="Move up">
            <ChevronUp className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => onMove(cell.id, 'down')} disabled={index === total - 1} className="p-1 text-gray-600 hover:text-gray-300 disabled:opacity-20 transition-colors" title="Move down">
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
          <button onClick={() => onDelete(cell.id)} className="p-1 text-gray-600 hover:text-red-400 transition-colors mt-1" title="Delete cell">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Add cell bar (on hover between cells) */}
      <div className="h-3 flex items-center justify-center opacity-0 group-hover/cell:opacity-100 transition-opacity my-0.5">
        <div className="flex items-center gap-1 bg-[#1a1a1a] border border-white/10 rounded-full px-2 py-0.5 shadow-lg">
          <button
            onClick={() => onAddBelow(cell.id, 'code')}
            className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-gray-400 hover:text-blue-400 font-mono transition-colors"
          >
            <Code className="w-2.5 h-2.5" /> + Code
          </button>
          <div className="w-px h-3 bg-white/10" />
          <button
            onClick={() => onAddBelow(cell.id, 'markdown')}
            className="flex items-center gap-1 px-2 py-0.5 text-[10px] text-gray-400 hover:text-violet-400 font-mono transition-colors"
          >
            <AlignLeft className="w-2.5 h-2.5" /> + Markdown
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
export default function DataSourceNotebook() {
  const { id } = useParams();
  const [activeTab, setActiveTab] = useState<Tab>('notebook');
  const [cells, setCells] = useState<Cell[]>([makeCell('code'), makeCell('markdown')]);
  const [kernelBusy, setKernelBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [cells.length]);

  const { data: source, isLoading } = useQuery({
    queryKey: ['dataSource', id],
    queryFn: async () => {
      const res = await fetch(`${INGEST_API_URL}/data/${id}`);
      if (!res.ok) throw new Error('Failed');
      return res.json();
    },
    enabled: !!id,
  });

  const chatMutation = useMutation({
    mutationFn: async (message: string) => {
      const res = await fetch(`${CHAT_API_URL}/${id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) throw new Error('Agent error');
      return res.json();
    },
  });

  const updateCell = useCallback((id: string, patch: Partial<Cell>) => {
    setCells(prev => prev.map(c => c.id === id ? { ...c, ...patch } : c));
  }, []);

  const runCell = useCallback((cellId: string) => {
    const cell = cells.find(c => c.id === cellId);
    if (!cell || !cell.input.trim() || kernelBusy) return;

    if (cell.type === 'markdown') {
      updateCell(cellId, { isEditing: false, status: 'done' });
      return;
    }

    // Code cell → run agent
    const execCount = globalExecCounter++;
    setKernelBusy(true);
    updateCell(cellId, { status: 'running', execCount, blocks: [] });

    chatMutation.mutate(cell.input, {
      onSuccess: (data) => {
        updateCell(cellId, { status: 'done', blocks: data.blocks ?? [] });
        setKernelBusy(false);
      },
      onError: (err: any) => {
        updateCell(cellId, {
          status: 'error',
          blocks: [{ type: 'markdown', content: `❌ **Error:** ${err.message}` }],
        });
        setKernelBusy(false);
      },
    });
  }, [cells, kernelBusy, chatMutation, updateCell]);

  const deleteCell = useCallback((id: string) => {
    setCells(prev => prev.length > 1 ? prev.filter(c => c.id !== id) : prev);
  }, []);

  const moveCell = useCallback((id: string, dir: 'up' | 'down') => {
    setCells(prev => {
      const idx = prev.findIndex(c => c.id === id);
      if (idx < 0) return prev;
      const next = [...prev];
      const swap = dir === 'up' ? idx - 1 : idx + 1;
      if (swap < 0 || swap >= next.length) return prev;
      [next[idx], next[swap]] = [next[swap], next[idx]];
      return next;
    });
  }, []);

  const addCellBelow = useCallback((id: string, type: CellType) => {
    setCells(prev => {
      const idx = prev.findIndex(c => c.id === id);
      if (idx < 0) return prev;
      const next = [...prev];
      next.splice(idx + 1, 0, makeCell(type));
      return next;
    });
  }, []);

  const addCellAtEnd = (type: CellType) => {
    setCells(prev => [...prev, makeCell(type)]);
  };

  const runAll = () => {
    cells.filter(c => c.type === 'code' && c.input.trim()).forEach(c => runCell(c.id));
  };

  if (isLoading) return (
    <div className="flex items-center justify-center h-screen bg-[#111111]">
      <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
    </div>
  );

  return (
    <div className="flex flex-col h-screen bg-[#111111] overflow-hidden font-sans">
      {/* ── MENUBAR ─────────────────────────────────────────── */}
      <div className="h-[38px] bg-[#1a1a1a] border-b border-white/[0.07] flex items-center px-3 gap-1 shrink-0 z-20">
        <Link to="/datasources" className="p-1.5 text-gray-500 hover:text-white hover:bg-white/[0.07] rounded transition-colors mr-1">
          <ArrowLeft className="w-4 h-4" />
        </Link>

        {/* Dataset name */}
        <div className="flex items-center gap-2 px-2 py-1 rounded hover:bg-white/[0.05] cursor-default">
          <div className={`w-5 h-5 rounded flex items-center justify-center text-[10px] ${source?.source_type?.includes('db') ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'}`}>
            {source?.source_type?.includes('db') ? <Database className="w-3 h-3" /> : <FileText className="w-3 h-3" />}
          </div>
          <span className="text-[13px] font-medium text-gray-200 max-w-[200px] truncate">
            {source?.dataset_name || 'Untitled Notebook'}
          </span>
        </div>

        <div className="h-4 w-px bg-white/10 mx-1" />

        {/* Menu items */}
        {['File', 'Edit', 'View', 'Run', 'Kernel'].map(m => (
          <button key={m} className="px-2.5 py-1 text-[12px] text-gray-400 hover:text-white hover:bg-white/[0.07] rounded transition-colors">
            {m}
          </button>
        ))}

        <div className="flex-1" />
        <KernelDot status={kernelBusy ? 'busy' : 'idle'} />
      </div>

      {/* ── TOOLBAR ─────────────────────────────────────────── */}
      <div className="h-[42px] bg-[#161616] border-b border-white/[0.07] flex items-center px-4 gap-2 shrink-0 z-10">
        {/* Run all */}
        <button
          onClick={runAll}
          disabled={kernelBusy}
          className="flex items-center gap-1.5 px-3 h-7 bg-[#2a2a2a] hover:bg-[#333] disabled:opacity-40 text-gray-200 text-[12px] font-medium rounded border border-white/[0.08] transition-colors"
        >
          <Play className="w-3 h-3 fill-current text-blue-400" /> Run All
        </button>
        <button
          onClick={() => setCells(prev => prev.map(c => ({ ...c, blocks: [], status: 'idle', execCount: null })))}
          className="flex items-center gap-1.5 px-3 h-7 bg-[#2a2a2a] hover:bg-[#333] text-gray-200 text-[12px] font-medium rounded border border-white/[0.08] transition-colors"
        >
          <RotateCcw className="w-3 h-3 text-gray-400" /> Clear Outputs
        </button>

        <div className="h-5 w-px bg-white/[0.07] mx-1" />

        {/* Add cell buttons */}
        <button
          onClick={() => addCellAtEnd('code')}
          className="flex items-center gap-1.5 px-3 h-7 bg-[#2a2a2a] hover:bg-[#333] text-gray-200 text-[12px] font-medium rounded border border-white/[0.08] transition-colors"
        >
          <Plus className="w-3 h-3" /><Code className="w-3 h-3 text-blue-400" /> Code
        </button>
        <button
          onClick={() => addCellAtEnd('markdown')}
          className="flex items-center gap-1.5 px-3 h-7 bg-[#2a2a2a] hover:bg-[#333] text-gray-200 text-[12px] font-medium rounded border border-white/[0.08] transition-colors"
        >
          <Plus className="w-3 h-3" /><AlignLeft className="w-3 h-3 text-violet-400" /> Markdown
        </button>

        <div className="flex-1" />

        {/* Tabs */}
        <div className="flex bg-[#2a2a2a] border border-white/[0.08] rounded overflow-hidden">
          {([
            ['notebook', TerminalSquare, 'Notebook'],
            ['explorer', Table2,        'Explorer'],
            ['dashboard', LayoutDashboard, 'Dashboard'],
          ] as const).map(([tab, Icon, label]) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-1.5 px-3 h-7 text-[12px] font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-[#3a3a3a] text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-[#333]'
              }`}
            >
              <Icon className="w-3.5 h-3.5" /> {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── MAIN CONTENT ────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto bg-[#111111]">

        {/* ======= NOTEBOOK TAB ======= */}
        {activeTab === 'notebook' && (
          <div className="max-w-[900px] mx-auto py-6 px-4 space-y-0.5 pb-24">
            {cells.map((cell, idx) => (
              <NotebookCell
                key={cell.id}
                cell={cell}
                index={idx}
                total={cells.length}
                onUpdate={updateCell}
                onRun={runCell}
                onDelete={deleteCell}
                onMove={moveCell}
                onAddBelow={addCellBelow}
                isKernelBusy={kernelBusy}
              />
            ))}

            {/* Bottom add buttons */}
            <div className="pt-4 flex items-center gap-3 pl-[52px]">
              <button
                onClick={() => addCellAtEnd('code')}
                className="flex items-center gap-2 px-4 py-1.5 border border-dashed border-white/10 hover:border-blue-500/40 text-gray-600 hover:text-blue-400 text-[12px] font-mono rounded transition-all"
              >
                <Plus className="w-3.5 h-3.5" /> Code cell
              </button>
              <button
                onClick={() => addCellAtEnd('markdown')}
                className="flex items-center gap-2 px-4 py-1.5 border border-dashed border-white/10 hover:border-violet-500/40 text-gray-600 hover:text-violet-400 text-[12px] font-mono rounded transition-all"
              >
                <Plus className="w-3.5 h-3.5" /> Markdown cell
              </button>
            </div>
            <div ref={endRef} />
          </div>
        )}

        {/* ======= EXPLORER TAB ======= */}
        {activeTab === 'explorer' && (
          <div className="max-w-5xl mx-auto p-8 animate-in fade-in duration-200">
            <h2 className="text-lg font-semibold text-white mb-1">Schema Explorer</h2>
            <p className="text-[13px] text-gray-500 mb-6 font-mono">Inferred schema from uploaded dataset</p>
            <div className="bg-[#161616] border border-white/[0.07] rounded-lg overflow-hidden">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="border-b border-white/[0.07] bg-white/[0.02]">
                    {['Column', 'Type', 'Non-Null', 'Sample'].map(h => (
                      <th key={h} className="px-5 py-3 text-[11px] uppercase tracking-wider text-gray-500 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.04]">
                  {[
                    { col: 'filename', type: 'VARCHAR', nn: '100%', sample: '1-a_h.wav' },
                    { col: 'mfcc_0', type: 'DOUBLE', nn: '100%', sample: '-234.47577' },
                    { col: 'mfcc_1', type: 'DOUBLE', nn: '100%', sample: '42.706825' },
                    { col: 'label', type: 'VARCHAR', nn: '100%', sample: 'binary' },
                  ].map(row => (
                    <tr key={row.col} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-5 py-2.5 font-mono text-blue-400">{row.col}</td>
                      <td className="px-5 py-2.5"><span className="px-2 py-0.5 bg-white/[0.06] rounded text-[11px] font-mono text-gray-400">{row.type}</span></td>
                      <td className="px-5 py-2.5 text-gray-500 font-mono">{row.nn}</td>
                      <td className="px-5 py-2.5 text-gray-500 font-mono">{row.sample}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ======= DASHBOARD TAB ======= */}
        {activeTab === 'dashboard' && (
          <div className="max-w-6xl mx-auto p-8 animate-in fade-in duration-200">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white mb-0.5">Dashboard</h2>
                <p className="text-[13px] text-gray-500">Pinned outputs from the Notebook</p>
              </div>
              <button className="px-4 py-1.5 bg-[#2a2a2a] hover:bg-[#333] text-gray-300 text-[12px] font-medium rounded border border-white/[0.08] transition-colors">
                Export PDF
              </button>
            </div>
            <div className="border-2 border-dashed border-white/[0.06] rounded-xl py-20 flex flex-col items-center justify-center text-center">
              <Pin className="w-8 h-8 text-gray-700 mb-3" />
              <p className="text-[13px] text-gray-500">No outputs pinned yet</p>
              <p className="text-[12px] text-gray-600 mt-1">Hover over a cell output and click the pin icon</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}