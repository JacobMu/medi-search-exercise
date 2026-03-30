import { FileUpload } from "@/composer/components/FileUpload";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

beforeEach(() => {
	global.URL.createObjectURL = jest.fn(() => "blob:mock-url");
	global.URL.revokeObjectURL = jest.fn();
});

describe("FileUpload", () => {
	it("renders label text", () => {
		// Act
		render(
			<FileUpload label="Avatar Image" value={null} onChange={jest.fn()} />,
		);

		// Assert
		expect(screen.getByText("Avatar Image")).toBeInTheDocument();
	});

	it("file input has default accept attribute", () => {
		// Act
		render(<FileUpload label="Test" value={null} onChange={jest.fn()} />);

		// Assert
		const input = document.querySelector(
			"input[type=file]",
		) as HTMLInputElement;
		expect(input.accept).toBe("image/png,image/jpeg,image/webp");
	});

	it("custom accept attribute is forwarded to input", () => {
		// Act
		render(
			<FileUpload
				label="Test"
				accept="image/png"
				value={null}
				onChange={jest.fn()}
			/>,
		);

		// Assert
		const input = document.querySelector(
			"input[type=file]",
		) as HTMLInputElement;
		expect(input.accept).toBe("image/png");
	});

	it("selecting a file calls onChange with the file", async () => {
		// Arrange
		const onChange = jest.fn();
		const file = new File(["content"], "test.png", { type: "image/png" });
		render(<FileUpload label="Test" value={null} onChange={onChange} />);
		const input = document.querySelector(
			"input[type=file]",
		) as HTMLInputElement;

		// Act
		await userEvent.upload(input, file);

		// Assert
		expect(onChange).toHaveBeenCalledWith(file);
	});

	it("shows preview img when value is a File", () => {
		// Arrange
		const file = new File(["content"], "test.png", { type: "image/png" });

		// Act
		render(<FileUpload label="Test" value={file} onChange={jest.fn()} />);

		// Assert
		expect(screen.getByRole("img")).toBeInTheDocument();
	});

	it("rejects files with disallowed MIME types", async () => {
		// Arrange
		const onChange = jest.fn();
		const badFile = new File(["content"], "malware.exe", {
			type: "application/octet-stream",
		});
		render(<FileUpload label="Test" value={null} onChange={onChange} />);
		const input = document.querySelector(
			'input[type="file"]',
		) as HTMLInputElement;

		// Act
		await userEvent.upload(input, badFile);

		// Assert
		expect(onChange).not.toHaveBeenCalledWith(expect.any(File));
	});
});
