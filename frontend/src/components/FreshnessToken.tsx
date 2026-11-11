import { useTranslation } from "react-i18next";
import type { LayerSource } from "@/api/types";
import { freshness } from "@/lib/freshness";
import { Token } from "./Token";

export function FreshnessToken({ source }: { source: LayerSource | null }) {
  const { t } = useTranslation();
  const f = freshness(source?.status, source?.data_date);
  return <Token tone={f.tone}>{t(f.key, f.values)}</Token>;
}
