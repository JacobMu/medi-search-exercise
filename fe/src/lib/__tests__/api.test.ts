import { fetchStats, pollJob, saveRating, submitOverlay } from "@/lib/api";
import type { JobResponse, StatsResponse } from "@/lib/types";

// jsdom doesn't include fetch; define a stub so jest.spyOn can wrap it
if (!global.fetch) {
	global.fetch = jest.fn() as typeof fetch;
}

const mockFetch = jest.spyOn(global, "fetch");

beforeEach(() => {
	mockFetch.mockReset();
});

function mockResponse(status: number, body: unknown): void {
	mockFetch.mockResolvedValueOnce({
		ok: status >= 200 && status < 300,
		status,
		statusText: status === 200 ? "OK" : "Error",
		json: () => Promise.resolve(body),
	} as Response);
}

describe("submitOverlay", () => {
	it("sends a POST to /api/overlay", async () => {
		const jobResponse: JobResponse = { job_id: "abc-123", status: "pending" };
		mockResponse(202, jobResponse);

		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		await submitOverlay(avatar, screenshot);

		expect(mockFetch).toHaveBeenCalledWith(
			"/api/overlay",
			expect.objectContaining({ method: "POST" }),
		);
	});

	it("uses FormData as body", async () => {
		const jobResponse: JobResponse = { job_id: "abc-123", status: "pending" };
		mockResponse(202, jobResponse);

		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		await submitOverlay(avatar, screenshot);

		const [, init] = mockFetch.mock.calls[0];
		expect(init?.body).toBeInstanceOf(FormData);
	});

	it("returns parsed JobResponse on 202", async () => {
		const jobResponse: JobResponse = { job_id: "abc-123", status: "pending" };
		mockResponse(202, jobResponse);

		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		const result = await submitOverlay(avatar, screenshot);

		expect(result).toEqual(jobResponse);
	});

	it("throws Error on non-2xx (415)", async () => {
		mockResponse(415, { detail: "Unsupported Media Type" });

		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		await expect(submitOverlay(avatar, screenshot)).rejects.toThrow(
			"Request failed with status 415",
		);
	});
});

describe("pollJob", () => {
	it("sends a GET to /api/jobs/test-id", async () => {
		const jobResponse: JobResponse = {
			job_id: "test-id",
			status: "processing",
		};
		mockResponse(200, jobResponse);

		await pollJob("test-id");

		expect(mockFetch).toHaveBeenCalledWith(
			"/api/jobs/test-id",
			expect.anything(),
		);
	});

	it("returns parsed JobResponse on 200", async () => {
		const jobResponse: JobResponse = {
			job_id: "test-id",
			status: "completed",
			output_url: "/output/test-id.png",
		};
		mockResponse(200, jobResponse);

		const result = await pollJob("test-id");

		expect(result).toEqual(jobResponse);
	});

	it("throws Error on 404", async () => {
		mockResponse(404, { detail: "Not found" });

		await expect(pollJob("test-id")).rejects.toThrow(
			"Request failed with status 404",
		);
	});

	it("encodes path-traversal characters in jobId", async () => {
		mockResponse(200, { job_id: "safe", status: "pending" });
		await pollJob("../admin");
		const [url] = mockFetch.mock.calls[0] as [string, ...unknown[]];
		expect(url).toBe("/api/jobs/..%2Fadmin");
	});
});

describe("saveRating", () => {
	it("sends a POST to /api/save", async () => {
		mockResponse(200, { ok: true });

		await saveRating({
			job_id: "abc-123",
			rating: 4,
			processing_time_ms: 1200,
		});

		expect(mockFetch).toHaveBeenCalledWith(
			"/api/save",
			expect.objectContaining({ method: "POST" }),
		);
	});

	it("sends Content-Type: application/json header", async () => {
		mockResponse(200, { ok: true });

		await saveRating({
			job_id: "abc-123",
			rating: 4,
			processing_time_ms: 1200,
		});

		const [, init] = mockFetch.mock.calls[0];
		const headers = init?.headers as Record<string, string>;
		expect(headers["Content-Type"]).toBe("application/json");
	});

	it("sends correct JSON body", async () => {
		mockResponse(200, { ok: true });

		const payload = { job_id: "abc-123", rating: 4, processing_time_ms: 1200 };
		await saveRating(payload);

		const [, init] = mockFetch.mock.calls[0];
		expect(init?.body).toBe(JSON.stringify(payload));
	});

	it("resolves void on 200", async () => {
		mockResponse(200, { ok: true });

		const result = await saveRating({
			job_id: "abc-123",
			rating: 4,
			processing_time_ms: 1200,
		});

		expect(result).toBeUndefined();
	});

	it("throws Error on 422", async () => {
		mockResponse(422, { detail: "Validation Error" });

		await expect(
			saveRating({ job_id: "abc-123", rating: 6, processing_time_ms: 1200 }),
		).rejects.toThrow("Request failed with status 422");
	});
});

describe("fetchStats", () => {
	it("sends a GET to /api/stats", async () => {
		const stats: StatsResponse = {
			total_generations: 10,
			avg_rating: 4.2,
			avg_processing_time_ms: 850,
			rating_distribution: { "1": 0, "2": 1, "3": 2, "4": 4, "5": 3 },
		};
		mockResponse(200, stats);

		await fetchStats();

		expect(mockFetch).toHaveBeenCalledWith("/api/stats", expect.anything());
	});

	it("returns parsed StatsResponse on 200", async () => {
		const stats: StatsResponse = {
			total_generations: 10,
			avg_rating: 4.2,
			avg_processing_time_ms: 850,
			rating_distribution: { "1": 0, "2": 1, "3": 2, "4": 4, "5": 3 },
		};
		mockResponse(200, stats);

		const result = await fetchStats();

		expect(result).toEqual(stats);
	});

	it("throws Error on non-2xx", async () => {
		mockResponse(500, { detail: "Internal Server Error" });

		await expect(fetchStats()).rejects.toThrow(
			"Request failed with status 500",
		);
	});
});
