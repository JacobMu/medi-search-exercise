import { pollJob, saveRating, submitOverlay } from "@/lib/api";
import { useCallback, useEffect, useRef, useState } from "react";

function isSafeOutputUrl(url: string | undefined): url is string {
	if (!url) return false;
	// Only allow same-origin relative paths starting with /output/
	return url.startsWith("/output/");
}

export type ComposePhase = "idle" | "uploading" | "polling" | "done" | "error";

export interface ComposeState {
	phase: ComposePhase;
	jobId: string | null;
	outputUrl: string | null;
	errorMessage: string | null;
	processingTimeMs: number | null;
}

export interface UseComposeReturn {
	state: ComposeState;
	submit: (avatar: File, screenshot: File) => void;
	rate: (rating: number) => void;
	reset: () => void;
}

const initialState: ComposeState = {
	phase: "idle",
	jobId: null,
	outputUrl: null,
	errorMessage: null,
	processingTimeMs: null,
};

export function useCompose(): UseComposeReturn {
	const [state, setState] = useState<ComposeState>(initialState);

	const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
	const startTimeRef = useRef<number>(0);
	// Refs to read current values inside callbacks without stale closures
	const jobIdRef = useRef<string | null>(null);
	const processingTimeMsRef = useRef<number | null>(null);
	const phaseRef = useRef<ComposePhase>("idle");

	const clearTimers = useCallback(() => {
		if (intervalRef.current !== null) {
			clearInterval(intervalRef.current);
			intervalRef.current = null;
		}
		if (timeoutRef.current !== null) {
			clearTimeout(timeoutRef.current);
			timeoutRef.current = null;
		}
	}, []);

	const submit = useCallback(
		async (avatar: File, screenshot: File) => {
			clearTimers();

			phaseRef.current = "uploading";
			jobIdRef.current = null;
			processingTimeMsRef.current = null;
			setState({
				phase: "uploading",
				jobId: null,
				outputUrl: null,
				errorMessage: null,
				processingTimeMs: null,
			});

			startTimeRef.current = Date.now();

			let jobId: string;
			try {
				const response = await submitOverlay(avatar, screenshot);
				jobId = response.job_id;
			} catch (err) {
				const msg = err instanceof Error ? err.message : "Unknown error";
				phaseRef.current = "error";
				setState((prev) => ({ ...prev, phase: "error", errorMessage: msg }));
				return;
			}

			jobIdRef.current = jobId;
			phaseRef.current = "polling";
			setState((prev) => ({ ...prev, phase: "polling", jobId }));

			// Timeout after 60 s
			timeoutRef.current = setTimeout(() => {
				if (intervalRef.current !== null) {
					clearInterval(intervalRef.current);
					intervalRef.current = null;
				}
				timeoutRef.current = null;
				phaseRef.current = "error";
				setState((prev) => ({
					...prev,
					phase: "error",
					errorMessage: "Timed out waiting for result",
				}));
			}, 60000);

			// Poll every 1000 ms
			intervalRef.current = setInterval(async () => {
				try {
					const jobResponse = await pollJob(jobId);
					if (jobResponse.status === "completed") {
						if (!isSafeOutputUrl(jobResponse.output_url)) {
							clearTimers();
							phaseRef.current = "error";
							setState((prev) => ({
								...prev,
								phase: "error",
								errorMessage: "Received an invalid output URL from the server",
							}));
							return;
						}
						clearTimers();
						const ms = Date.now() - startTimeRef.current;
						processingTimeMsRef.current = ms;
						phaseRef.current = "done";
						setState((prev) => ({
							...prev,
							phase: "done",
							outputUrl: jobResponse.output_url ?? null,
							processingTimeMs: ms,
						}));
					} else if (jobResponse.status === "failed") {
						clearTimers();
						phaseRef.current = "error";
						setState((prev) => ({
							...prev,
							phase: "error",
							errorMessage: jobResponse.error ?? "Job failed",
						}));
					}
					// pending / processing: continue polling
				} catch (err) {
					clearTimers();
					const msg = err instanceof Error ? err.message : "Unknown error";
					phaseRef.current = "error";
					setState((prev) => ({ ...prev, phase: "error", errorMessage: msg }));
				}
			}, 1000);
		},
		[clearTimers],
	);

	const rate = useCallback((rating: number) => {
		if (
			phaseRef.current !== "done" ||
			jobIdRef.current === null ||
			processingTimeMsRef.current === null
		) {
			return;
		}
		saveRating({
			job_id: jobIdRef.current,
			rating,
			processing_time_ms: processingTimeMsRef.current,
		}).catch(() => {
			// best-effort; swallow silently
		});
	}, []);

	const reset = useCallback(() => {
		clearTimers();
		phaseRef.current = "idle";
		jobIdRef.current = null;
		processingTimeMsRef.current = null;
		setState(initialState);
	}, [clearTimers]);

	// Cleanup on unmount
	useEffect(() => {
		return () => {
			clearTimers();
		};
	}, [clearTimers]);

	return { state, submit, rate, reset };
}
