export interface TherapyGoal {
  icf_code: string;
  goal_text: string;
  methods: string[];
  milestones: string[];
  timeframe: string;
}

export interface TherapyPhaseData {
  phase_name: string;
  goals: TherapyGoal[];
  duration: string;
}

export interface TherapyPlanData {
  patient_pseudonym: string;
  diagnose_text: string;
  plan_phases: TherapyPhaseData[];
  frequency: string;
  total_sessions: number;
  elternberatung: string;
  haeusliche_uebungen: string[];
}
