import { useCompose } from "@/composer/hooks/useCompose";
import * as api from "@/lib/api";
import { act, renderHook } from "@testing-library/react";

jest.mock("@/lib/api");

const mockSubmitOverlay = api.submitOverlay as jest.MockedFunction<
	typeof api.submitOverlay
>;
const mockPollJob = api.pollJob as jest.MockedFunction<typeof api.pollJob>;
const mockSaveRating = api.saveRating as jest.MockedFunction<
	typeof api.saveRating
>;

function makeFile(name: string): File {
	return new File(["data"], name, { type: "image/png" });
}

describe("useCompose", () => {
	beforeEach(() => {
		jest.useFakeTimers();
		jest.clearAllMocks();
	});

	afterEach(() => {
		jest.useRealTimers();
	});

	it("initial state is idle with all null fields", () => {
		const { result } = renderHook(() => useCompose());
		expect(result.current.state.phase).toBe("idle");
		expect(result.current.state.jobId).toBeNull();
		expect(result.current.state.outputUrl).toBeNull();
		expect(result.current.state.errorMessage).toBeNull();
		expect(result.current.state.processingTimeMs).toBeNull();
	});

	it("submit → uploading → polling → done (happy path)", async () => {
		mockSubmitOverlay.mockResolvedValueOnce({
			job_id: "abc",
			status: "pending",
		});
		mockPollJob
			.mockResolvedValueOnce({ job_id: "abc", status: "processing" })
			.mockResolvedValueOnce({
				job_id: "abc",
				status: "completed",
				output_url: "/output/abc.png",
			});

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		expect(result.current.state.phase).toBe("polling");

		// First tick: still processing
		await act(async () => {
			jest.advanceTimersByTime(1100);
		});
		expect(result.current.state.phase).toBe("polling");

		// Second tick: completed
		await act(async () => {
			jest.advanceTimersByTime(1100);
		});

		expect(result.current.state.phase).toBe("done");
		expect(result.current.state.outputUrl).toBe("/output/abc.png");
		expect(result.current.state.processingTimeMs).not.toBeNull();
		expect(result.current.state.processingTimeMs).toBeGreaterThanOrEqual(0);
	});

	it("polling → error when status is failed", async () => {
		mockSubmitOverlay.mockResolvedValueOnce({
			job_id: "abc",
			status: "pending",
		});
		mockPollJob.mockResolvedValueOnce({
			job_id: "abc",
			status: "failed",
			error: "Compositor crashed",
		});

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		await act(async () => {
			jest.advanceTimersByTime(1100);
		});

		expect(result.current.state.phase).toBe("error");
		expect(result.current.state.errorMessage).toBe("Compositor crashed");
	});

	it("polling → error on timeout after 60 s", async () => {
		mockSubmitOverlay.mockResolvedValueOnce({
			job_id: "abc",
			status: "pending",
		});
		mockPollJob.mockResolvedValue({ job_id: "abc", status: "processing" });

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		await act(async () => {
			jest.advanceTimersByTime(61000);
		});

		expect(result.current.state.phase).toBe("error");
		expect(result.current.state.errorMessage).toBe(
			"Timed out waiting for result",
		);
	});

	it("rate() calls saveRating with correct args", async () => {
		mockSubmitOverlay.mockResolvedValueOnce({
			job_id: "abc",
			status: "pending",
		});
		mockPollJob.mockResolvedValueOnce({
			job_id: "abc",
			status: "completed",
			output_url: "/output/abc.png",
		});
		mockSaveRating.mockResolvedValueOnce(undefined);

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		await act(async () => {
			jest.advanceTimersByTime(1100);
		});

		expect(result.current.state.phase).toBe("done");
		const { processingTimeMs } = result.current.state;

		await act(async () => {
			result.current.rate(4);
		});

		expect(mockSaveRating).toHaveBeenCalledWith({
			job_id: "abc",
			rating: 4,
			processing_time_ms: processingTimeMs,
		});
	});

	it("transitions to error when submitOverlay rejects", async () => {
		(api.submitOverlay as jest.Mock).mockRejectedValueOnce(
			new Error("Upload failed"),
		);

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		expect(result.current.state.phase).toBe("error");
		expect(result.current.state.errorMessage).toBe("Upload failed");
	});

	it("transitions to error when pollJob throws", async () => {
		(api.submitOverlay as jest.Mock).mockResolvedValueOnce({
			job_id: "abc",
			status: "pending",
		});
		(api.pollJob as jest.Mock).mockRejectedValueOnce(
			new Error("Network error"),
		);

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		await act(async () => {
			jest.advanceTimersByTime(1100);
		});

		expect(result.current.state.phase).toBe("error");
		expect(result.current.state.errorMessage).toBe("Network error");
	});

	it("transitions to error when output_url is not a safe path", async () => {
		(api.submitOverlay as jest.Mock).mockResolvedValueOnce({
			job_id: "abc",
			status: "pending",
		});
		(api.pollJob as jest.Mock).mockResolvedValue({
			job_id: "abc",
			status: "completed",
			output_url: "javascript:alert(1)",
		});

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		await act(async () => {
			jest.advanceTimersByTime(1100);
		});

		expect(result.current.state.phase).toBe("error");
		expect(result.current.state.errorMessage).toBe(
			"Received an invalid output URL from the server",
		);
	});

	it("reset() returns state to idle", async () => {
		mockSubmitOverlay.mockResolvedValueOnce({
			job_id: "abc",
			status: "pending",
		});
		mockPollJob.mockResolvedValue({ job_id: "abc", status: "processing" });

		const { result } = renderHook(() => useCompose());

		await act(async () => {
			result.current.submit(makeFile("avatar.png"), makeFile("screenshot.png"));
		});

		expect(result.current.state.phase).toBe("polling");

		act(() => {
			result.current.reset();
		});

		expect(result.current.state.phase).toBe("idle");
		expect(result.current.state.jobId).toBeNull();
		expect(result.current.state.outputUrl).toBeNull();
		expect(result.current.state.errorMessage).toBeNull();
		expect(result.current.state.processingTimeMs).toBeNull();
	});
});
