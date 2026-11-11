export function Kpi({ label, value, unit }: { label: string; value: string | null; unit?: string }) {
  return (
    <div className="rounded-control border border-line bg-surface px-3 py-2">
      <div className="text-xs text-muted">{label}</div>
      <div className="font-serif text-xl font-semibold">
        {value ?? "—"}
        {value && unit ? <span className="ml-1 text-sm font-normal text-muted">{unit}</span> : null}
      </div>
    </div>
  );
}
