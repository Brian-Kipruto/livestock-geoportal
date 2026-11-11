import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { apiGet } from "@/api/client";
import { Panel } from "@/components/Panel";
import { Token } from "@/components/Token";
import { freshness, type DatasetStatus } from "@/lib/freshness";

interface DatasetRow {
  key: string;
  name: string;
  provider: string;
  licence: string;
  status: DatasetStatus;
  last_data_date: string | null;
}

/** Sources & licences — transparency page (SDD §11.1, NFR-12). */
export function AboutPage() {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: ["datasets"],
    queryFn: ({ signal }) => apiGet<DatasetRow[]>("/datasets/", signal),
  });
  return (
    <Panel className="absolute left-4 top-[196px] z-10 max-h-[calc(100vh-220px)] w-[min(720px,calc(100vw-32px))] overflow-y-auto p-4" title={t("nav.about")}>
      <table className="mt-2 w-full text-left text-sm">
        <thead className="section-label">
          <tr>
            <th className="py-2">Dataset</th>
            <th>Provider</th>
            <th>Licence</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(data ?? []).map((d) => {
            const f = freshness(d.status, d.last_data_date);
            return (
              <tr key={d.key} className="border-t border-line">
                <td className="py-2 pr-2">{d.name}</td>
                <td className="pr-2 text-muted">{d.provider}</td>
                <td className="pr-2 text-muted">{d.licence}</td>
                <td>
                  <Token tone={f.tone}>{t(f.key, f.values)}</Token>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Panel>
  );
}
