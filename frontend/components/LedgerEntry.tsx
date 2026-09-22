import type { Entry } from "@/lib/entry";

export function LedgerEntry({ entry, index }: { entry: Entry; index: number }) {
  return (
    <article className="border-b border-line py-6 first:pt-0 last:border-b-0">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-xs text-muted tabular-nums">
          {String(index + 1).padStart(2, "0")}
        </span>
        <p className="text-[17px] leading-snug text-paper">{entry.question}</p>
      </div>

      {entry.status === "pending" && (
        <p className="mt-3 ml-7 font-mono text-xs text-muted">running…</p>
      )}

      {entry.status === "error" && (
        <p className="mt-3 ml-7 text-sm text-danger">{entry.errorMessage}</p>
      )}

      {entry.status === "done" && entry.result && (
        <div className="mt-3 ml-7 space-y-3">
          <pre className="overflow-x-auto rounded border border-line bg-panel px-4 py-3 font-mono text-[13px] leading-relaxed text-paper/90">
            {entry.result.sql}
          </pre>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs">
            {entry.result.accepted ? (
              <span className="text-verified">validated · read-only</span>
            ) : (
              <span className="text-brass">blocked by guardrail</span>
            )}
            {entry.result.accepted && (
              <span className="text-muted">
                {entry.result.row_count} row{entry.result.row_count === 1 ? "" : "s"} ·{" "}
                {entry.result.elapsed_ms}ms
              </span>
            )}
            {!entry.result.accepted && entry.result.rejection_reason && (
              <span className="text-muted">{entry.result.rejection_reason}</span>
            )}
          </div>

          {entry.result.answer && (
            <p className="text-[15px] leading-relaxed text-paper/90">{entry.result.answer}</p>
          )}
        </div>
      )}
    </article>
  );
}
