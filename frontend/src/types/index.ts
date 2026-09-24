export type Difficulty = "Easy" | "Medium" | "Hard" | "Very Hard";

export type PriorityLevel = "Low" | "Medium" | "High" | "Critical";

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface Task {
  id: string;
  owner_id: string;
  title: string;
  subject: string;
  deadline: string; // ISO datetime
  difficulty: Difficulty;
  estimated_hours: number;
  completed: boolean;
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

export interface Dashboard {
  incomplete_count: number;
  completed_count: number;
  high_priority_count: number;
  upcoming_count: number;
  overdue_count: number;
  upcoming_tasks: Task[];
  recommended_task: Task | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}
