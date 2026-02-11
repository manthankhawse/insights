/**
 * VegaChart.tsx
 *
 * Renders any Vega-Lite v5 spec returned by the agent's generate_visuals node.
 * Injects the row data as the "table" named dataset so the spec stays data-agnostic.
 *
 * Install: npm install react-vega vega vega-lite
 */

import { useRef, useEffect, useState } from "react";
import embed, { type Result } from "vega-embed";

// ─── TYPES ────────────────────────────────────────────────────────────────────
export type ChartUIBlock = {
  type: "chart";
  spec: Record<string, any>;       // Vega-Lite v5 spec (with "data": {"name": "table"})
  data: Record<string, any>[];     // Row data to bind as the "table" dataset
  row_count?: number;              // Total rows before capping (for the caption)
};

// ─── COMPONENT ────────────────────────────────────────────────────────────────
export default function VegaChart({ block }: { block: ChartUIBlock }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef      = useRef<Result | null>(null);
  const [error, setError]     = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!containerRef.current) return;

    // Clean up any previous view
    viewRef.current?.finalize();

    // Merge the data into the spec as a named data source
    const specWithData = {
      ...block.spec,
      data: { name: "table" },      // always override — LLM might inline data accidentally
    };

    embed(containerRef.current, specWithData, {
      actions: false,               // hide the Vega toolbar (download/edit links)
      renderer: "svg",
      theme: "dark",
      config: {
        // Belt-and-suspenders dark theme in case the LLM forgets to include config
        background: "#111111",
        view: { stroke: "transparent" },
        axis: {
          gridColor: "#2a2a2a",
          tickColor: "#3a3a3a",
          labelColor: "#9ca3af",
          titleColor: "#6b7280",
          domainColor: "#2a2a2a",
          labelFont: "monospace",
          titleFont: "monospace",
          labelFontSize: 11,
          titleFontSize: 11,
        },
        legend: {
          labelColor: "#9ca3af",
          titleColor: "#6b7280",
          labelFont: "monospace",
          titleFont: "monospace",
          labelFontSize: 11,
        },
        title: {
          color: "#d1d5db",
          font: "monospace",
          fontSize: 12,
        },
      },
    })
      .then((result) => {
        viewRef.current = result;

        // Inject the actual row data into the named "table" dataset
        result.view
          .change("table", result.view.changeset().insert(block.data).remove(() => false))
          .run();

        setLoading(false);
        setError(null);
      })
      .catch((err) => {
        console.error("[VegaChart] Embed failed:", err);
        setError(err?.message ?? "Failed to render chart");
        setLoading(false);
      });

    return () => {
      viewRef.current?.finalize();
    };
  }, [block.spec, block.data]);

  return (
    <div className="px-4 pt-4 pb-2">
      {/* Loading skeleton */}
      {loading && (
        <div className="h-[280px] w-full rounded bg-white/[0.03] animate-pulse flex items-center justify-center">
          <span className="text-[11px] font-mono text-gray-600">Rendering chart...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="h-[280px] w-full rounded border border-red-500/20 bg-red-500/5 flex flex-col items-center justify-center gap-2">
          <span className="text-[12px] font-mono text-red-400">Chart render failed</span>
          <span className="text-[11px] text-gray-600 max-w-sm text-center">{error}</span>
        </div>
      )}

      {/* The Vega-Lite chart — always mounted so embed() has a target */}
      <div
        ref={containerRef}
        className={`w-full transition-opacity duration-300 ${loading || error ? "opacity-0 h-0 overflow-hidden" : "opacity-100"}`}
      />

      {/* Row count caption */}
      {!loading && !error && block.row_count !== undefined && (
        <p className="mt-1.5 text-[10px] font-mono text-gray-600 text-right">
          {block.data.length < block.row_count
            ? `Showing ${block.data.length.toLocaleString()} of ${block.row_count.toLocaleString()} rows`
            : `${block.row_count.toLocaleString()} rows`}
        </p>
      )}
    </div>
  );
}