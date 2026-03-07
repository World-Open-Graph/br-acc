import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import { Spinner } from "../components/common/Spinner";
import styles from "./Emendas.module.css";

interface EmendaRecord {
  payment: Record<string, string | number | boolean | null>;
  beneficiary: Record<string, string | number | boolean | null> | null;
}

interface EmendasResponse {
  data: EmendaRecord[];
  total_count: number;
  skip: number;
  limit: number;
}

const PAGE_SIZE = 50;

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function Emendas() {
  const { t } = useTranslation();
  const [data, setData] = useState<EmendasResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const fetchEmendas = useCallback(async (currentPage: number) => {
    setLoading(true);
    setError(null);
    try {
      const skip = currentPage * PAGE_SIZE;
      const res = await fetch(
        `${API_URL}/api/v1/emendas/?skip=${skip}&limit=${PAGE_SIZE}`,
      );
      if (!res.ok) {
        throw new Error(`Error: ${res.statusText}`);
      }
      const json: EmendasResponse = await res.json();
      setData(json);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchEmendas(page);
  }, [page, fetchEmendas]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total_count / PAGE_SIZE)) : 1;

  const formatCurrency = (val: unknown) => {
    const num = typeof val === "number" ? val : 0;
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: "BRL",
    }).format(num);
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>{t("emendas.title")}</h1>
        <p>{t("emendas.subtitle")}</p>
      </header>

      {loading && (
        <div className={styles.loadingState}>
          <Spinner />
          <p>{t("emendas.loading")}</p>
        </div>
      )}

      {error && <div className={styles.errorState}>{error}</div>}

      {!loading && !error && data && (
        <>
          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>{t("emendas.colOB")}</th>
                  <th>{t("emendas.colDate")}</th>
                  <th>{t("emendas.colType")}</th>
                  <th>{t("emendas.colValue")}</th>
                  <th>{t("emendas.colBeneficiary")}</th>
                  <th>{t("emendas.colActions")}</th>
                </tr>
              </thead>
              <tbody>
                {data.data.map((record) => (
                  <tr key={String(record.payment.transfer_id)}>
                    <td>{String(record.payment.ob ?? "")}</td>
                    <td>{String(record.payment.date ?? "")}</td>
                    <td>
                      <span className={styles.badge}>
                        {String(record.payment.amendment_type ?? "")}
                      </span>
                    </td>
                    <td className={styles.val}>
                      {formatCurrency(record.payment.value)}
                    </td>
                    <td>
                      {record.beneficiary ? (
                        <div className={styles.beneficiaryInfo}>
                          <strong>
                            {String(record.beneficiary.razao_social ?? "")}
                          </strong>
                          <span className={styles.cnpjLabel}>
                            {String(record.beneficiary.cnpj ?? "")}
                          </span>
                        </div>
                      ) : (
                        <span className={styles.cnpjLabel}>
                          {t("emendas.noLink")}
                        </span>
                      )}
                    </td>
                    <td>
                      {record.beneficiary?.cnpj ? (
                        <Link
                          to={`/app/analysis/cnpj_${String(record.beneficiary.cnpj)}`}
                          className={styles.actionBtn}
                        >
                          {t("emendas.exploreNode")}
                        </Link>
                      ) : (
                        "-"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className={styles.pagination}>
            <button
              className={styles.pageBtn}
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              {t("emendas.previous")}
            </button>

            <span className={styles.pageInfo}>
              {t("emendas.pageInfo", {
                page: page + 1,
                total: totalPages,
              })}
            </span>

            <button
              className={styles.pageBtn}
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
            >
              {t("emendas.next")}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
