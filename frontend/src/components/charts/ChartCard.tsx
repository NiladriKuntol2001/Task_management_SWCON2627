import { useState, type ReactNode } from "react";

export interface TableView {
  columns: string[];
  rows: (string | number)[][];
}

/** Card wrapper for every chart: title, optional subtitle, and a
 *  "Table" toggle so the numbers are always readable without color. */
export default function ChartCard({
  title,
  subtitle,
  table,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  table?: TableView;
  children: ReactNode;
  className?: string;
}) {
  const [showTable, setShowTable] = useState(false);

  return (
    <section className={`chart-card ${className}`}>
      <header className="chart-card-header">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="chart-card-subtitle">{subtitle}</p>}
        </div>
        {table && (
          <button
            type="button"
            className="link-button"
            onClick={() => setShowTable((v) => !v)}
            aria-pressed={showTable}
          >
            {showTable ? "Chart" : "Table"}
          </button>
        )}
      </header>
      {showTable && table ? (
        <div className="table-wrap">
          <table className="data-table compact">
            <thead>
              <tr>
                {table.columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} className={typeof cell === "number" ? "num" : ""}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        children
      )}
    </section>
  );
}
