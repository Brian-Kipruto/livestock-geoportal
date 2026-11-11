import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { formatMonth, monthRange } from "@/lib/months";
import { FIRST_MONTH, LATEST_MONTH, useView } from "@/state/view";

const SPEEDS = [1, 2, 4] as const;
const BASE_MS = 900;

/** Bottom-centre playback dock (FR-E4). Space = play/pause, ←/→ = step. */
export function Playback({ subtitle }: { subtitle?: string }) {
  const { t, i18n } = useTranslation();
  const { time, lite, set } = useView();
  const months = useMemo(() => monthRange(FIRST_MONTH, LATEST_MONTH), []);
  const idx = Math.max(0, months.indexOf(time));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [loop, setLoop] = useState(true);

  const step = (d: number) => {
    const next = idx + d;
    if (next >= months.length) return loop ? set({ time: months[0] }) : setPlaying(false);
    if (next < 0) return;
    set({ time: months[next] });
  };

  useEffect(() => {
    if (!playing || lite) return;
    const id = window.setTimeout(() => step(1), BASE_MS / speed);
    return () => window.clearTimeout(id);
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (["INPUT", "SELECT", "TEXTAREA", "BUTTON"].includes(tag)) return;
      if (e.code === "Space") {
        e.preventDefault();
        setPlaying((p) => !p);
      } else if (e.key === "ArrowRight") step(1);
      else if (e.key === "ArrowLeft") step(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const years = months.filter((m) => m.endsWith("-01")).map((m) => m.slice(0, 4));

  return (
    <section
      aria-label="Time"
      className="panel map-zone absolute bottom-4 left-1/2 z-20 w-[min(960px,calc(100vw-660px))] min-w-[520px] -translate-x-1/2 px-4 py-3 max-[899px]:min-w-0 max-[899px]:translate-x-0"
    >
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn w-11 px-0" aria-label={t("playback.prev")} onClick={() => step(-1)}>
          ◀
        </button>
        <button
          type="button"
          className="btn-primary h-12 w-12 rounded-full px-0"
          aria-label={playing ? t("playback.pause") : t("playback.play")}
          aria-pressed={playing}
          disabled={lite}
          onClick={() => setPlaying((p) => !p)}
        >
          {playing ? "❚❚" : "▶"}
        </button>
        <button type="button" className="btn w-11 px-0" aria-label={t("playback.next")} onClick={() => step(1)}>
          ▶
        </button>
        <div className="mr-auto" aria-live="polite">
          <div className="font-serif text-2xl font-semibold leading-none">{formatMonth(time, i18n.language)}</div>
          <div className="text-xs text-muted">{subtitle ?? t("playback.monthly")}</div>
        </div>
        <div className="seg" role="group" aria-label={t("playback.speed")}>
          {SPEEDS.map((s) => (
            <button key={s} type="button" aria-pressed={speed === s} onClick={() => setSpeed(s)}>
              {s}×
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={loop} onChange={(e) => setLoop(e.target.checked)} />
          {t("playback.loop")}
        </label>
      </div>
      <label className="sr-only" htmlFor="time-slider">
        {t("playback.month")}
      </label>
      <input
        id="time-slider"
        type="range"
        min={0}
        max={months.length - 1}
        value={idx}
        onChange={(e) => set({ time: months[Number(e.target.value)] })}
        className="mt-3 w-full accent-pigment-umber"
        aria-valuetext={formatMonth(time, i18n.language)}
      />
      <div className="mt-1 flex justify-between text-[11px] tabular-nums text-muted">
        {years.map((y) => (
          <span key={y}>{y}</span>
        ))}
      </div>
    </section>
  );
}
