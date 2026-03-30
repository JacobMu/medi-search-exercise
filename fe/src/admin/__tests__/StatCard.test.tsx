import { StatCard } from "@/admin/components/StatCard";
import { render, screen } from "@testing-library/react";

describe("StatCard", () => {
	it("renders label", () => {
		// Act
		render(<StatCard label="Total Generations" value="42" />);

		// Assert
		expect(screen.getByText("Total Generations")).toBeInTheDocument();
	});

	it("renders value", () => {
		// Act
		render(<StatCard label="Total Generations" value="42" />);

		// Assert
		expect(screen.getByText("42")).toBeInTheDocument();
	});

	it("renders description when provided", () => {
		// Act
		render(
			<StatCard label="Total Generations" value="42" description="All time" />,
		);

		// Assert
		expect(screen.getByText("All time")).toBeInTheDocument();
	});

	it("does not render description when omitted", () => {
		// Act
		render(<StatCard label="Total Generations" value="42" />);

		// Assert
		expect(screen.queryByText("All time")).not.toBeInTheDocument();
	});
});
