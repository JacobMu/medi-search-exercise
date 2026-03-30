import { StarRating } from "@/composer/components/StarRating";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

describe("StarRating", () => {
	it("renders 5 stars", () => {
		render(<StarRating value={0} onRate={jest.fn()} />);
		expect(screen.getAllByRole("button")).toHaveLength(5);
	});

	it("clicking star 3 calls onRate(3)", async () => {
		const onRate = jest.fn();
		render(<StarRating value={0} onRate={onRate} />);
		const buttons = screen.getAllByRole("button");
		await userEvent.click(buttons[2]);
		expect(onRate).toHaveBeenCalledWith(3);
	});

	it("clicking star 5 calls onRate(5)", async () => {
		const onRate = jest.fn();
		render(<StarRating value={0} onRate={onRate} />);
		const buttons = screen.getAllByRole("button");
		await userEvent.click(buttons[4]);
		expect(onRate).toHaveBeenCalledWith(5);
	});

	it("stars at/below value have data-active=true, others false", () => {
		render(<StarRating value={3} onRate={jest.fn()} />);
		const buttons = screen.getAllByRole("button");
		expect(buttons[0]).toHaveAttribute("data-active", "true");
		expect(buttons[1]).toHaveAttribute("data-active", "true");
		expect(buttons[2]).toHaveAttribute("data-active", "true");
		expect(buttons[3]).toHaveAttribute("data-active", "false");
		expect(buttons[4]).toHaveAttribute("data-active", "false");
	});

	it("disabled=true prevents click", async () => {
		const onRate = jest.fn();
		render(<StarRating value={0} onRate={onRate} disabled={true} />);
		const buttons = screen.getAllByRole("button");
		await userEvent.click(buttons[2]);
		expect(onRate).not.toHaveBeenCalled();
	});
});
