export type Difficulty = "Easy" | "Medium" | "Hard" | "Very Hard";

export type PriorityLevel = "Low" | "Medium" | "High" | "Critical";

export interface User {
  id: number; // unique sequential user ID; the main admin is always 1
  name: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface Task {
  id: string;
  owner_id: number;
  title: string;
  subject: string;
  deadline: string; // ISO datetime
  difficulty: Difficulty;
  estimated_hours: number;
  completed: boolean;
  completed_at: string | null;
  priority_score: number;
  priority_level: PriorityLevel;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
}

export interface TaskInput {
  title: string;
  subject: string;
  deadline: string;
  difficulty: Difficulty;
  estimated_hours: number;
}

export type TaskPatch = Partial<TaskInput> & { completed?: boolean };

export interface LabelCount {
  label: string;
  count: number;
}

export interface Dashboard {
  incomplete_count: number;
  completed_count: number;
  high_priority_count: number;
  upcoming_count: number;
  overdue_count: number;
  completion_rate: number;
  hours_due_this_week: number;
  priority_breakdown: LabelCount[];
  upcoming_tasks: Task[];
  overdue_tasks: Task[];
  priority_queue: Task[];
  recommended_task: Task | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// --- admin -----------------------------------------------------------------

export interface AdminUser extends User {
  total_tasks: number;
  open_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  critical_open: number;
  last_activity: string | null;
}

export interface AdminUserPatch {
  name?: string;
  email?: string;
  is_admin?: boolean;
  is_active?: boolean;
  password?: string;
}

export interface AdminTask extends Task {
  owner_name: string;
  owner_email: string;
}

export interface AdminUserDetail {
  user: AdminUser;
  tasks: AdminTask[];
}

export interface AdminTaskPage {
  items: AdminTask[];
  total: number;
}

export interface SubjectStat {
  subject: string;
  open: number;
  completed: number;
  overdue: number;
}

export interface DailyActivity {
  day: string; // YYYY-MM-DD
  created: number;
  completed: number;
}

export interface StudentAtRisk {
  user_id: number;
  name: string;
  email: string;
  open: number;
  overdue: number;
  critical_open: number;
}

export interface AdminStats {
  users_total: number;
  students_total: number;
  admins_total: number;
  active_users: number;
  new_users_7d: number;
  students_with_overdue: number;
  tasks_total: number;
  tasks_open: number;
  tasks_completed: number;
  tasks_overdue: number;
  critical_open: number;
  completion_rate: number;
  open_hours: number;
  priority_distribution: LabelCount[];
  difficulty_distribution: LabelCount[];
  deadline_pressure: LabelCount[];
  subjects: SubjectStat[];
  daily_activity: DailyActivity[];
  students_at_risk: StudentAtRisk[];
  recent_tasks: AdminTask[];
}
