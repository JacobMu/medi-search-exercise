import { RatingBar } from "@/admin/components/RatingBar";
import type { RatingDistribution } from "@/lib/types";
import { render, screen } from "@testing-library/react";

const dist: RatingDistribution = { "1": 0, "2": 0, "3": 5, "4": 10, "5": 2 };

describe("RatingBar", () => {
	it("renders 5 bar rows", () => {
		render(<RatingBar distribution={dist} />);
		for (let i = 1; i <= 5; i++) {
			expect(screen.getByTestId(`rating-bar-${i}`)).toBeInTheDocument();
		}
	});

	it("bar with highest count gets 100% width", () => {
		render(<RatingBar distribution={dist} />);
		const fill = screen.getByTestId("rating-bar-fill-4");
		expect(fill).toHaveStyle({ width: "100%" });
	});

	it("bar with zero count renders at 0% width", () => {
		render(<RatingBar distribution={dist} />);
		const fill = screen.getByTestId("rating-bar-fill-1");
		expect(fill).toHaveStyle({ width: "0%" });
	});

	it("proportional width for star 5 (count=2, max=10)", () => {
		render(<RatingBar distribution={dist} />);
		const fill = screen.getByTestId("rating-bar-fill-5");
		expect(fill).toHaveStyle({ width: "20%" });
	});

	it("no divide-by-zero when all counts are 0", () => {
		const zeroDist: RatingDistribution = {
			"1": 0,
			"2": 0,
			"3": 0,
			"4": 0,
			"5": 0,
		};
		render(<RatingBar distribution={zeroDist} />);
		for (let i = 1; i <= 5; i++) {
			const fill = screen.getByTestId(`rating-bar-fill-${i}`);
			expect(fill).toHaveStyle({ width: "0%" });
		}
	});

	it("renders correctly when distribution has missing keys (sparse)", () => {
		const sparseDist = { "5": 3 } as unknown as RatingDistribution;
		render(<RatingBar distribution={sparseDist} />);
		const fillMax = screen.getByTestId("rating-bar-fill-5");
		expect(fillMax).toHaveStyle({ width: "100%" });
		for (const star of [1, 2, 3, 4]) {
			const fill = screen.getByTestId(`rating-bar-fill-${star}`);
			expect(fill).toHaveStyle({ width: "0%" });
		}
	});
});
