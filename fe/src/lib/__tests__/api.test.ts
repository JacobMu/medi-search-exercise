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
		// Arrange
		const jobResponse: JobResponse = { job_id: "abc-123", status: "pending" };
		mockResponse(202, jobResponse);
		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		// Act
		await submitOverlay(avatar, screenshot);

		// Assert
		expect(mockFetch).toHaveBeenCalledWith(
			"/api/overlay",
			expect.objectContaining({ method: "POST" }),
		);
	});

	it("uses FormData as body", async () => {
		// Arrange
		const jobResponse: JobResponse = { job_id: "abc-123", status: "pending" };
		mockResponse(202, jobResponse);
		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		// Act
		await submitOverlay(avatar, screenshot);

		// Assert
		const [, init] = mockFetch.mock.calls[0];
		expect(init?.body).toBeInstanceOf(FormData);
	});

	it("returns parsed JobResponse on 202", async () => {
		// Arrange
		const jobResponse: JobResponse = { job_id: "abc-123", status: "pending" };
		mockResponse(202, jobResponse);
		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		// Act
		const result = await submitOverlay(avatar, screenshot);

		// Assert
		expect(result).toEqual(jobResponse);
	});

	it("throws Error on non-2xx (415)", async () => {
		// Arrange
		mockResponse(415, { detail: "Unsupported Media Type" });
		const avatar = new File(["avatar"], "avatar.png", { type: "image/png" });
		const screenshot = new File(["screenshot"], "screenshot.png", {
			type: "image/png",
		});

		// Act
		const call = submitOverlay(avatar, screenshot);

		// Assert
		await expect(call).rejects.toThrow("Request failed with status 415");
	});
});

describe("pollJob", () => {
	it("sends a GET to /api/jobs/test-id", async () => {
		// Arrange
		const jobResponse: JobResponse = {
			job_id: "test-id",
			status: "processing",
		};
		mockResponse(200, jobResponse);

		// Act
		await pollJob("test-id");

		// Assert
		expect(mockFetch).toHaveBeenCalledWith(
			"/api/jobs/test-id",
			expect.anything(),
		);
	});

	it("returns parsed JobResponse on 200", async () => {
		// Arrange
		const jobResponse: JobResponse = {
			job_id: "test-id",
			status: "completed",
			output_url: "/output/test-id.png",
		};
		mockResponse(200, jobResponse);

		// Act
		const result = await pollJob("test-id");

		// Assert
		expect(result).toEqual(jobResponse);
	});

	it("throws Error on 404", async () => {
		// Arrange
		mockResponse(404, { detail: "Not found" });

		// Act
		const call = pollJob("test-id");

		// Assert
		await expect(call).rejects.toThrow("Request failed with status 404");
	});

	it("encodes path-traversal characters in jobId", async () => {
		// Arrange
		mockResponse(200, { job_id: "safe", status: "pending" });

		// Act
		await pollJob("../admin");

		// Assert
		const [url] = mockFetch.mock.calls[0] as [string, ...unknown[]];
		expect(url).toBe("/api/jobs/..%2Fadmin");
	});
});

describe("saveRating", () => {
	it("sends a POST to /api/save", async () => {
		// Arrange
		mockResponse(200, { ok: true });

		// Act
		await saveRating({
			job_id: "abc-123",
			rating: 4,
			processing_time_ms: 1200,
		});

		// Assert
		expect(mockFetch).toHaveBeenCalledWith(
			"/api/save",
			expect.objectContaining({ method: "POST" }),
		);
	});

	it("sends Content-Type: application/json header", async () => {
		// Arrange
		mockResponse(200, { ok: true });

		// Act
		await saveRating({
			job_id: "abc-123",
			rating: 4,
			processing_time_ms: 1200,
		});

		// Assert
		const [, init] = mockFetch.mock.calls[0];
		const headers = init?.headers as Record<string, string>;
		expect(headers["Content-Type"]).toBe("application/json");
	});

	it("sends correct JSON body", async () => {
		// Arrange
		mockResponse(200, { ok: true });
		const payload = { job_id: "abc-123", rating: 4, processing_time_ms: 1200 };

		// Act
		await saveRating(payload);

		// Assert
		const [, init] = mockFetch.mock.calls[0];
		expect(init?.body).toBe(JSON.stringify(payload));
	});

	it("resolves void on 200", async () => {
		// Arrange
		mockResponse(200, { ok: true });

		// Act
		const result = await saveRating({
			job_id: "abc-123",
			rating: 4,
			processing_time_ms: 1200,
		});

		// Assert
		expect(result).toBeUndefined();
	});

	it("throws Error on 422", async () => {
		// Arrange
		mockResponse(422, { detail: "Validation Error" });

		// Act
		const call = saveRating({
			job_id: "abc-123",
			rating: 6,
			processing_time_ms: 1200,
		});

		// Assert
		await expect(call).rejects.toThrow("Request failed with status 422");
	});
});

describe("fetchStats", () => {
	it("sends a GET to /api/stats", async () => {
		// Arrange
		const stats: StatsResponse = {
			total_generations: 10,
			avg_rating: 4.2,
			avg_processing_time_ms: 850,
			rating_distribution: { "1": 0, "2": 1, "3": 2, "4": 4, "5": 3 },
		};
		mockResponse(200, stats);

		// Act
		await fetchStats();

		// Assert
		expect(mockFetch).toHaveBeenCalledWith("/api/stats", expect.anything());
	});

	it("returns parsed StatsResponse on 200", async () => {
		// Arrange
		const stats: StatsResponse = {
			total_generations: 10,
			avg_rating: 4.2,
			avg_processing_time_ms: 850,
			rating_distribution: { "1": 0, "2": 1, "3": 2, "4": 4, "5": 3 },
		};
		mockResponse(200, stats);

		// Act
		const result = await fetchStats();

		// Assert
		expect(result).toEqual(stats);
	});

	it("throws Error on non-2xx", async () => {
		// Arrange
		mockResponse(500, { detail: "Internal Server Error" });

		// Act
		const call = fetchStats();

		// Assert
		await expect(call).rejects.toThrow("Request failed with status 500");
	});
});
