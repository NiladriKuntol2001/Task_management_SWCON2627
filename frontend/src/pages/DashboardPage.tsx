import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Dashboard } from "../types";
import TaskCard from "../components/TaskCard";
import PriorityBadge from "../components/PriorityBadge";

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

  return (
    <div className="page">
      <h1>Dashboard</h1>

      <div className="stat-grid">
        <div className="stat-tile">
          <div className="stat-value">{dashboard.incomplete_count}</div>
          <div className="stat-label">Incomplete</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{dashboard.completed_count}</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{dashboard.high_priority_count}</div>
          <div className="stat-label">High priority</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{dashboard.upcoming_count}</div>
          <div className="stat-label">Due this week</div>
        </div>
        <div className="stat-tile stat-tile-danger">
          <div className="stat-value">{dashboard.overdue_count}</div>
          <div className="stat-label">Overdue</div>
        </div>
      </div>

      <section className="section">
        <h2>What should I work on today?</h2>
        {dashboard.recommended_task ? (
          <TaskCard task={dashboard.recommended_task} onComplete={handleComplete} />
        ) : (
          <div className="empty-state">
            <p>Nothing left to do &mdash; nice work! Add a new task to get a recommendation.</p>
          </div>
        )}
      </section>

      <section className="section">
        <h2>Upcoming deadlines (next 7 days)</h2>
        {dashboard.upcoming_tasks.length === 0 ? (
          <div className="empty-state">
            <p>No deadlines in the next 7 days.</p>
          </div>
        ) : (
          <div className="task-list">
            {dashboard.upcoming_tasks.map((task) => (
              <TaskCard key={task.id} task={task} onComplete={handleComplete} />
            ))}
          </div>
        )}
      </section>

      <p className="legend">
        Priority: <PriorityBadge level="Critical" /> <PriorityBadge level="High" />{" "}
        <PriorityBadge level="Medium" /> <PriorityBadge level="Low" />
      </p>
    </div>
  );
}
