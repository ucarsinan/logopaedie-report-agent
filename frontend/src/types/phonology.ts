export interface PhonologicalProcess {
  target_word: string;
  production: string;
  processes: string[];
  severity: string;
}

export interface PhonologicalAnalysisData {
  items: PhonologicalProcess[];
  summary: string;
  age_appropriate: boolean;
  recommended_focus: string[];
}

export interface ComparisonItem {
  category: string;
  initial_finding: string;
  current_finding: string;
  change: string;
  details: string;
}

export interface ReportComparisonData {
  items: ComparisonItem[];
  overall_progress: string;
  remaining_issues: string[];
  recommendation: string;
}
