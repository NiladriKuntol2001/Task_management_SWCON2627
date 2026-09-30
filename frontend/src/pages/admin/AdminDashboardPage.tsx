import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { adminApi } from "../../api/client";
import type { AdminStats, PriorityLevel } from "../../types";
import StatTile from "../../components/StatTile";
import ChartCard from "../../components/charts/ChartCard";
import LineChart from "../../components/charts/LineChart";
import HBarChart from "../../components/charts/HBarChart";
import StackedHBarChart from "../../components/charts/StackedHBarChart";
import ColumnChart from "../../components/charts/ColumnChart";
import { CRITICAL, PRIORITY_COLORS, SERIES } from "../../components/charts/chartTheme";
import PriorityBadge from "../../components/PriorityBadge";
import { formatNumber, relativeTime } from "../../utils/format";

function dayLabel(day: string): string {
  // "2026-09-27" -> "Sep 27" without timezone drift.
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null);

  const load = () => {
    setError(null);
    adminApi
      .stats()
      .then((s) => {
        setStats(s);
        setRefreshedAt(new Date());
      })
      .catch(() => setError("Could not load platform statistics."));
  };

  useEffect(load, []);

  if (error) return <div className="page-error">{error}</div>;
  if (!stats) return <div className="page-loading">Loading...</div>;

  const days = stats.daily_activity.map((d) => dayLabel(d.day));
  const created14 = stats.daily_activity.reduce((s, d) => s + d.created, 0);
  const completed14 = stats.daily_activity.reduce((s, d) => s + d.completed, 0);

  return (
    <div className="page page-wide">
      <div className="page-header">
        <div>
          <h1>Admin dashboard</h1>
          <p className="page-subtitle">
            Platform-wide view of every student and task.
            {refreshedAt && <> Updated {refreshedAt.toLocaleTimeString()}.</>}
          </p>
        </div>
        <div className="header-actions">
          <button type="button" className="btn btn-secondary" onClick={load}>
            Refresh
          </button>
          <Link to="/admin/users" className="btn btn-primary">
            Manage users
          </Link>
        </div>
      </div>

      {/* Headline KPIs — each links to the list behind it. */}
      <div className="stat-grid stat-grid-6">
        <StatTile
          label="Students"
          value={stats.students_total}
          hint={`+${stats.new_users_7d} in the last 7 days`}
          to="/admin/users?role=student"
        />
        <StatTile
          label="Open tasks"
          value={stats.tasks_open}
          hint={`${formatNumber(stats.open_hours)} h of estimated work`}
          to="/admin/tasks?completed=false"
        />
        <StatTile
          label="Completion rate"
          value={`${stats.completion_rate}%`}
          hint={`${stats.tasks_completed} of ${stats.tasks_total} tasks done`}
          tone={stats.completion_rate >= 50 ? "good" : "default"}
          to="/admin/tasks?completed=true"
        />
        <StatTile
          label="Overdue"
          value={stats.tasks_overdue}
          hint={`${stats.students_with_overdue} student${stats.students_with_overdue === 1 ? "" : "s"} affected`}
          tone={stats.tasks_overdue > 0 ? "danger" : "default"}
          to="/admin/tasks?overdue_only=true"
        />
        <StatTile
          label="Critical open"
          value={stats.critical_open}
          hint="Score 80-100, not yet done"
          tone={stats.critical_open > 0 ? "warning" : "default"}
          to="/admin/tasks?priority_level=Critical&completed=false"
        />
        <StatTile
          label="Accounts"
          value={stats.users_total}
          hint={`${stats.admins_total} admin · ${stats.users_total - stats.active_users} deactivated`}
          to="/admin/users"
        />
      </div>

      <div className="dash-grid">
        <ChartCard
          className="span-2"
          title="Activity, last 14 days"
          subtitle={`${created14} tasks created · ${completed14} completed`}
          table={{
            columns: ["Day", "Created", "Completed"],
            rows: stats.daily_activity.map((d) => [dayLabel(d.day), d.created, d.completed]),
          }}
        >
          <LineChart
            xLabels={days}
            series={[
              { name: "Created", color: SERIES.primary, values: stats.daily_activity.map((d) => d.created) },
              { name: "Completed", color: SERIES.secondary, values: stats.daily_activity.map((d) => d.completed) },
            ]}
          />
        </ChartCard>

        <ChartCard
          title="Open tasks by priority"
          subtitle="Using the spec's score bands"
          table={{
            columns: ["Priority", "Open tasks"],
            rows: stats.priority_distribution.map((p) => [p.label, p.count]),
          }}
        >
          <HBarChart
            data={[...stats.priority_distribution].reverse().map((p) => ({
              label: p.label,
              value: p.count,
              color: PRIORITY_COLORS[p.label as PriorityLevel],
            }))}
            emptyText="No open tasks."
          />
        </ChartCard>

        <ChartCard
          title="Deadline pressure"
          subtitle="Open tasks by time left until deadline"
          table={{
            columns: ["Due", "Open tasks"],
            rows: stats.deadline_pressure.map((b) => [b.label, b.count]),
          }}
        >
          <ColumnChart
            data={stats.deadline_pressure.map((b) => ({
              label: b.label,
              value: b.count,
              color: b.label === "Overdue" ? CRITICAL : SERIES.primary,
            }))}
            emptyText="No open tasks."
          />
        </ChartCard>

        <ChartCard
          title="Subjects"
          subtitle="Top subjects by task volume"
          table={{
            columns: ["Subject", "Open", "Completed", "Overdue"],
            rows: stats.subjects.map((s) => [s.subject, s.open, s.completed, s.overdue]),
          }}
        >
          <StackedHBarChart
            aLabel="Open"
            bLabel="Completed"
            rows={stats.subjects.map((s) => ({
              label: s.subject,
              a: s.open,
              b: s.completed,
              detail: s.overdue ? `${s.overdue} overdue` : undefined,
            }))}
            emptyText="No tasks yet."
          />
        </ChartCard>

        <ChartCard
          title="Open tasks by difficulty"
          table={{
            columns: ["Difficulty", "Open tasks"],
            rows: stats.difficulty_distribution.map((d) => [d.label, d.count]),
          }}
        >
          <HBarChart
            data={stats.difficulty_distribution.map((d) => ({ label: d.label, value: d.count, color: SERIES.primary }))}
            emptyText="No open tasks."
          />
        </ChartCard>
      </div>

      <div className="dash-grid">
        <section className="chart-card span-2">
          <header className="chart-card-header">
            <div>
              <h3>Students who need attention</h3>
              <p className="chart-card-subtitle">Most overdue first, then most critical open work</p>
            </div>
          </header>
          {stats.students_at_risk.length === 0 ? (
            <p className="chart-empty">No students with overdue or critical tasks. </p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th className="num">Overdue</th>
                    <th className="num">Critical open</th>
                    <th className="num">Open</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {stats.students_at_risk.map((s) => (
                    <tr key={s.user_id}>
                      <td>
                        <div className="cell-title">{s.name}</div>
                        <div className="cell-sub">{s.email}</div>
                      </td>
                      <td className={`num ${s.overdue ? "text-danger strong" : ""}`}>{s.overdue}</td>
                      <td className="num">{s.critical_open}</td>
                      <td className="num">{s.open}</td>
                      <td className="row-actions">
                        <Link to={`/admin/users/${s.user_id}`} className="btn btn-sm btn-secondary">
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="chart-card">
          <header className="chart-card-header">
            <div>
              <h3>Latest tasks</h3>
              <p className="chart-card-subtitle">Newest first, all students</p>
            </div>
            <Link to="/admin/tasks?sort_by=created" className="link-button">
              View all
            </Link>
          </header>
          {stats.recent_tasks.length === 0 ? (
            <p className="chart-empty">No tasks yet.</p>
          ) : (
            <ul className="feed">
              {stats.recent_tasks.map((t) => (
                <li key={t.id} className="feed-item">
                  <div className="feed-main">
                    <span className="cell-title">{t.title}</span>
                    <span className="cell-sub">
                      <Link to={`/admin/users/${t.owner_id}`} className="cell-link">
                        {t.owner_name}
                      </Link>{" "}
                      · {t.subject} · {relativeTime(t.created_at)}
                    </span>
                  </div>
                  <PriorityBadge level={t.priority_level} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
