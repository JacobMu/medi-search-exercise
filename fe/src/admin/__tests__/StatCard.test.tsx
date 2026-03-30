import { StatCard } from "@/admin/components/StatCard";
import { render, screen } from "@testing-library/react";

describe("StatCard", () => {
	it("renders label", () => {
		render(<StatCard label="Total Generations" value="42" />);
		expect(screen.getByText("Total Generations")).toBeInTheDocument();
	});

	it("renders value", () => {
		render(<StatCard label="Total Generations" value="42" />);
		expect(screen.getByText("42")).toBeInTheDocument();
	});

	it("renders description when provided", () => {
		render(
			<StatCard label="Total Generations" value="42" description="All time" />,
		);
		expect(screen.getByText("All time")).toBeInTheDocument();
	});

	it("does not render description when omitted", () => {
		render(<StatCard label="Total Generations" value="42" />);
		expect(screen.queryByText("All time")).not.toBeInTheDocument();
	});
});
