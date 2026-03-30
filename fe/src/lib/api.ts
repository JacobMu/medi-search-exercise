import type { JobResponse, SaveRequest, StatsResponse } from "./types";

async function checkResponse(response: Response): Promise<void> {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
}

export async function submitOverlay(avatar: File, screenshot: File): Promise<JobResponse> {
  const body = new FormData();
  body.append("avatar", avatar);
  body.append("screenshot", screenshot);

  const response = await fetch("/api/overlay", { method: "POST", body });
  await checkResponse(response);
  return response.json() as Promise<JobResponse>;
}

export async function pollJob(jobId: string): Promise<JobResponse> {
  const response = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
    method: "GET",
  });
  await checkResponse(response);
  return response.json() as Promise<JobResponse>;
}

export async function saveRating(payload: SaveRequest): Promise<void> {
  const response = await fetch("/api/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await checkResponse(response);
}

export async function fetchStats(): Promise<StatsResponse> {
  const response = await fetch("/api/stats", { method: "GET" });
  await checkResponse(response);
  return response.json() as Promise<StatsResponse>;
}
