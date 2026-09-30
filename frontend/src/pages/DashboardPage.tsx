import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Dashboard, Task } from "../types";
import TaskCard from "../components/TaskCard";
import PriorityBadge from "../components/PriorityBadge";
import StatTile from "../components/StatTile";
import SegmentedBar from "../components/charts/SegmentedBar";
import { formatNumber, relativeTime } from "../utils/format";

function whyThisTask(task: Task): string {
  const parts: string[] = [];
  parts.push(task.is_overdue ? `overdue (${relativeTime(task.deadline)})` : `due ${relativeTime(task.deadline)}`);
  parts.push(`${task.difficulty.toLowerCase()} difficulty`);
  parts.push(`about ${task.estimated_hours} h of work`);
  return parts.join(" · ");
}

function CompactTaskRow({ task }: { task: Task }) {
  return (
    <li className="feed-item">
      <div className="feed-main">
        <Link to={`/tasks/${task.id}`} className="cell-title cell-link">
          {task.title}
        </Link>
        <span className={`cell-sub ${task.is_overdue ? "text-danger" : ""}`}>
          {task.subject} · {task.is_overdue ? `overdue ${relativeTime(task.deadline)}` : `due ${relativeTime(task.deadline)}`} ·{" "}
          {task.estimated_hours} h
        </span>
      </div>
      <PriorityBadge level={task.priority_level} />
    </li>
  );
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    api
      .dashboard()
      .then(setDashboard)
      .catch(() => setError("Could not load your dashboard. Please try again."));
  };

  useEffect(load, []);

  const handleComplete = async (id: string) => {
    await api.completeTask(id);
    load();
  };

  if (error) return <div className="page-error">{error}</div>;
  if (!dashboard) return <div className="page-loading">Loading...</div>;

  const rec = dashboard.recommended_task;
  const total = dashboard.incomplete_count + dashboard.completed_count;

  return (
    <div className="page">
      <div className="page-header">
        <h1>Dashboard</h1>
        <Link to="/tasks/new" className="btn btn-primary">
          New task
        </Link>
      </div>

      {/* FR-20: the single most important thing, first. */}
      <section className={`focus-card ${rec?.is_overdue ? "focus-card-overdue" : ""}`}>
        <div className="focus-eyebrow">What should I work on today?</div>
        {rec ? (
          <>
            <div className="focus-title-row">
              <Link to={`/tasks/${rec.id}`} className="focus-title">
                {rec.title}
              </Link>
              <PriorityBadge level={rec.priority_level} score={rec.priority_score} />
            </div>
            <p className="focus-why">
              {rec.subject} · {whyThisTask(rec)}
            </p>
            <div className="form-actions">
              <button type="button" className="btn btn-primary" onClick={() => handleComplete(rec.id)}>
                Mark complete
              </button>
              <Link to={`/tasks/${rec.id}`} className="btn btn-secondary">
                Open task
              </Link>
            </div>
          </>
        ) : (
          <p className="focus-why">
            {total === 0 ? "Add your first task to get a recommendation." : "Nothing left to do. Nice work!"}
          </p>
        )}
      </section>

      <div className="stat-grid">
        <StatTile label="Open tasks" value={dashboard.incomplete_count} to="/tasks" />
        <StatTile
          label="Due this week"
          value={dashboard.upcoming_count}
          hint={`${formatNumber(dashboard.hours_due_this_week)} h of work`}
        />
        <StatTile
          label="High priority"
          value={dashboard.high_priority_count}
          hint="High or Critical"
          tone={dashboard.high_priority_count ? "warning" : "default"}
        />
        <StatTile
          label="Overdue"
          value={dashboard.overdue_count}
          tone={dashboard.overdue_count ? "danger" : "default"}
        />
        <StatTile
          label="Completed"
          value={`${dashboard.completion_rate}%`}
          hint={
            <span className="progress" aria-label={`${dashboard.completion_rate}% complete`}>
              <span className="progress-fill" style={{ width: `${dashboard.completion_rate}%` }} />
            </span>
          }
          tone="good"
        />
      </div>

      <section className="chart-card">
        <header className="chart-card-header">
          <div>
            <h3>Open work by priority</h3>
            <p className="chart-card-subtitle">{dashboard.incomplete_count} open tasks</p>
          </div>
        </header>
        <SegmentedBar data={dashboard.priority_breakdown} />
      </section>

      <div className="dash-grid dash-grid-2">
        <section className="chart-card">
          <header className="chart-card-header">
            <div>
              <h3>Up next</h3>
              <p className="chart-card-subtitle">Your queue after today's focus, by priority</p>
            </div>
          </header>
          {dashboard.priority_queue.length === 0 ? (
            <p className="chart-empty">Nothing queued.</p>
          ) : (
            <ul className="feed">
              {dashboard.priority_queue.map((t) => (
                <CompactTaskRow key={t.id} task={t} />
              ))}
            </ul>
          )}
        </section>

        <section className="chart-card">
          <header className="chart-card-header">
            <div>
              <h3>{dashboard.overdue_count ? "Overdue" : "Upcoming deadlines"}</h3>
              <p className="chart-card-subtitle">
                {dashboard.overdue_count ? "Past their deadline and still open" : "Due in the next 7 days"}
              </p>
            </div>
          </header>
          {(dashboard.overdue_count ? dashboard.overdue_tasks : dashboard.upcoming_tasks).length === 0 ? (
            <p className="chart-empty">No deadlines in the next 7 days.</p>
          ) : (
            <ul className="feed">
              {(dashboard.overdue_count ? dashboard.overdue_tasks : dashboard.upcoming_tasks).slice(0, 6).map((t) => (
                <CompactTaskRow key={t.id} task={t} />
              ))}
            </ul>
          )}
        </section>
      </div>

      {dashboard.overdue_count > 0 && dashboard.upcoming_tasks.length > dashboard.overdue_count && (
        <section className="section">
          <h2>Also due this week</h2>
          <div className="task-list">
            {dashboard.upcoming_tasks
              .filter((t) => !t.is_overdue)
              .map((task) => (
                <TaskCard key={task.id} task={task} onComplete={handleComplete} />
              ))}
          </div>
        </section>
      )}
    </div>
  );
}
