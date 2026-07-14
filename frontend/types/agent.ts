export type OutputType = "text" | "chart" | "table" | "docx" | "pdf";
export type StepStatus = "running" | "completed" | "failed";

export type StepEvent = {
  step: string;
  status: StepStatus;
  message: string;
  payload?: Record<string, unknown>;
  timestamp?: string;
};

export type SourceFinding = {
  query?: string;
  title: string;
  url: string;
  snippet?: string;
  published_at?: string | null;
  credibility?: {
    domain?: string;
    tier?: string;
    score?: number;
  };
};

export type ChartArtifact = {
  type: "chart";
  data: Array<Record<string, string | number>>;
};

export type TableArtifact = {
  type: "table";
  columns?: string[];
  rows: Array<Record<string, string | number | null | undefined>>;
};

export type FileArtifact = {
  type: "docx" | "pdf" | "file";
  href: string;
  fileName?: string;
};

export type AgentArtifact = ChartArtifact | TableArtifact | FileArtifact | null;

export type CompletionPayload = {
  session_id?: string;
  answer?: string;
  output_type?: OutputType;
  artifact?: AgentArtifact;
  sources?: SourceFinding[];
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  output_type?: OutputType;
  outputMode?: "auto" | "explicit";
  artifact?: AgentArtifact;
  sources?: SourceFinding[];
};
