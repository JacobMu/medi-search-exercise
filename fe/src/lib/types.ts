export type JobStatus = "pending" | "processing" | "completed" | "failed";

export interface JobResponse {
	job_id: string;
	status: JobStatus;
	output_url?: string;
	error?: string;
}

export interface SaveRequest {
	job_id: string;
	rating: number; // 1–5
	processing_time_ms: number; // ≥0
}

export interface RatingDistribution {
	"1": number;
	"2": number;
	"3": number;
	"4": number;
	"5": number;
}

export interface StatsResponse {
	total_generations: number;
	avg_rating: number;
	avg_processing_time_ms: number;
	rating_distribution: RatingDistribution;
}
